"""米游社《绝区零》百科调频数据与静态影画资源映射。"""

from __future__ import annotations

import re


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


def build_frequency_items(payload: dict) -> list[dict]:
    """将官方调频接口转换为项目现有卡池数据结构。"""
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
            entries.append(
                {
                    "title": name,
                    "rank": rank,
                    "img": entry.get("icon", ""),
                    "img_path": "",
                    "display_img_path": display_path,
                }
            )
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


def format_timer(value) -> str:
    return str(value or "").strip().replace("-", "/")
