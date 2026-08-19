"""米游社《绝区零》百科调频数据与静态影画资源映射。"""

from __future__ import annotations

import re


# 角色展示图固定为详情页“意象影画 → 影画展示3”，下载后由前端读取本地静态文件。
ENTRY_META = {
    1624: ("琉音", "角色", "img/zzz/display-three/琉音.png"),
    1386: ("柚叶", "角色", "img/zzz/display-three/柚叶.png"),
    997: ("悠真", "角色", "img/zzz/display-three/悠真.png"),
    2076: ("蕾米埃尔", "角色", "img/zzz/display-three/蕾米埃尔.png"),
    758: ("赛斯", "角色", "img/zzz/display-three/赛斯.png"),
    485: ("派派", "角色", "img/zzz/display-three/派派.png"),
    2079: ("希格莉德", "角色", "img/zzz/display-three/希格莉德.png"),
    227: ("苍角", "角色", "img/zzz/display-three/苍角.png"),
    493: ("露西", "角色", "img/zzz/display-three/露西.png"),
    1689: ("昨夜来电", "武器", ""),
    1463: ("狸法七变化", "武器", ""),
    991: ("残心青囊", "武器", ""),
    2109: ("空羽复归之诗", "武器", ""),
    761: ("维序者-特化型", "武器", ""),
    494: ("轰鸣座驾", "武器", ""),
    2162: ("骁骑礼赞", "武器", ""),
    215: ("含羞恶面", "武器", ""),
    486: ("好斗的阿炮", "武器", ""),
}


def build_frequency_items(payload: dict) -> list[dict]:
    """将官方调频接口转换为项目现有卡池数据结构。"""
    result = []
    for pool in (payload.get("data") or {}).get("list") or []:
        entries = []
        pool_type = ""
        for entry in pool.get("pool") or []:
            entry_id = extract_content_id(entry.get("url", ""))
            meta = ENTRY_META.get(entry_id)
            if not meta:
                continue
            name, entry_type, static_path = meta
            pool_type = pool_type or entry_type
            entries.append(
                {
                    "title": name,
                    "img": "" if static_path else entry.get("icon", ""),
                    "img_path": static_path,
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
