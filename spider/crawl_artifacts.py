"""按游戏收集爬虫产物，并在「处理数据」阶段合并回仓库。

CI 把抓取拆成按游戏的 matrix：每个游戏在独立 runner 上运行，只把自己改动的
文件（data / img / config）收集到 staging 目录上传为 artifact。处理阶段把所有
artifact 合并回仓库、合并未知内容 ID 登记、更新 meta.json，最后只提交一次。

这样任一游戏失败只影响自己的 job，不会把其他游戏已抓到的数据一起拖没。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
META_PATH = Path("spider/data/meta.json")
CONFIG_PATH = Path("spider/config/zzz_entry_meta.json")
META_FRAGMENT_DIR = ".meta"

# 收集范围：只关心爬虫会写入的目录，避免把 httpcache 等临时文件带上。
COLLECT_PATHS = ("spider/data", "spider/img", "spider/config")

# 每个抓取分组负责的 meta 键。只有这里声明的键才会被写回 meta.json：
# ys-history 会把数据写进 data/ys/history.json，但它不能改 ys 的当前卡池指针。
GAME_META_KEYS = {
    "zzz": ("zzz",),
    "sr": ("sr",),
    "ww": ("ww",),
    "ys": ("ys",),
    "ys-history": (),
    "arknights": ("arknights",),
    "endfield": ("endfield",),
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # 与 pipelines.update_or_create_meta_key 保持一致：indent=2、不写结尾换行，
    # 避免每次合并都产生无意义的 diff。
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def changed_files(repo_root: Path) -> list[Path]:
    """返回本次爬虫改动过的文件（相对仓库根目录）。

    使用 ``-z``：路径按 NUL 分隔且不做八进制转义，
    否则 ``spider/img/zzz/中文名.png`` 会被转义成 ``\\344\\270\\255`` 而漏收。
    """
    result = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "-z",
            "--untracked-files=all",
            "--",
            *COLLECT_PATHS,
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    entries = [entry for entry in result.stdout.split("\0") if entry]
    files = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        status = entry[:2]
        if len(entry) > 3:
            files.append(Path(entry[3:]))
        # 重命名/复制条目后面紧跟原路径，跳过它，只收集新路径。
        index += 2 if status[:1] in {"R", "C"} else 1
    return files


def collect(game: str, repo_root: Path = REPO_ROOT, staging: Path | None = None) -> dict:
    """收集单个游戏的变更文件与 meta 片段，供 upload-artifact 上传。"""
    if game not in GAME_META_KEYS:
        raise ValueError(f"不支持的游戏标识：{game}")

    staging = staging or (repo_root / ".crawl-out")
    if staging.exists():
        shutil.rmtree(staging)

    copied = []
    for relative in changed_files(repo_root):
        # meta.json 由处理阶段统一维护，抓取 job 不参与，避免多游戏互相覆盖。
        if relative == META_PATH:
            continue
        source = repo_root / relative
        if not source.is_file():
            continue
        target = staging / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(str(relative))

    meta_keys = GAME_META_KEYS[game]
    fragment = {}
    if meta_keys and (repo_root / META_PATH).exists():
        meta = _read_json(repo_root / META_PATH)
        fragment = {key: meta[key] for key in meta_keys if key in meta}
    _write_json(staging / META_FRAGMENT_DIR / f"{game}.json", fragment)

    summary = {"game": game, "files": copied, "meta": fragment}
    print(json.dumps(summary, ensure_ascii=False))
    return summary


def merge_entry_meta(base: dict, incoming: dict) -> tuple[dict, list[str]]:
    """合并未知内容 ID 登记：已填写的字段永不被 null 覆盖，first_seen 取最早。"""
    entries = dict(base.get("entries") or {})
    added = []
    for key, value in (incoming.get("entries") or {}).items():
        if key not in entries:
            entries[key] = value
            added.append(key)
            continue
        merged = dict(entries[key])
        for field in ("name", "type", "rank", "display_path"):
            if not merged.get(field) and value.get(field):
                merged[field] = value[field]
        first_seen = [item for item in (merged.get("first_seen"), value.get("first_seen")) if item]
        if first_seen:
            merged["first_seen"] = min(first_seen)
        entries[key] = merged

    result = dict(base)
    for field in ("version", "note"):
        if not result.get(field) and incoming.get(field):
            result[field] = incoming[field]
    result["entries"] = {
        key: entries[key] for key in sorted(entries, key=lambda item: int(item))
    }
    return result, added


def _apply_meta_fragments(repo_root: Path, staging: Path) -> dict:
    fragment_dir = staging / META_FRAGMENT_DIR
    if not fragment_dir.is_dir():
        return {}

    meta_path = repo_root / META_PATH
    meta = _read_json(meta_path) if meta_path.exists() else {}
    applied = {}
    for fragment_file in sorted(fragment_dir.glob("*.json")):
        game = fragment_file.stem
        allowed = set(GAME_META_KEYS.get(game, ()))
        for key, value in _read_json(fragment_file).items():
            if key not in allowed:
                print(f"::warning::忽略 {game} 的 meta 键 {key}（不在该游戏职责范围内）")
                continue
            # 指针必须指向真实存在的数据文件，避免把 meta 写成悬空路径。
            if not (repo_root / "spider" / value).exists():
                print(f"::warning::{game} 的 meta 指针指向不存在的文件，已跳过：{value}")
                continue
            meta[key] = value
            applied.setdefault(game, {})[key] = value

    if applied:
        _write_json(meta_path, meta)
    return applied


def _merge_config(repo_root: Path, staging: Path) -> dict:
    incoming_path = staging / CONFIG_PATH
    if not incoming_path.exists():
        return {}

    incoming = _read_json(incoming_path)
    target_path = repo_root / CONFIG_PATH
    if not target_path.exists():
        _write_json(target_path, incoming)
        return {"entries": len(incoming.get("entries") or {})}

    merged, added = merge_entry_meta(_read_json(target_path), incoming)
    _write_json(target_path, merged)
    return {"added": added, "entries": len(merged.get("entries") or {})}


def _pending_entries(repo_root: Path) -> list[tuple[str, dict]]:
    """返回映射文件里还未补全名称的内容 ID。"""
    if not (repo_root / CONFIG_PATH).exists():
        return []
    entries = _read_json(repo_root / CONFIG_PATH).get("entries") or {}
    return [(key, value) for key, value in entries.items() if not (value or {}).get("name")]


def write_summary(repo_root: Path, summary: dict) -> None:
    """把合并结果写进 GitHub Actions 运行摘要，便于直接看出谁更新了、谁缺失。"""
    output_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not output_path:
        return

    meta = _read_json(repo_root / META_PATH) if (repo_root / META_PATH).exists() else {}
    lines = ["## 卡池数据处理结果", "", "| 游戏 | 当前数据文件 | 本次更新 |", "| --- | --- | --- |"]
    updated = summary.get("meta") or {}
    for game in sorted(meta):
        pointer = str(meta.get(game, ""))
        mark = "✅" if game in updated else "—"
        lines.append(f"| {game} | `{pointer}` | {mark} |")

    pending = _pending_entries(repo_root)
    added = (summary.get("config") or {}).get("added") or []
    lines += ["", f"- 本次合并文件数：{summary.get('files', 0)}"]
    if added:
        lines.append(f"- 新登记未知内容 ID：{', '.join(added)}")
    if pending:
        lines.append(f"- 待补全名称的内容 ID：{', '.join(key for key, _ in pending)}")
        for key, value in pending:
            print(
                f"::warning::绝区零内容 ID {key} 名称待补全"
                f"（首次发现 {value.get('first_seen', '未知')}），请编辑 {CONFIG_PATH}"
            )
    else:
        lines.append("- 没有待补全的内容 ID")

    Path(output_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def merge(repo_root: Path = REPO_ROOT, staging: Path | None = None) -> dict:
    """把 staging 里的所有游戏产物合并回仓库。"""
    staging = staging or (repo_root / ".crawl-merged")
    copied = 0
    if staging.is_dir():
        for source in staging.rglob("*"):
            if not source.is_file():
                continue
            relative = source.relative_to(staging)
            if relative.parts[0] == META_FRAGMENT_DIR:
                continue
            if relative == CONFIG_PATH:
                # 配置文件走并集合并，不直接覆盖。
                continue
            target = repo_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied += 1

    config_summary = _merge_config(repo_root, staging)
    meta_summary = _apply_meta_fragments(repo_root, staging)
    summary = {"files": copied, "meta": meta_summary, "config": config_summary}
    print(json.dumps(summary, ensure_ascii=False))
    write_summary(repo_root, summary)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="收集/合并按游戏拆分的爬虫产物")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="收集单个游戏的变更文件")
    collect_parser.add_argument("--game", required=True, choices=sorted(GAME_META_KEYS))
    collect_parser.add_argument("--repo-root", default=str(REPO_ROOT))
    collect_parser.add_argument("--staging", default="")

    merge_parser = subparsers.add_parser("merge", help="合并所有游戏产物")
    merge_parser.add_argument("--repo-root", default=str(REPO_ROOT))
    merge_parser.add_argument("--staging", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    staging = Path(args.staging) if args.staging else None
    if args.command == "collect":
        collect(args.game, repo_root, staging)
    else:
        merge(repo_root, staging)
    return 0


if __name__ == "__main__":
    sys.exit(main())
