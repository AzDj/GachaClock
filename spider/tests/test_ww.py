import unittest

from spider.spiders.ww import WwSpider


class WwSpiderTest(unittest.TestCase):
    def setUp(self):
        self.spider = WwSpider()

    def test_uses_official_community_source(self):
        self.assertEqual(
            "https://wiki.kurobbs.com/mc/home?bbs_clientSource=12",
            self.spider.source_url,
        )

    def test_build_timer_normalizes_minute_range(self):
        self.assertEqual(
            ["2026-07-30 10:00:00", "2026-08-19 11:59:59"],
            self.spider.build_timer(
                {"countDown": {"dateRange": ["2026-07-30 10:00", "2026-08-19 11:59"]}}
            ),
        )

    def test_build_timer_rejects_missing_range(self):
        self.assertIsNone(self.spider.build_timer({"countDown": {}}))


if __name__ == "__main__":
    unittest.main()
