import unittest

from scrapy.selector import Selector

from spider.spiders.sr_history import extract_image_urls, extract_link_titles, normalize_single_or_list


class SrHistoryParserTest(unittest.TestCase):

    def test_extracts_multiple_main_roles_and_skips_file_links(self):
        cell = Selector(
            text="""
            <td>
              <a href="/sr/文件:火花.png" title="文件:火花.png"><img /></a>
              <a href="/sr/火花" title="火花">火花</a>
              <a href="/sr/丹恒•腾荒" title="丹恒•腾荒">丹恒•腾荒</a>
              <a href="/sr/长夜月" title="长夜月">长夜月</a>
            </td>
            """,
        ).xpath("//td")[0]

        self.assertEqual(extract_link_titles(cell), ["火花", "丹恒•腾荒", "长夜月"])

    def test_uses_cleaned_file_title_when_role_link_is_missing(self):
        cell = Selector(
            text="""
            <td>
              <a href="/sr/文件:吉尔伽美什.png" title="文件:吉尔伽美什.png"><img /></a>
            </td>
            """,
        ).xpath("//td")[0]

        self.assertEqual(extract_link_titles(cell), ["吉尔伽美什"])

    def test_keeps_single_value_compatible_with_existing_history_shape(self):
        self.assertEqual(normalize_single_or_list(["姬子•启行"]), "姬子•启行")
        self.assertEqual(normalize_single_or_list(["火花", "长夜月"]), ["火花", "长夜月"])

    def test_extracts_role_avatar_urls_from_srcset(self):
        cell = Selector(
            text="""
            <td>
              <img srcset="//patchwiki.biligame.com/images/sr/thumb/a/a1/demo.png/30px-demo.png 1.5x" />
              <img srcset="//patchwiki.biligame.com/images/sr/thumb/a/a1/demo.png/45px-demo.png 1.5x" />
              <img src="https://patchwiki.biligame.com/images/sr/b/b2/other.png" />
            </td>
            """,
        ).xpath("//td")[0]

        self.assertEqual(
            extract_image_urls(cell),
            [
                "https://patchwiki.biligame.com/images/sr/thumb/a/a1/demo.png/45px-demo.png",
                "https://patchwiki.biligame.com/images/sr/b/b2/other.png",
            ],
        )


if __name__ == "__main__":
    unittest.main()
