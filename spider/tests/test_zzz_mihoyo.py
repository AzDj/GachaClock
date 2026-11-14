import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from spider.zzz_mihoyo import (
    ENTRY_META_PATH,
    build_frequency_items,
    extract_content_id,
    extract_display_three_image,
    load_entry_meta,
)


def write_meta(path, entries):
    payload = {
        "version": 1,
        "note": "test fixture",
        "entries": {str(key): value for key, value in entries.items()},
    }
    Path(path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class ZzzMihoyoParserTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.meta_path = Path(tmp.name) / "zzz_entry_meta.json"
        write_meta(
            self.meta_path,
            {
                2145: {"name": "克拉蕾", "type": "角色", "rank": "S"},
                147: {"name": "安东", "type": "角色", "rank": "A"},
                2217: {"name": "赛维里安·洛威尔", "type": "角色", "rank": "S"},
                2305: {"name": "禁罪囚笼", "type": "武器", "rank": "S"},
                2400: {"name": None, "type": None, "rank": None},
            },
        )

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
        items = build_frequency_items(payload, meta_path=self.meta_path)
        self.assertEqual("「红月初升」", items[0]["title"])
        self.assertEqual("角色", items[0]["type"])
        self.assertEqual("克拉蕾", items[0]["gachas"][0]["title"])
        self.assertEqual("S", items[0]["gachas"][0]["rank"])
        self.assertEqual("https://example.com/avatar.png", items[0]["gachas"][0]["img"])
        self.assertEqual("", items[0]["gachas"][0]["img_path"])
        self.assertEqual("", items[0]["gachas"][0]["display_img_path"])

    def test_unknown_content_id_is_skipped_and_recorded(self):
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

        items = build_frequency_items(payload, meta_path=self.meta_path)

        self.assertEqual([], items)
        saved = load_entry_meta(self.meta_path)["entries"]
        self.assertIn("99999", saved)
        self.assertIsNone(saved["99999"]["name"])
        self.assertIsNone(saved["99999"]["type"])
        self.assertIn("first_seen", saved["99999"])

    def test_pending_entry_is_skipped_without_failing(self):
        payload = {
            "data": {
                "list": [
                    {
                        "title": "待补全卡池",
                        "pool": [{"url": "https://baike.mihoyo.com/zzz/wiki/content/2400/detail"}],
                    }
                ]
            }
        }

        items = build_frequency_items(payload, meta_path=self.meta_path)

        self.assertEqual([], items)
        saved = load_entry_meta(self.meta_path)["entries"]
        self.assertIsNone(saved["2400"]["name"])

    def test_invalid_content_url_is_skipped(self):
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

        items = build_frequency_items(payload, meta_path=self.meta_path)

        self.assertEqual([], items)

    def test_weapon_pool_is_skipped(self):
        """站点只展示角色卡池：type 为武器的条目跳过，不判失败。"""
        payload = {
            "data": {
                "list": [
                    {
                        "title": "「答案在风中」",
                        "start_time": "2026-11-11 12:00:00",
                        "end_time": "2026-12-01 14:59:59",
                        "pool": [
                            {"url": "https://baike.mihoyo.com/zzz/wiki/content/2217/detail"},
                        ],
                    },
                    {
                        "title": "「禁罪囚笼」",
                        "start_time": "2026-11-11 12:00:00",
                        "end_time": "2026-12-01 14:59:59",
                        "pool": [
                            {"url": "https://baike.mihoyo.com/zzz/wiki/content/2305/detail"},
                        ],
                    },
                ]
            }
        }

        items = build_frequency_items(payload, meta_path=self.meta_path)

        self.assertEqual(1, len(items))
        self.assertEqual("「答案在风中」", items[0]["title"])
        self.assertEqual("角色", items[0]["type"])
        self.assertEqual("赛维里安·洛威尔", items[0]["gachas"][0]["title"])

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

        with patch("spider.zzz_mihoyo.fetch_display_three_image", return_value="large.png") as fetch:
            items = build_frequency_items(
                payload, fetch_display_images=True, meta_path=self.meta_path
            )
        self.assertEqual("large.png", items[0]["gachas"][0]["display_img"])
        self.assertNotIn("display_img", items[0]["gachas"][1])
        fetch.assert_called_once()

    def test_repository_meta_file_is_valid(self):
        """生产配置文件必须可解析，且每条都有明确类型或标记为待补全。"""
        entries = load_entry_meta(ENTRY_META_PATH)["entries"]
        self.assertTrue(entries)
        for entry_id, value in entries.items():
            self.assertIsInstance(int(entry_id), int)
            self.assertIn(value.get("type"), ("角色", "武器", None))
            if value.get("name"):
                self.assertIsInstance(value["name"], str)


if __name__ == "__main__":
    unittest.main()
