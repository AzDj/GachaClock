import unittest

from spider.zzz_mihoyo import (
    build_frequency_items,
    extract_content_id,
    extract_display_three_image,
)


class ZzzMihoyoParserTest(unittest.TestCase):
    def test_build_frequency_items_separates_avatar_and_display_image(self):
        payload = {
            "data": {
                "list": [
                    {
                        "title": "「红月初升」",
                        "start_time": "2026-09-09 10:00:00",
                        "end_time": "2026-09-30 11:59:00",
                        "pool": [
                            {
                                "url": "https://baike.mihoyo.com/zzz/wiki/content/2145/detail",
                                "icon": "https://example.com/avatar.png",
                            }
                        ],
                    }
                ]
            }
        }
        items = build_frequency_items(payload)
        self.assertEqual("「红月初升」", items[0]["title"])
        self.assertEqual("角色", items[0]["type"])
        self.assertEqual("克拉蕾", items[0]["gachas"][0]["title"])
        self.assertEqual("S", items[0]["gachas"][0]["rank"])
        self.assertEqual("https://example.com/avatar.png", items[0]["gachas"][0]["img"])
        self.assertEqual("", items[0]["gachas"][0]["img_path"])
        self.assertEqual("", items[0]["gachas"][0]["display_img_path"])

    def test_unknown_content_fails_explicitly(self):
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
        with self.assertRaisesRegex(ValueError, "99999"):
            build_frequency_items(payload)

    def test_invalid_content_url_fails_explicitly(self):
        payload = {
            "data": {
                "list": [
                    {
                        "title": "异常卡池",
                        "pool": [{"url": "https://baike.mihoyo.com/zzz/wiki/"}],
                    }
                ]
            }
        }
        with self.assertRaisesRegex(ValueError, "URL 无法识别"):
            build_frequency_items(payload)

    def test_extract_content_id(self):
        self.assertEqual(2145, extract_content_id("https://baike.mihoyo.com/zzz/wiki/content/2145/detail"))
        self.assertIsNone(extract_content_id("https://baike.mihoyo.com/zzz/wiki/"))

    def test_extract_display_three_image_by_tab_name(self):
        payload = {
            "data": {
                "page": {
                    "modules": [
                        {
                            "components": [
                                {
                                    "component_id": "map_desc",
                                    "data": '{"list":[{"tab_name":"影画展示1","image":"small.png"},{"tab_name":"影画展示3","image":"large.png"}]}',
                                }
                            ]
                        }
                    ]
                }
            }
        }
        self.assertEqual("large.png", extract_display_three_image(payload))

    def test_build_frequency_items_fetches_only_s_role_display_image(self):
        payload = {
            "data": {
                "list": [
                    {
                        "title": "当前卡池",
                        "pool": [
                            {"url": "https://baike.mihoyo.com/zzz/wiki/content/2145/detail"},
                            {"url": "https://baike.mihoyo.com/zzz/wiki/content/147/detail"},
                        ],
                    }
                ]
            }
        }
        from unittest.mock import patch

        with patch("spider.zzz_mihoyo.fetch_display_three_image", return_value="large.png") as fetch:
            items = build_frequency_items(payload, fetch_display_images=True)
        self.assertEqual("large.png", items[0]["gachas"][0]["display_img"])
        self.assertNotIn("display_img", items[0]["gachas"][1])
        fetch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
