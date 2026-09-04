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
