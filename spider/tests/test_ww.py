from spider.spiders.ww import WwSpider


def test_get_poster_image_selects_poster_figure():
    detail = {
        "content": {
            "modules": [
                {
                    "components": [
                        {
                            "role": {
                                "figures": [
                                    {"name": "基础信息", "url": "basic.png"},
                                    {"name": "海报立绘", "url": "poster.png"},
                                ]
                            }
                        }
                    ]
                }
            ]
        }
    }

    assert WwSpider().get_poster_image(detail) == "poster.png"


def test_get_poster_image_returns_empty_when_missing():
    assert WwSpider().get_poster_image({}) == ""


def test_get_avatar_image_selects_basic_info_figure():
    detail = {
        "content": {
            "modules": [{
                "components": [{
                    "role": {"figures": [
                        {"name": "基础信息", "url": "avatar.png"},
                        {"name": "海报立绘", "url": "poster.png"},
                    ]}
                }]
            }]
        }
    }
    assert WwSpider().get_avatar_image(detail) == "avatar.png"


def test_build_gachas_rejects_incomplete_pool(monkeypatch):
    spider = WwSpider()
    monkeypatch.setattr(
        spider,
        "get_entry_detail",
        lambda entry_id: {"name": " 景燃" if entry_id == "featured" else "莫特斐"},
    )

    assert spider.build_gachas([
        {"linkConfig": {"entryId": "featured"}, "img": "featured.png"},
        {"linkConfig": {}, "img": "broken.png"},
    ]) == []


def test_build_gachas_strips_role_name():
    spider = WwSpider()
    spider.get_entry_detail = lambda entry_id: {"name": " 景燃"}

    result = spider.build_gachas([
        {"linkConfig": {"entryId": "featured"}, "img": "featured.png"},
    ])

    assert result[0]["title"] == "景燃"


def test_role_pool_requires_featured_poster():
    spider = WwSpider()
    spider.get_entry_detail = lambda entry_id: {"name": "莫特斐"}
    gachas = spider.build_gachas([
        {"linkConfig": {"entryId": "featured"}, "img": "featured.png"},
    ])

    assert gachas and not any(gacha["largeImg"] for gacha in gachas)
    assert not spider.is_featured_role_pool("角色活动唤取", gachas)
    assert spider.is_featured_role_pool("角色活动唤取", [{"largeImg": "poster.png"}])
