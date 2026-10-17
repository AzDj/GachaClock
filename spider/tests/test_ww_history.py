import json

import pytest
from scrapy.http import HtmlResponse

from spider.spiders.ww_history import WwHistorySpider


def build_flight_html(banners, extra_html=""):
    """把卡池数组包装成 Next.js flight payload 形式的 HTML。"""
    flight_chunk = json.dumps(
        'Foo,"banners":' + json.dumps(banners, ensure_ascii=False, separators=(",", ":")) + ",Bar"
    )
    return (
        "<html><head></head><body><script>"
        f'self.__next_f.push([1,{flight_chunk}])'
        "</script></body></html>" + extra_html
    )


def make_banner(banner_id="wuwa-3.7-1", version="3.7", phase=1, kind=None,
                start_ms=1790737200000, end_ms=1792547940000,
                names=("心", "卜灵"), art_image="https://assets.example/banner.webp",
                hidden=False):
    return {
        "id": banner_id,
        "title": "Version 3.7 Featured Resonator Convene [Phase I]",
        "kind": kind,
        "version": version,
        "phase": phase,
        "startAt": start_ms,
        "endAt": end_ms,
        "characters": [
            {"id": f"c{i}", "enName": n, "zhName": n, "icon": f"/icons/wuwa/characters/{n}.png"}
            for i, n in enumerate(names)
        ],
        "art": {
            "images": [
                {"src": art_image, "label": "cover", "hidden": hidden},
            ],
        } if art_image else "$undefined",
    }


@pytest.fixture
def spider():
    return WwHistorySpider()


def test_parse_extracts_banners_sorted_desc(spider):
    older = make_banner(banner_id="wuwa-1.0-1", version="1.0", start_ms=1716429600000,
                        end_ms=1717639140000, names=("忌炎",))
    newer = make_banner(banner_id="wuwa-3.7-1", version="3.7")
    response = HtmlResponse(spider.source_url, body=build_flight_html([older, newer]), encoding="utf-8")

    items = list(spider.parse(response))

    assert [item["version"] for item in items] == ["3.7上半", "1.0上半"]
    first = items[0]
    assert first["title"] == "角色唤取 3.7上半"
    assert first["type"] == "角色"
    assert first["timer"] == "2026-09-30 11:00:00 ~ 2026-10-21 09:59:00"
    assert first["s"] == ["心", "卜灵"]
    assert first["img"] == "https://assets.example/banner.webp"


def test_parse_special_kinds_get_labels(spider):
    banners = [
        make_banner(banner_id="wuwa-3.5-legacy-3", version="3.5", phase=3, kind="legacy",
                    names=("忌炎", "吟霖"), art_image=None),
        make_banner(banner_id="wuwa-3.4-collab-1", version="3.4", phase=1, kind="collab",
                    names=("露西", "丽贝卡"), art_image=None),
        make_banner(banner_id="wuwa-2.3-anniversary-1", version="2.3", phase=1, kind="anniversary",
                    names=("忌炎",)),
    ]
    response = HtmlResponse(spider.source_url, body=build_flight_html(banners), encoding="utf-8")

    items = list(spider.parse(response))

    assert [item["version"] for item in items] == ["3.5复刻", "3.4联动上半", "2.3周年上半"]
    # 无宣传图时回退到首位角色图标
    assert items[0]["img"] == "https://bannerhistory.app/icons/wuwa/characters/忌炎.png"


def test_parse_dedupes_repeated_payloads(spider):
    banner = make_banner()
    duplicated_html = build_flight_html([banner]) + build_flight_html([banner])
    response = HtmlResponse(spider.source_url, body=duplicated_html, encoding="utf-8")

    items = list(spider.parse(response))

    assert len(items) == 1


def test_parse_skips_invalid_banners(spider):
    incomplete = make_banner(banner_id="wuwa-9.9-1", version="9.9", names=())
    complete = make_banner()
    response = HtmlResponse(spider.source_url, body=build_flight_html([incomplete, complete]), encoding="utf-8")

    items = list(spider.parse(response))

    assert [item["version"] for item in items] == ["3.7上半"]


def test_parse_raises_on_empty_payload(spider):
    response = HtmlResponse(spider.source_url, body="<html><body>no data</body></html>", encoding="utf-8")

    with pytest.raises(ValueError, match="bannerhistory"):
        list(spider.parse(response))
