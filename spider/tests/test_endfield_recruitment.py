import hashlib
import hmac
import json
import unittest

from spider.spiders.endfield_recruitment import EndfieldRecruitmentSpider


class EndfieldRecruitmentTest(unittest.TestCase):
    def test_signed_headers_follow_official_algorithm(self):
        token = "token"
        timestamp = "1787072643"
        path = "/web/v1/wiki/char-pool"
        sign_headers = {
            "platform": "3",
            "timestamp": timestamp,
            "dId": "",
            "vName": "1.0.0",
        }
        raw = path + timestamp + json.dumps(
            sign_headers, ensure_ascii=False, separators=(",", ":")
        )
        digest = hmac.new(token.encode(), raw.encode(), hashlib.sha256).hexdigest()
        expected = hashlib.md5(digest.encode()).hexdigest()

        headers = EndfieldRecruitmentSpider.signed_headers(
            path, token, timestamp=timestamp
        )

        self.assertEqual(expected, headers["sign"])
        self.assertEqual(timestamp, headers["timestamp"])

    def test_extract_pool_timer_uses_official_timestamps(self):
        timer = EndfieldRecruitmentSpider.extract_pool_timer(
            {
                "poolStartAtTs": "1786248000",
                "poolEndAtTs": "1788300000",
            }
        )
        self.assertEqual("2026/08/09 12:00:00 ~ 2026/09/02 06:00:00", timer)

    def test_extract_demo_image_uses_operator_display_image_tab(self):
        image = "https://bbs.hycdn.cn/image/common/20260809/demo.webp"
        item = {
            "document": {
                "chapterGroup": [
                    {
                        "title": "官方情报",
                        "widgets": [{"id": "demo", "title": "干员演示"}],
                    }
                ],
                "widgetCommonMap": {
                    "demo": {
                        "tabList": [
                            {"tabId": "profile", "title": "干员履历"},
                            {"tabId": "display", "title": "干员展示图"},
                        ],
                        "tabDataMap": {
                            "profile": {"content": "profile-content"},
                            "display": {"content": "display-content"},
                        },
                    }
                },
                "documentMap": {
                    "display-content": {
                        "blockMap": {
                            "image": {
                                "kind": "image",
                                "image": {"url": image},
                            }
                        }
                    }
                },
            }
        }

        self.assertEqual(image, EndfieldRecruitmentSpider.extract_demo_image(item))

    def test_extract_demo_image_does_not_use_other_module(self):
        item = {
            "document": {
                "chapterGroup": [
                    {
                        "title": "角色信息",
                        "widgets": [{"id": "demo", "title": "干员演示"}],
                    }
                ],
                "widgetCommonMap": {},
                "documentMap": {},
            }
        }
        self.assertEqual("", EndfieldRecruitmentSpider.extract_demo_image(item))


if __name__ == "__main__":
    unittest.main()
