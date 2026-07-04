import re

import scrapy

from spider.items import HistoryItem


class WwHistorySpider(scrapy.Spider):
    name = "ww/history"
    custom_settings = {
        "ITEM_PIPELINES": {
            "spider.pipelines.HistoryPipeline": 300,
        },
    }
    allowed_domains = ["wiki.biligame.com"]
    start_urls = ["https://wiki.biligame.com/wutheringwaves/UP%E8%AE%B0%E5%BD%95"]

    def parse(self, response):
        heading_list = response.xpath('//*[@id="mw-content-text"]//h3')

        for heading in heading_list:
            version = self.clean_text(heading.xpath("string(.)").get())
            if not re.match(r"^\d{4}年\d{1,2}月\d{1,2}日", version):
                continue

            s_name = self.extract_heading_name(version)

            for sibling in heading.xpath("following-sibling::*"):
                if sibling.root.tag == "h3":
                    break

                for table in sibling.xpath('.//table[contains(@class, "wikitable")]'):
                    item = self.build_item(table, version, s_name)
                    if item:
                        yield item

    def build_item(self, table, version, s_name):
        img = table.xpath(".//img/@srcset").get()
        if img:
            img = img.strip().split(" ", 1)[0]
        else:
            img = table.xpath(".//img/@src").get()

        title = self.clean_text(table.xpath(".//img/@alt").get())
        timer = self.clean_text(
            table.xpath('.//tr[td[contains(normalize-space(.), "唤取时间")]]/td[last()]/text()').get()
        )

        if not img or not title or not timer:
            return None

        item = HistoryItem()
        item["img"] = img
        item["title"] = title.rsplit(".", 1)[0]
        item["type"] = "角色" if "角色" in title else "武器"
        item["version"] = version
        item["timer"] = timer
        item["s"] = s_name if item["type"] == "角色" else item["title"]
        item["a"] = []
        return item

    def clean_text(self, value):
        return re.sub(r"\s+", " ", value or "").strip()

    def extract_heading_name(self, value):
        return re.sub(r"^\d{4}年\d{1,2}月\d{1,2}日\s*", "", value).strip()
