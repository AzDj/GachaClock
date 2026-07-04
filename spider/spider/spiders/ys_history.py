import re

import scrapy

from spider.items import HistoryItem


class YsHistorySpider(scrapy.Spider):
    name = "ys/history"
    custom_settings = {
        "ITEM_PIPELINES": {
            "spider.pipelines.HistoryMetaPipeline": 300,
        },
    }
    allowed_domains = ["wiki.biligame.com"]
    start_urls = ["https://wiki.biligame.com/ys/%E5%BE%80%E6%9C%9F%E7%A5%88%E6%84%BF"]

    def parse(self, response):
        table_list = response.xpath('//table[contains(concat(" ", normalize-space(@class), " "), " ys-qy-table ")]')

        for table in table_list:
            yield from self.parse_table(response, table)

    def parse_table(self, response, table):
        title = self.clean_text(
            table.xpath(".//tr[1]/th//img/@alt").get()
            or table.xpath(".//tr[1]/th//img/@title").get()
            or table.xpath("string(.//tr[1]/th)").get()
        )
        img = self.extract_image(response, table)
        fields = self.extract_fields(table)

        timer = fields.get("时间", {}).get("text", "")
        version = fields.get("版本", {}).get("text", "")
        type_name = "武器" if "武器" in title or "5星武器" in fields else "角色"
        s_list = fields.get(f"5星{type_name}", {}).get("names", [])
        a_list = fields.get(f"4星{type_name}", {}).get("names", [])

        if not title or not timer or not version or not s_list:
            return

        for s_name in s_list:
            item = HistoryItem()
            item["img"] = img
            item["title"] = title
            item["type"] = type_name
            item["version"] = version
            item["timer"] = timer
            item["s"] = s_name
            item["a"] = sorted(set(a_list))
            yield item

    def extract_fields(self, table):
        fields = {}

        for row in table.xpath(".//tr[position() > 1]"):
            key = self.clean_text(row.xpath("string(./th[1])").get())
            if not key:
                continue

            cell = row.xpath("./td[1]")
            fields[key] = {
                "text": self.clean_text(cell.xpath("string(.)").get()),
                "names": self.extract_names(cell),
            }

        return fields

    def extract_names(self, cell):
        raw_names = cell.xpath(".//a/@title").getall() or cell.xpath(".//a/text()").getall()
        names = [self.clean_text(value) for value in raw_names]
        names = [name for name in names if name and name not in ("暂无", "待定")]

        if names:
            return sorted(set(names))

        text = self.clean_text(cell.xpath("string(.)").get())
        return [text] if text and text not in ("暂无", "待定") else []

    def extract_image(self, response, table):
        image = table.xpath(".//tr[1]/th//img/@srcset").get()
        if image:
            image = image.strip().split(",", 1)[0].strip().split(" ", 1)[0]
        else:
            image = table.xpath(".//tr[1]/th//img/@src").get()

        return response.urljoin(image) if image else ""

    def clean_text(self, value):
        return re.sub(r"\s+", " ", value or "").strip()
