import unittest

from spider.zzz_mihoyo import build_frequency_items, extract_content_id


class ZzzMihoyoParserTest(unittest.TestCase):
    def test_build_frequency_items_uses_static_display_three_image(self):
        payload = {
            "data": {
                "list": [
                    {
                        "title": "「独家重映」",
                        "start_time": "2026-08-19 12:00:00",
                        "end_time": "2026-09-08 14:59:00",
                        "pool": [
                            {
                                "url": "https://baike.mihoyo.com/zzz/wiki/content/1624/detail",
                                "icon": "https://example.com/avatar.png",
                            }
                        ],
                    }
                ]
            }
        }
        items = build_frequency_items(payload)
        self.assertEqual("「独家重映」", items[0]["title"])
        self.assertEqual("角色", items[0]["type"])
        self.assertEqual("琉音", items[0]["gachas"][0]["title"])
        self.assertEqual("img/zzz/display-three/琉音.png", items[0]["gachas"][0]["img_path"])
        self.assertEqual("", items[0]["gachas"][0]["img"])

    def test_unknown_content_is_not_emitted(self):
        payload = {
            "data": {
                "list": [
                    {
                        "title": "未知卡池",
                        "pool": [{"url": "https://baike.mihoyo.com/zzz/wiki/content/99999/detail"}],
                    }
                ]
            }
        }
        self.assertEqual([], build_frequency_items(payload))

    def test_extract_content_id(self):
        self.assertEqual(1624, extract_content_id("https://baike.mihoyo.com/zzz/wiki/content/1624/detail"))
        self.assertIsNone(extract_content_id("https://baike.mihoyo.com/zzz/wiki/"))


if __name__ == "__main__":
    unittest.main()
