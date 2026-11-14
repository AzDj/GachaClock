import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from crawl_artifacts import (
    _apply_meta_fragments,
    collect,
    merge,
    merge_entry_meta,
)


def make_repo() -> Path:
    """构造一个最小仓库：data/meta.json + 一个旧卡池文件 + 映射文件。"""
    repo = Path(tempfile.mkdtemp())
    (repo / "spider/data/zzz").mkdir(parents=True)
    (repo / "spider/data/ys").mkdir(parents=True)
    (repo / "spider/config").mkdir(parents=True)
    (repo / "spider/data/meta.json").write_text(
        json.dumps({"zzz": "data/zzz/old.json", "ys": "data/ys/old.json"}, indent=2),
        encoding="utf-8",
    )
    (repo / "spider/data/zzz/old.json").write_text("[]", encoding="utf-8")
    (repo / "spider/data/ys/old.json").write_text("[]", encoding="utf-8")
    (repo / "spider/config/zzz_entry_meta.json").write_text(
        json.dumps(
            {
                "version": 1,
                "note": "测试",
                "entries": {"2217": {"name": "赛维里安·洛威尔", "type": "角色", "rank": "S"}},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    return repo


class CollectTest(unittest.TestCase):
    def test_collect_only_changed_files_and_meta_fragment(self):
        repo = make_repo()
        (repo / "spider/data/zzz/new.json").write_text('[{"title": "新池"}]', encoding="utf-8")
        meta = json.loads((repo / "spider/data/meta.json").read_text(encoding="utf-8"))
        meta["zzz"] = "data/zzz/new.json"
        (repo / "spider/data/meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

        staging = repo / ".crawl-out"
        summary = collect("zzz", repo, staging)

        self.assertTrue((staging / "spider/data/zzz/new.json").exists())
        # meta.json 由处理阶段统一维护，抓取阶段不得上传，避免多游戏互相覆盖。
        self.assertFalse((staging / "spider/data/meta.json").exists())
        self.assertEqual({"zzz": "data/zzz/new.json"}, summary["meta"])
        self.assertEqual({"zzz": "data/zzz/new.json"}, json.loads(
            (staging / ".meta/zzz.json").read_text(encoding="utf-8")
        ))

    def test_collect_ys_history_has_no_meta_keys(self):
        repo = make_repo()
        (repo / "spider/data/ys/history.json").write_text("[]", encoding="utf-8")
        meta = json.loads((repo / "spider/data/meta.json").read_text(encoding="utf-8"))
        meta["ys"] = "data/ys/history.json"
        (repo / "spider/data/meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

        staging = repo / ".crawl-out"
        summary = collect("ys-history", repo, staging)

        self.assertEqual({}, summary["meta"])


class MergeTest(unittest.TestCase):
    def test_merge_applies_data_meta_and_config_union(self):
        source = make_repo()
        (source / "spider/data/zzz/new.json").write_text('[{"title": "新池"}]', encoding="utf-8")
        meta = json.loads((source / "spider/data/meta.json").read_text(encoding="utf-8"))
        meta["zzz"] = "data/zzz/new.json"
        (source / "spider/data/meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        config = json.loads((source / "spider/config/zzz_entry_meta.json").read_text(encoding="utf-8"))
        config["entries"]["9999"] = {
            "name": None, "type": None, "rank": None, "first_seen": "2026-11-14"
        }
        (source / "spider/config/zzz_entry_meta.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        staging = source / ".crawl-out"
        collect("zzz", source, staging)

        target = make_repo()
        merge(target, staging)

        self.assertTrue((target / "spider/data/zzz/new.json").exists())
        merged_meta = json.loads((target / "spider/data/meta.json").read_text(encoding="utf-8"))
        self.assertEqual("data/zzz/new.json", merged_meta["zzz"])
        self.assertEqual("data/ys/old.json", merged_meta["ys"])

        merged_config = json.loads(
            (target / "spider/config/zzz_entry_meta.json").read_text(encoding="utf-8")
        )
        self.assertEqual("赛维里安·洛威尔", merged_config["entries"]["2217"]["name"])
        self.assertIn("9999", merged_config["entries"])

    def test_merge_without_staging_is_noop(self):
        repo = make_repo()
        before = (repo / "spider/data/meta.json").read_text(encoding="utf-8")

        merge(repo, repo / ".not-exists")

        self.assertEqual(before, (repo / "spider/data/meta.json").read_text(encoding="utf-8"))

    def test_meta_fragment_ignores_unowned_and_dangling_pointer(self):
        repo = make_repo()
        staging = repo / ".crawl-out"
        (staging / ".meta").mkdir(parents=True)
        (staging / ".meta/ys-history.json").write_text(
            json.dumps({"ys": "data/ys/history.json"}), encoding="utf-8"
        )
        (staging / ".meta/zzz.json").write_text(
            json.dumps({"zzz": "data/zzz/not-exists.json"}), encoding="utf-8"
        )

        applied = _apply_meta_fragments(repo, staging)

        self.assertEqual({}, applied)
        meta = json.loads((repo / "spider/data/meta.json").read_text(encoding="utf-8"))
        self.assertEqual("data/zzz/old.json", meta["zzz"])


class MergeEntryMetaTest(unittest.TestCase):
    def test_filled_fields_are_never_overwritten_by_null(self):
        base = {"version": 1, "entries": {"1": {"name": "已补全", "type": "角色", "first_seen": "2026-11-01"}}}
        incoming = {"version": 1, "entries": {"1": {"name": None, "type": None, "first_seen": "2026-11-10"}}}

        merged, added = merge_entry_meta(base, incoming)

        self.assertEqual([], added)
        self.assertEqual("已补全", merged["entries"]["1"]["name"])
        self.assertEqual("角色", merged["entries"]["1"]["type"])
        self.assertEqual("2026-11-01", merged["entries"]["1"]["first_seen"])

    def test_added_ids_are_sorted_numerically(self):
        base = {"entries": {"100": {"name": "a"}}}
        incoming = {"entries": {"99": {"name": "b"}, "2": {"name": "c"}}}

        merged, added = merge_entry_meta(base, incoming)

        self.assertEqual(["99", "2"], added)
        self.assertEqual(["2", "99", "100"], list(merged["entries"]))


if __name__ == "__main__":
    unittest.main()
