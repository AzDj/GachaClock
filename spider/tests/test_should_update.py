"""卡池定时维护判定测试。"""

import os
import unittest
from unittest.mock import patch

import should_update


class ShouldUpdateScheduleTest(unittest.TestCase):
    """验证明日方舟仅在每日专用定时事件中纳入抓取。"""

    def test_arknights_daily_schedule(self):
        with patch.dict(os.environ, {"SCHEDULE_CRON": "0 1 * * *"}):
            self.assertTrue(should_update.is_arknights_daily_schedule())

    def test_regular_schedule_skips_arknights(self):
        with patch.dict(os.environ, {"SCHEDULE_CRON": "0 0,4,8,12 * * *"}):
            self.assertFalse(should_update.is_arknights_daily_schedule())


if __name__ == "__main__":
    unittest.main()
