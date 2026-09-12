import unittest

from run_spider import ensure_spiders_produced_items


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


if __name__ == "__main__":
    unittest.main()
