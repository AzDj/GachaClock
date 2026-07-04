import re

import scrapy

from spider.items import HistoryItem


class ArknightsHistorySpider(scrapy.Spider):
    name = "arknights/history"
    custom_settings = {
        "ITEM_PIPELINES": {
            "spider.pipelines.HistoryMetaPipeline": 300,
        },
    }
    allowed_domains = ["prts.wiki"]
    start_urls = ["https://prts.wiki/w/%E5%8D%A1%E6%B1%A0%E4%B8%80%E8%A7%88"]

    def parse(self, response):
        row_list = response.xpath(
            '//table[contains(concat(" ", normalize-space(@class), " "), " wikitable ")'
            ' and contains(concat(" ", normalize-space(@class), " "), " fullline ")'
            ' and contains(concat(" ", normalize-space(@class), " "), " logo ")]//tr[td]'
        )

        for row in row_list:
            yield from self.parse_row(response, row)

    def parse_row(self, response, row):
        cell_list = row.xpath("./td")
        if len(cell_list) < 4:
            return

        section_name = self.clean_text(
            row.xpath('string(preceding::h2[1]/span[contains(@class, "mw-headline")])').get()
        ) or "卡池一览"

        if len(cell_list) == 4:
            image_cell = cell_list[0]
            timer_cell = cell_list[1]
            s_cell = cell_list[2]
            a_cell = cell_list[3]
        else:
            image_cell = cell_list[1]
            timer_cell = cell_list[2]
            s_cell = cell_list[3]
            a_cell = cell_list[4]

        img = self.extract_image(response, image_cell)
        timer = self.clean_timer(timer_cell.xpath("string(.)").get())
        if not img or "~" not in timer:
            return

        title = self.extract_title(image_cell)
        s_list = self.extract_names(s_cell)
        a_list = self.extract_names(a_cell)
        if not title or not s_list:
            return

        start_date = timer.split("~", 1)[0].strip().split(" ")[0]
        version = f"{start_date} {section_name}"

        for s_name in s_list:
            item = HistoryItem()
            item["img"] = img
            item["title"] = title
            item["type"] = "角色"
            item["version"] = version
            item["timer"] = timer
            item["s"] = s_name
            item["a"] = sorted(set(a_list))
            yield item

    def extract_title(self, cell):
        title_list = [
            self.clean_text(value)
            for value in cell.xpath(".//a/@title | .//img/@alt").getall()
        ]
        title_list = [value for value in title_list if value and not value.startswith("文件:")]
        if not title_list:
            return ""

        title = title_list[-1]
        return title.rsplit("/", 1)[-1]

    def extract_names(self, cell):
        raw_names = cell.xpath(".//a/@title").getall() or cell.xpath(".//a/text()").getall()
        names = [self.clean_text(value) for value in raw_names]
        return sorted(set(name for name in names if name and not name.startswith("文件:")))

    def extract_image(self, response, cell):
        image = cell.xpath(".//img/@srcset").get()
        if image:
            image = image.strip().split(",", 1)[0].strip().split(" ", 1)[0]
        else:
            image = cell.xpath(".//img/@data-src | .//img/@src").get()

        return response.urljoin(image) if image else ""

    def clean_timer(self, value):
        timer = self.clean_text(value)
        timer = re.sub(r"[（(].*?[）)]", "", timer)
        return re.sub(r"\s*~\s*", " ~ ", timer)

    def clean_text(self, value):
        return re.sub(r"\s+", " ", value or "").strip()
