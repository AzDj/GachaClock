"""从森空岛终末地版区提取官方“特许寻访”公告。"""

import json
import re
from urllib.parse import urlencode

import scrapy

from spider.items import HistoryItem


class EndfieldRecruitmentSpider(scrapy.Spider):
    name = "endfield/recruitment"
    allowed_domains = ["www.skland.com", "zonai.skland.com", "bbs.hycdn.cn"]
    start_urls = ["https://www.skland.com/game/endfield?cateId=16"]
    api_url = "https://zonai.skland.com/web/v2/search/item"
    custom_settings = {
        "ITEM_PIPELINES": {
            "spider.pipelines.HistoryMetaPipeline": 300,
        },
    }

    def parse(self, response):
        # 页面本身是动态渲染的；先从官方页面发现 API，再由 API 返回结构化公告。
        query = urlencode(
            {
                "gameId": 3,
                "cateId": 16,
                "keyword": "特许寻访说明",
                "pageSize": 20,
            }
        )
        yield scrapy.Request(
            f"{self.api_url}?{query}",
            callback=self.parse_api,
            errback=self.parse_api_error,
            headers={"Referer": response.url, "Accept": "application/json"},
        )

    def parse_api(self, response):
        try:
            payload = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.warning("终末地特许寻访接口返回非 JSON：%s", response.url)
            return

        for record in self.extract_records(payload):
            yield record

    def parse_api_error(self, failure):
        # 森空岛接口可能随时要求登录/签名；失败时不覆盖已有历史数据。
        self.logger.warning("终末地特许寻访接口读取失败：%s", failure.value)

    def extract_records(self, payload):
        """兼容接口 list/data/list 与 item 聚合两种返回形态。"""
        data = payload.get("data", payload) if isinstance(payload, dict) else payload
        records = data.get("list", []) if isinstance(data, dict) else []
        for record in records:
            title = str(record.get("title", "")).strip()
            text = " ".join(
                str(record.get(key, ""))
                for key in ("title", "text", "content", "description")
            )
            if "特许寻访说明" not in text and "特许寻访" not in title:
                continue
            item = HistoryItem()
            item["title"] = title
            item["type"] = "角色"
            item["version"] = title
            item["timer"] = record.get("timer") or self.extract_timer(text)
            item["s"] = record.get("role", record.get("character", ""))
            item["a"] = []
            item["img"] = record.get("cover", record.get("coverUrl", ""))
            yield item

    @staticmethod
    def extract_timer(text):
        """从官方公告正文提取“YYYY/MM/DD HH:MM ~ YYYY/MM/DD HH:MM”时间。"""
        match = re.search(
            r"(20\d{2}[/-]\d{1,2}[/-]\d{1,2}\s+\d{1,2}:\d{2})\s*[至到~—-]+\s*"
            r"(20\d{2}[/-]\d{1,2}[/-]\d{1,2}\s+\d{1,2}:\d{2})",
            text,
        )
        return f"{match.group(1)} ~ {match.group(2)}" if match else "待定"
