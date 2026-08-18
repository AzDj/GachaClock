import unittest

from spider.spiders.endfield_recruitment import EndfieldRecruitmentSpider


class EndfieldRecruitmentTest(unittest.TestCase):
    def test_extract_timer_from_official_notice_text(self):
        timer = EndfieldRecruitmentSpider.extract_timer(
            "特许寻访说明：2026/08/20 12:00 至 2026/09/10 11:59"
        )
        self.assertEqual("2026/08/20 12:00 ~ 2026/09/10 11:59", timer)

    def test_extract_records_uses_notice_content(self):
        records = list(
            EndfieldRecruitmentSpider().extract_records(
                {
                    "data": {
                        "list": [
                            {
                                "title": "终末地活动公告",
                                "content": "特许寻访说明：2026/08/20 12:00 至 2026/09/10 11:59",
                                "role": "弭弗",
                            }
                        ]
                    }
                }
            )
        )
        self.assertEqual("角色", records[0]["type"])
        self.assertEqual("弭弗", records[0]["s"])
        self.assertEqual("2026/08/20 12:00 ~ 2026/09/10 11:59", records[0]["timer"])


if __name__ == "__main__":
    unittest.main()
