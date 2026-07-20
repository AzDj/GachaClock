import unittest
from datetime import datetime

from spider.arknights_current import (
    get_arknights_maintenance_end_time,
)
from spider.history_merge import merge_history_items, select_current_history_items
from spider.pool_time import LOCAL_TIMEZONE


def local_time(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=LOCAL_TIMEZONE)


def pool(title, timer, section="限时寻访"):
    start_date = timer.split(" ", 1)[0]
    return {
        "title": title,
        "version": f"{start_date} {section}",
        "timer": timer,
    }


class ArknightsCurrentTest(unittest.TestCase):
    def test_select_current_arknights_items_keeps_two_active_pools(self):
        current_time = local_time(2026, 7, 16, 12)
        pool_list = [
            pool("已结束标准寻访", "2026-07-02 16:00 ~ 2026-07-16 03:59", "常驻标准寻访"),
            pool("当前标准寻访", "2026-07-16 04:00 ~ 2026-07-30 03:59", "常驻标准寻访"),
            pool("当前中坚寻访", "2026-07-16 04:00 ~ 2026-07-23 03:59", "常驻中坚寻访&中坚甄选"),
        ]

        current_titles = [
            item["title"]
            for item in select_current_history_items(pool_list, current_time)
        ]

        self.assertEqual(["当前标准寻访", "当前中坚寻访"], current_titles)

    def test_maintenance_end_time_uses_earliest_current_end_time(self):
        current_time = local_time(2026, 7, 16, 12)
        pool_list = [
            pool("过期限时寻访", "2026-07-01 16:00 ~ 2026-07-15 03:59"),
            pool("当前限时寻访", "2026-07-16 04:00 ~ 2026-07-30 03:59"),
            pool("当前标准寻访", "2026-07-16 04:00 ~ 2026-07-23 03:59", "常驻标准寻访"),
            pool("当前中坚寻访", "2026-07-16 04:00 ~ 2026-07-25 03:59", "常驻中坚寻访&中坚甄选"),
            pool("未来限时寻访", "2026-08-01 16:00 ~ 2026-08-15 03:59"),
        ]

        end_time = get_arknights_maintenance_end_time(pool_list, current_time)

        self.assertEqual(local_time(2026, 7, 23, 3, 59), end_time)

    def test_maintenance_end_time_is_empty_when_standard_pool_is_missing(self):
        current_time = local_time(2026, 7, 18, 12)
        pool_list = [
            pool("当前限时寻访", "2026-07-10 12:00 ~ 2026-07-24 03:59"),
            pool("过期标准寻访", "2026-07-02 04:00 ~ 2026-07-16 03:59", "常驻标准寻访"),
            pool("当前中坚寻访", "2026-07-09 04:00 ~ 2026-07-23 03:59", "常驻中坚寻访&中坚甄选"),
        ]

        end_time = get_arknights_maintenance_end_time(pool_list, current_time)

        self.assertIsNone(end_time)

    def test_merge_keeps_active_existing_pool_and_updates_expired_pool(self):
        current_time = local_time(2026, 7, 16, 12)
        existing_items = [
            {
                **pool("当前标准寻访", "2026-07-16 04:00 ~ 2026-07-30 03:59", "常驻标准寻访"),
                "s": "老数据",
                "img_path": "img/old-current.png",
            },
            {
                **pool("过期标准寻访", "2026-07-01 04:00 ~ 2026-07-15 03:59", "常驻标准寻访"),
                "s": "过期数据",
                "img_path": "img/old-expired.png",
            },
        ]
        fetched_items = [
            {
                **pool("当前标准寻访", "2026-07-16 04:00 ~ 2026-07-30 03:59", "常驻标准寻访"),
                "s": "新数据",
                "img_path": "img/new-current.png",
            },
            {
                **pool("过期标准寻访", "2026-07-01 04:00 ~ 2026-07-15 03:59", "常驻标准寻访"),
                "s": "过期数据",
                "img_path": "img/new-expired.png",
            },
            {
                **pool("新增中坚寻访", "2026-07-16 04:00 ~ 2026-07-23 03:59", "常驻中坚寻访&中坚甄选"),
                "s": "新增数据",
                "img_path": "img/new-added.png",
            },
        ]

        merged_items = merge_history_items(existing_items, fetched_items, current_time)

        self.assertEqual("img/old-current.png", merged_items[0]["img_path"])
        self.assertEqual("img/new-expired.png", merged_items[1]["img_path"])
        self.assertEqual("img/new-added.png", merged_items[2]["img_path"])

    def test_merge_adds_new_limited_pool_with_same_start_time(self):
        current_time = local_time(2026, 7, 16, 12)
        timer = "2026-07-16 04:00 ~ 2026-07-30 03:59"
        existing_items = [
            {
                **pool("当前限定寻访A", timer),
                "s": "旧限定",
                "img_path": "img/old-limited-a.png",
            },
        ]
        fetched_items = [
            {
                **pool("当前限定寻访A", timer),
                "s": "新限定",
                "img_path": "img/new-limited-a.png",
            },
            {
                **pool("当前限定寻访B", timer),
                "s": "新增限定",
                "img_path": "img/new-limited-b.png",
            },
        ]

        merged_items = merge_history_items(existing_items, fetched_items, current_time)

        self.assertEqual(["当前限定寻访A", "当前限定寻访B"], [item["title"] for item in merged_items])
        self.assertEqual("img/old-limited-a.png", merged_items[0]["img_path"])
        self.assertEqual("img/new-limited-b.png", merged_items[1]["img_path"])

    def test_merge_replaces_same_section_when_start_time_changes(self):
        current_time = local_time(2026, 7, 16, 12)
        existing_items = [
            {
                **pool("旧标准寻访", "2026-07-02 04:00 ~ 2026-07-16 03:59", "常驻标准寻访"),
                "s": "旧数据",
                "img_path": "img/old-standard.png",
            }
        ]
        fetched_items = [
            {
                **pool("新标准寻访", "2026-07-16 04:00 ~ 2026-07-30 03:59", "常驻标准寻访"),
                "s": "新数据",
                "img_path": "img/new-standard.png",
            }
        ]

        merged_items = merge_history_items(existing_items, fetched_items, current_time)

        self.assertEqual("新标准寻访", merged_items[0]["title"])
        self.assertEqual("img/new-standard.png", merged_items[0]["img_path"])


if __name__ == "__main__":
    unittest.main()
