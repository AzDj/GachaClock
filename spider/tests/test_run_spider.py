import unittest

from run_spider import ensure_spiders_produced_items, parse_allow_empty


class FakeStats:
    def __init__(self, item_count):
        self.item_count = item_count

    def get_value(self, key, default=None):
        if key == "item_scraped_count":
            return self.item_count
        return default


class FakeCrawler:
    def __init__(self, item_count):
        self.stats = FakeStats(item_count)


class SpiderOutputValidationTest(unittest.TestCase):
    def test_all_spiders_produced_items(self):
        ensure_spiders_produced_items(
            [("zzz", FakeCrawler(4)), ("zzz-history", FakeCrawler(36))]
        )

    def test_empty_spider_fails_explicitly(self):
        with self.assertRaisesRegex(RuntimeError, "zzz"):
            ensure_spiders_produced_items(
                [("zzz", FakeCrawler(0)), ("zzz-history", FakeCrawler(36))]
            )

    def test_allow_empty_tolerates_listed_spider(self):
        ensure_spiders_produced_items(
            [("zzz", FakeCrawler(4)), ("endfield/history", FakeCrawler(0))],
            allow_empty={"endfield/history"},
        )

    def test_allow_empty_does_not_cover_other_spiders(self):
        with self.assertRaisesRegex(RuntimeError, "ww"):
            ensure_spiders_produced_items(
                [("ww", FakeCrawler(0)), ("endfield/history", FakeCrawler(0))],
                allow_empty={"endfield/history"},
            )

    def test_parse_allow_empty(self):
        self.assertEqual(parse_allow_empty(" a , b,, "), {"a", "b"})
        self.assertEqual(parse_allow_empty(""), set())
        self.assertEqual(parse_allow_empty(None), set())


if __name__ == "__main__":
    unittest.main()
