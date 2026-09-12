"""米游社《绝区零》百科调频数据与静态影画资源映射。"""

from __future__ import annotations

import json
import re
import requests


# 当前调频接口只提供图片和百科内容 ID，名称、类型及稀有度需在版本更新时核对官方公告。
# 未知内容 ID 必须中止抓取，避免工作流成功但继续发布过期卡池。
ENTRY_META = {
    2145: ("克拉蕾", "角色", "S", ""),
    147: ("安东", "角色", "A", ""),
    80: ("妮可", "角色", "A", ""),
    2188: ("猩红渴望", "武器", "S", ""),
    265: ("旋钻机-赤轴", "武器", "A", ""),
    217: ("聚宝箱", "武器", "A", ""),
    1852: ("南宫羽", "角色", "S", ""),
    1908: ("霓虹妄想", "武器", "S", ""),
}

DETAIL_API_BASE = "https://act-api-takumi-static.mihoyo.com/hoyowiki/zzz/wapi/entry_page"
WIKI_APP_HEADER = "zzz"


def build_frequency_items(payload: dict, fetch_display_images: bool = False) -> list[dict]:
    """将官方调频接口转换为项目现有卡池数据结构。

    ``fetch_display_images`` 只由线上爬虫开启，测试和离线数据转换保持纯函数行为。
    """
    result = []
    for pool in (payload.get("data") or {}).get("list") or []:
        entries = []
        pool_type = ""
        for entry in pool.get("pool") or []:
            entry_id = extract_content_id(entry.get("url", ""))
            if entry_id is None:
                raise ValueError(f"绝区零调频内容 URL 无法识别：{entry.get('url', '')}")
            meta = ENTRY_META.get(entry_id)
            if not meta:
                raise ValueError(f"绝区零调频内容 ID 未配置：{entry_id}")
            name, entry_type, rank, display_path = meta
            pool_type = pool_type or entry_type
            gacha = {
                "title": name,
                "rank": rank,
                "img": entry.get("icon", ""),
                "img_path": "",
                "display_img_path": display_path,
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
    return result


def extract_content_id(url: str) -> int | None:
    match = re.search(r"/content/(\d+)/", url or "")
    return int(match.group(1)) if match else None


def fetch_display_three_image(detail_url: str) -> str:
    """从角色详情页的“意象影画 → 影画展示3”读取原图 URL。"""
    content_id = extract_content_id(detail_url)
    if content_id is None:
        raise ValueError(f"绝区零角色详情 URL 无法识别内容 ID：{detail_url}")

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
