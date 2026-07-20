import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from spider.history_merge import get_history_pool_identity, merge_history_items
from spider.pipelines import HistoryPipeline
from spider.pool_time import LOCAL_TIMEZONE


def local_time(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=LOCAL_TIMEZONE)


def pool(title, timer, pool_type="角色", **extra):
    return {
        "title": title,
        "type": pool_type,
        "version": extra.pop("version", "测试版本"),
        "timer": timer,
        **extra,
    }


class HistoryMergeTest(unittest.TestCase):
    def test_same_type_and_start_time_accepts_any_number_of_new_pools(self):
        current_time = local_time(2026, 7, 16, 12)
        timer = "2026-07-16 04:00 ~ 2026-07-30 03:59"
        existing_items = [pool("角色池A", timer, img_path="old-a.png")]
        fetched_items = [
            pool("角色池A", timer, img_path="new-a.png"),
            pool("角色池B", timer, img_path="new-b.png"),
            pool("角色池C", timer, img_path="new-c.png"),
        ]

        merged_items = merge_history_items(existing_items, fetched_items, current_time)

        self.assertEqual(["角色池A", "角色池B", "角色池C"], [item["title"] for item in merged_items])
        self.assertEqual("old-a.png", merged_items[0]["img_path"])

    def test_same_title_and_start_time_keeps_different_pool_types(self):
        current_time = local_time(2026, 7, 16, 12)
        timer = "2026-07-16 04:00 ~ 2026-07-30 03:59"
        existing_items = [pool("共用标题", timer, "角色", img_path="old-role.png")]
        fetched_items = [
            pool("共用标题", timer, "角色", img_path="new-role.png"),
            pool("共用标题", timer, "武器", img_path="new-weapon.png"),
        ]

        merged_items = merge_history_items(existing_items, fetched_items, current_time)

        self.assertEqual(["角色", "武器"], [item["type"] for item in merged_items])
        self.assertEqual("old-role.png", merged_items[0]["img_path"])

    def test_missing_active_pool_is_preserved_as_fallback(self):
        current_time = local_time(2026, 7, 16, 12)
        active_timer = "2026-07-16 04:00 ~ 2026-07-30 03:59"
        existing_items = [pool("暂时漏抓的池", active_timer)]

        merged_items = merge_history_items(existing_items, [], current_time)

        self.assertEqual(existing_items, merged_items)

    def test_expired_pool_is_replaced_by_newly_fetched_data(self):
        current_time = local_time(2026, 7, 16, 12)
        timer = "2026-07-01 04:00 ~ 2026-07-15 03:59"
        existing_items = [pool("过期池", timer, s="旧数据")]
        fetched_items = [pool("过期池", timer, s="新数据")]

        merged_items = merge_history_items(existing_items, fetched_items, current_time)

        self.assertEqual("新数据", merged_items[0]["s"])
        self.assertEqual(1, len(merged_items))

    def test_invalid_timer_uses_full_fields_to_avoid_identity_collision(self):
        first = pool("未知池", "待定", s="角色A")
        second = pool("未知池", "待定", s="角色B")

        self.assertNotEqual(get_history_pool_identity(first), get_history_pool_identity(second))

    def test_history_pipeline_applies_fallback_to_other_games(self):
        existing_items = [
            pool("漏抓的旧池", "2026-07-01 04:00 ~ 2026-07-15 03:59")
        ]
        fetched_items = [
            pool("新抓取池", "2026-07-16 04:00 ~ 2026-07-30 03:59")
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.json"
            history_path.write_text(
                json.dumps(existing_items, ensure_ascii=False),
                encoding="utf-8",
            )
            merged_items = HistoryPipeline().merge_history_items(
                SimpleNamespace(name="sr/history"),
                str(history_path),
                fetched_items,
            )

        self.assertEqual(["新抓取池", "漏抓的旧池"], [item["title"] for item in merged_items])


if __name__ == "__main__":
    unittest.main()
