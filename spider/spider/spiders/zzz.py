"""从米游社《绝区零》百科“调频”接口读取当前卡池。"""

import json

import scrapy

from spider.items import SpiderItem
from spider.zzz_mihoyo import build_frequency_items


class ZzzSpider(scrapy.Spider):
    name = "zzz"
    allowed_domains = ["act-api-takumi.mihoyo.com"]
    start_urls = [
        "https://act-api-takumi.mihoyo.com/common/blackboard/zzz_wiki/v1/gacha_pool"
        "?app_sn=zzz_wiki"
    ]
    custom_settings = {
        "ITEM_PIPELINES": {
            "spider.pipelines.SpiderPipeline": 300,
        },
        # 当前卡池必须读取实时调频数据，不能使用旧 HTTP 缓存。
        "HTTPCACHE_ENABLED": False,
    }

    def parse(self, response):
        try:
            payload = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("绝区零调频接口返回无效 JSON")
            return

        if payload.get("retcode") != 0:
            self.logger.error("绝区零调频接口失败：%s", payload.get("message"))
            return

        for raw_item in build_frequency_items(payload):
            item = SpiderItem()
            item["title"] = raw_item["title"]
            item["type"] = raw_item["type"]
            item["timer"] = raw_item["timer"]
            item["gachas"] = raw_item["gachas"]
            yield item
