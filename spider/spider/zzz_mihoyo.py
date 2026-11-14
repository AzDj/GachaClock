"""米游社《绝区零》百科调频数据与静态影画资源映射。"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


# 内容 ID 映射单独维护在 spider/config/zzz_entry_meta.json，避免每次换池改代码：
# - type 为「角色」才作为卡池产出；type 为「武器」直接跳过（站点只展示角色池）
# - name 为 null 的是待补全条目，跳过并告警，等人工补名称
# - 接口出现全新 ID 时自动写入该文件（name 留空），随数据一起提交
ENTRY_META_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "zzz_entry_meta.json"
)

DETAIL_API_BASE = "https://act-api-takumi-static.mihoyo.com/hoyowiki/zzz/wapi/entry_page"
WIKI_APP_HEADER = "zzz"


def load_entry_meta(path: Path | str = ENTRY_META_PATH) -> dict:
    """读取映射文件原始结构，保留 version/note 等人工字段。"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_entry_meta(meta: dict, path: Path | str = ENTRY_META_PATH) -> None:
    """按 ID 升序写回，保证 diff 稳定、便于 code review。"""
    entries = meta.get("entries") or {}
    meta["entries"] = {key: entries[key] for key in sorted(entries, key=int)}
    Path(path).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build_frequency_items(
    payload: dict,
    fetch_display_images: bool = False,
    meta_path: Path | str = ENTRY_META_PATH,
) -> list[dict]:
    """将官方调频接口转换为项目现有卡池数据结构。

    ``fetch_display_images`` 只由线上爬虫开启，测试和离线数据转换保持纯函数行为。
    未知内容 ID 不再中断抓取：跳过并写入映射文件（name 留空），
    由人工补全名称与类型，避免一次上游换池把整站拖停。
    """
    meta = load_entry_meta(meta_path)
    entries_meta = meta.get("entries") or {}
    discovered = False

    result = []
    for pool in (payload.get("data") or {}).get("list") or []:
        entries = []
        pool_type = ""
        for entry in pool.get("pool") or []:
            url = entry.get("url", "")
            entry_id = extract_content_id(url)
            if entry_id is None:
                # 结构异常只影响这一条，不让整次抓取失败。
                print(f"::warning::绝区零调频内容 URL 无法识别，已跳过：{url}")
                continue

            content_meta = entries_meta.get(str(entry_id))
            if content_meta is None:
                entries_meta[str(entry_id)] = {
                    "name": None,
                    "type": None,
                    "rank": None,
                    "first_seen": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                }
                discovered = True
                print(
                    f"::warning::绝区零出现未配置的内容 ID {entry_id}，已跳过并写入 "
                    f"{Path(meta_path).name}，请补全 name/type/rank"
                )
                continue

            entry_type = str(content_meta.get("type") or "").strip()
            if entry_type == "武器":
                continue
            name = str(content_meta.get("name") or "").strip()
            if not name:
                print(f"::warning::绝区零内容 ID {entry_id} 名称待补全，已跳过")
                continue

            rank = str(content_meta.get("rank") or "S").strip()
            pool_type = pool_type or entry_type or "角色"
            gacha = {
                "title": name,
                "rank": rank,
                "img": entry.get("icon", ""),
                "img_path": "",
                "display_img_path": str(content_meta.get("display_path") or ""),
            }
            if fetch_display_images and entry_type == "角色" and rank == "S":
                gacha["display_img"] = fetch_display_three_image(entry.get("url", ""))
            entries.append(gacha)
        if not entries:
            continue
        result.append(
            {
                "title": str(pool.get("title") or "").strip(),
                "type": pool_type,
                "timer": [format_timer(pool.get("start_time")), format_timer(pool.get("end_time"))],
                "gachas": entries,
            }
        )

    if discovered:
        meta["entries"] = entries_meta
        save_entry_meta(meta, meta_path)
    return result


def extract_content_id(url: str) -> int | None:
    match = re.search(r"/content/(\d+)/", url or "")
    return int(match.group(1)) if match else None


def fetch_display_three_image(detail_url: str, retries: int = 3) -> str:
    """从角色详情页的“意象影画 → 影画展示3”读取原图 URL。

    CI runner 到米哈游接口偶发 SSL 握手/读取超时，单次请求失败不应让整个爬虫崩溃。
    """
    content_id = extract_content_id(detail_url)
    if content_id is None:
        raise ValueError(f"绝区零角色详情 URL 无法识别内容 ID：{detail_url}")

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                DETAIL_API_BASE,
                params={"entry_page_id": content_id, "lang": "zh-cn", "app_sn": "zzz_wiki"},
                headers={"x-rpc-wiki_app": WIKI_APP_HEADER},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("retcode") != 0:
                raise ValueError(f"绝区零角色详情接口失败：{payload.get('message', '')}")

            image_url = extract_display_three_image(payload)
            if not image_url:
                raise ValueError(f"绝区零内容 {content_id} 未找到“影画展示3”大图")
            return image_url
        except (requests.RequestException, ValueError) as e:
            last_error = e
            print(f"获取绝区零内容 {content_id} 影画展示3失败（第 {attempt}/{retries} 次）: {e}")
            time.sleep(2 * attempt)

    raise last_error


def extract_display_three_image(payload: dict) -> str:
    """从详情接口响应中按标签提取“影画展示3”，不依赖数组下标。"""
    page = (payload.get("data") or {}).get("page") or {}
    for module in page.get("modules") or []:
        for component in module.get("components") or []:
            if component.get("component_id") != "map_desc":
                continue
            component_data = component.get("data") or {}
            if isinstance(component_data, str):
                try:
                    component_data = json.loads(component_data)
                except (TypeError, ValueError):
                    continue
            for image in component_data.get("list") or []:
                if image.get("tab_name") == "影画展示3" and image.get("image"):
                    return str(image["image"]).strip()
    return ""


def format_timer(value) -> str:
    return str(value or "").strip().replace("-", "/")
