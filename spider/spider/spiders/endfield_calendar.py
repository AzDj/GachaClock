import re

import scrapy

from spider.items import HistoryItem


class EndfieldCalendarSpider(scrapy.Spider):
    name = "endfield/history"
    custom_settings = {
        "ITEM_PIPELINES": {
            "spider.pipelines.HistoryMetaPipeline": 300,
        },
    }
    allowed_domains = ["endfield.hypergryph.com", "web.hycdn.cn"]
    start_urls = ["https://endfield.hypergryph.com/#calendar"]
    fallback_calendar_url = (
        "https://web.hycdn.cn/endfield/official-v4/_next/static/media/content.8993ec05.jpg"
    )

    def parse(self, response):
        layout_scripts = [
            response.urljoin(src)
            for src in response.xpath("//script/@src").getall()
            if "/_next/static/chunks/app/" in src and "layout-" in src
        ]

        if not layout_scripts:
            yield self.build_item(self.fallback_calendar_url)
            return

        for script_url in layout_scripts:
            yield scrapy.Request(
                script_url,
                callback=self.parse_script,
                errback=self.parse_script_error,
                dont_filter=True,
            )

    def parse_script(self, response):
        calendar_url = self.extract_calendar_url(response.text)
        if calendar_url:
            yield self.build_item(calendar_url)

    def parse_script_error(self, failure):
        self.logger.warning("终末地版本日历脚本读取失败：%s", failure.value)
        yield self.build_item(self.fallback_calendar_url)

    def extract_calendar_url(self, text):
        module_match = re.search(
            r'lang:"zh-cn".*?"calendar\.content":n\((\d+)\)\.A\.src',
            text,
            re.S,
        )
        if not module_match:
            return ""

        module_id = module_match.group(1)
        module_pattern = re.compile(
            rf"{module_id}:\(e,a,n\)=>\{{.*?src:\"([^\"]+content\.[^\"]+?\.jpg)\"",
            re.S,
        )
        module_source = module_pattern.search(text)
        if module_source:
            return module_source.group(1)

        return ""

    def build_item(self, image_url):
        item = HistoryItem()
        item["img"] = image_url
        item["title"] = "终末地版本日历"
        item["type"] = "版本"
        item["version"] = "终末地版本日历"
        # 版本日历不是限时卡池，使用长期有效时间接入现有倒计时数据模型。
        item["timer"] = "2026/01/01 00:00 ~ 2099/12/31 23:59"
        item["s"] = "版本日历"
        item["a"] = []
        return item
