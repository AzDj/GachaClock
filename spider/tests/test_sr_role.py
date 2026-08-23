import unittest

from spider.spiders.sr_role import select_display_image


class SrRoleImageTest(unittest.TestCase):
    def test_selects_semantic_second_portrait_like_aventurine(self):
        images = [
            {"alt": "砂金立绘.png", "src": "https://example.com/portrait.png"},
            {"alt": "砂金立绘2.png", "src": "https://example.com/display.png"},
            {"alt": "砂金立绘3.jpg", "src": "https://example.com/mobile.jpg"},
        ]

        self.assertEqual("https://example.com/display.png", select_display_image(images))

    def test_does_not_guess_from_position_when_second_portrait_is_missing(self):
        images = [
            {"alt": "开拓者星•同谐立绘.png", "src": "https://example.com/stelle.png"},
            {"alt": "开拓者穹•同谐立绘.png", "src": "https://example.com/caelus.png"},
        ]

        self.assertEqual("", select_display_image(images))


if __name__ == "__main__":
    unittest.main()
