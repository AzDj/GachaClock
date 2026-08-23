import unittest

from spider.ys_mihoyo import build_frequency_items, select_display_image


class YsMihoyoImageTest(unittest.TestCase):
    def test_prefers_character_debut_image(self):
        page = {
            "modules": [
                {
                    "name": "角色展示",
                    "components": [{"data": '{"list":[{"tab_name":"角色展示","image":"https://example.com/fallback.png"}]}' }],
                },
                {
                    "name": "角色宣发时间轴",
                    "components": [{"data": '{"list":[{"tab_name":"「2026.01.01」角色登场","attr":[{"value":["<img src=\\"https://example.com/debut.png\\">"]}]}]}' }],
                },
            ]
        }

        self.assertEqual("https://example.com/debut.png", select_display_image(page))

    def test_falls_back_to_character_display_image(self):
        page = {
            "modules": [
                {
                    "name": "角色展示",
                    "components": [{"data": '{"list":[{"tab_name":"角色展示","image":"https://example.com/display.png"}]}' }],
                }
            ]
        }

        self.assertEqual("https://example.com/display.png", select_display_image(page))

    def test_builds_current_pool_with_detail_page_image(self):
        payload = {
            "data": {
                "list": [
                    {
                        "title": "「测试」祈愿",
                        "start_time": "2026-01-01 10:00:00",
                        "end_time": "2026-01-20 17:59:59",
                        "pool": [{"icon": "https://example.com/avatar.png", "url": "https://baike.mihoyo.com/ys/obc/content/123/detail"}],
                    }
                ]
            }
        }

        items = build_frequency_items(payload, lambda entry_id: {"name": "测试角色", "modules": []})
        self.assertEqual("测试角色", items[0]["gachas"][0]["title"])
        self.assertEqual("https://example.com/avatar.png", items[0]["gachas"][0]["img"])


if __name__ == "__main__":
    unittest.main()
