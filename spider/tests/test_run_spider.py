import unittest

from run_spider import (
    ensure_spiders_produced_items,
    parse_allow_empty,
    partition_spider_output,
    resolve_retry_groups,
    warn_tolerated,
)


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


class PartitionSpiderOutputTest(unittest.TestCase):
    def test_split_empty_and_tolerated(self):
        empty, tolerated = partition_spider_output(
            [
                ("zzz", FakeCrawler(4)),
                ("ys", FakeCrawler(0)),
                ("endfield/history", FakeCrawler(0)),
            ],
            allow_empty={"endfield/history"},
        )
        self.assertEqual(empty, ["ys"])
        self.assertEqual(tolerated, ["endfield/history"])

    def test_no_empty_spiders(self):
        empty, tolerated = partition_spider_output(
            [("zzz", FakeCrawler(4)), ("ys", FakeCrawler(2))]
        )
        self.assertEqual((empty, tolerated), ([], []))


class ResolveRetryGroupsTest(unittest.TestCase):
    def test_map_spider_names_to_groups(self):
        # 爬虫名与游戏组名不同（如 sr/role 属于 sr 组）。
        self.assertEqual(resolve_retry_groups(["ys"]), ["ys"])
        self.assertEqual(resolve_retry_groups(["sr/role"]), ["sr"])
        self.assertEqual(
            resolve_retry_groups(["ys", "endfield/history"]), ["endfield", "ys"]
        )

    def test_unknown_spider_maps_to_nothing(self):
        self.assertEqual(resolve_retry_groups(["not-a-spider"]), [])

    def test_warn_tolerated_prints_annotation(self):
        import io
        from contextlib import redirect_stdout

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            warn_tolerated(["endfield/history"])
        self.assertIn("::warning::endfield/history", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
