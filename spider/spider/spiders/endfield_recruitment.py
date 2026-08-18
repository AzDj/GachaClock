"""从森空岛终末地 Wiki 的“干员寻访”读取角色卡池及展示图。"""

import hashlib
import hmac
import json
import time
from datetime import datetime
from urllib.parse import urlencode

import scrapy

from spider.items import HistoryItem
from spider.pipelines import HistoryMetaPipeline
from spider.pool_time import LOCAL_TIMEZONE


class EndfieldHistoryPipeline(HistoryMetaPipeline):
    """保留官方图片 URL，避免把 WebP 内容误存为 PNG。"""

    def process_item(self, item, spider):
        # 前端优先使用 img_path；终末地展示图可能是 WebP，因此直接使用官方 URL。
        item["img_path"] = ""
        self.items.append(item)
        return item


class EndfieldRecruitmentSpider(scrapy.Spider):
    """抓取官方“干员寻访”并关联详情页的“干员展示图”。"""

    name = "endfield/history"
    allowed_domains = ["wiki.skland.com", "zonai.skland.com", "bbs.hycdn.cn"]
    start_urls = [
        "https://wiki.skland.com/endfield?hg_media=skland&hg_link_campaign=tools&header=0"
    ]
    api_host = "https://zonai.skland.com"
    auth_path = "/web/v1/auth/refresh"
    char_pool_path = "/web/v1/wiki/char-pool"
    item_info_path = "/web/v1/wiki/item/info"
    custom_settings = {
        "ITEM_PIPELINES": {
            "spider.spiders.endfield_recruitment.EndfieldHistoryPipeline": 300,
        },
    }

    @classmethod
    def base_headers(cls):
        return {
            "Accept": "application/json",
            "Origin": "https://wiki.skland.com",
            "Referer": "https://wiki.skland.com/",
            "platform": "3",
            "vName": "1.0.0",
        }

    def start_requests(self):
        yield scrapy.Request(
            f"{self.api_host}{self.auth_path}",
            headers=self.base_headers(),
            callback=self.parse_auth,
            errback=self.parse_api_error,
            meta={"dont_cache": True},
        )

    def parse_auth(self, response):
        payload = self.load_json(response)
        token = ((payload or {}).get("data") or {}).get("token")
        if not token:
            self.logger.warning("终末地 Wiki 刷新令牌失败，未覆盖已有卡池：%s", response.text[:200])
            return

        headers = self.signed_headers(self.char_pool_path, token)
        yield scrapy.Request(
            f"{self.api_host}{self.char_pool_path}",
            headers=headers,
            callback=self.parse_char_pool,
            errback=self.parse_api_error,
            meta={"token": token, "dont_cache": True},
        )

    def parse_char_pool(self, response):
        payload = self.load_json(response)
        data = (payload or {}).get("data") or {}
        for pool in data.get("list", []):
            timer = self.extract_pool_timer(pool)
            if not timer:
                self.logger.warning("终末地卡池缺少有效开放时间：%s", pool.get("name", ""))
                continue

            for char in pool.get("chars", []):
                item_id = str(char.get("pcLink", "")).split("gameEntryId=")[-1]
                if not item_id or item_id == char.get("pcLink", ""):
                    self.logger.warning("终末地卡池角色缺少详情 ID：%s", char)
                    continue
                token = response.meta["token"]
                query = {"id": item_id}
                query_string = urlencode(query)
                yield scrapy.Request(
                    f"{self.api_host}{self.item_info_path}?{query_string}",
                    headers=self.signed_headers(
                        self.item_info_path, token, query_string=query_string
                    ),
                    callback=self.parse_item_info,
                    errback=self.parse_item_error,
                    meta={
                        "pool": pool,
                        "timer": timer,
                        "char": char,
                        "dont_cache": True,
                    },
                )

    def parse_item_info(self, response):
        payload = self.load_json(response)
        item = ((payload or {}).get("data") or {}).get("item") or {}
        char = response.meta["char"]
        name = str(item.get("name") or char.get("name") or "").strip()
        image = self.extract_demo_image(item)
        if not name or not image:
            self.logger.warning(
                "终末地角色详情缺少名称或“干员展示图”，跳过该角色：%s",
                response.url,
            )
            return

        pool = response.meta["pool"]
        history_item = HistoryItem()
        history_item["title"] = str(pool.get("name") or "终末地角色寻访").strip()
        history_item["type"] = "角色"
        history_item["version"] = history_item["title"]
        history_item["timer"] = response.meta["timer"]
        history_item["s"] = name
        history_item["s_imgs"] = [image]
        history_item["a"] = []
        history_item["img"] = image
        yield history_item

    def parse_item_error(self, failure):
        status = getattr(getattr(failure, "value", None), "response", None)
        status = getattr(status, "status", "unknown")
        self.logger.warning(
            "终末地角色详情读取失败，跳过该角色（HTTP %s）：%s",
            status,
            failure.request.url,
        )

    def parse_api_error(self, failure):
        # 认证或接口失败时不产生空记录，历史卡池由 HistoryMetaPipeline 保留。
        self.logger.warning("终末地官方卡池接口读取失败：%s", failure.value)

    @staticmethod
    def load_json(response):
        try:
            return json.loads(response.text)
        except (TypeError, json.JSONDecodeError):
            return None

    @classmethod
    def signed_headers(cls, path, token, query_string="", timestamp=None):
        """按官方 Wiki 客户端算法生成接口签名。"""
        timestamp = str(timestamp if timestamp is not None else int(time.time()))
        sign_headers = {
            "platform": "3",
            "timestamp": timestamp,
            "dId": "",
            "vName": "1.0.0",
        }
        raw = path + query_string + timestamp + json.dumps(
            sign_headers, ensure_ascii=False, separators=(",", ":")
        )
        digest = hmac.new(token.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
        sign = hashlib.md5(digest.encode("utf-8")).hexdigest()
        headers = cls.base_headers()
        headers.update(sign_headers)
        headers["sign"] = sign
        return headers

    @staticmethod
    def format_timestamp(value):
        try:
            timestamp = int(value)
        except (TypeError, ValueError):
            return ""
        return datetime.fromtimestamp(timestamp, tz=LOCAL_TIMEZONE).strftime(
            "%Y/%m/%d %H:%M:%S"
        )

    @classmethod
    def extract_pool_timer(cls, pool):
        start = cls.format_timestamp(pool.get("poolStartAtTs") or pool.get("startAtTs"))
        end = cls.format_timestamp(pool.get("poolEndAtTs") or pool.get("endAtTs"))
        return f"{start} ~ {end}" if start and end else ""

    @classmethod
    def extract_demo_image(cls, item):
        """从“官方情报 → 干员演示 → 干员展示图”结构提取第一张展示图。"""
        document = item.get("document") or {}
        document_map = document.get("documentMap") or {}
        common_map = document.get("widgetCommonMap") or {}
        for group in document.get("chapterGroup") or []:
            if str(group.get("title", "")).strip() != "官方情报":
                continue
            for widget in group.get("widgets") or []:
                if str(widget.get("title", "")).strip() != "干员演示":
                    continue
                common = common_map.get(str(widget.get("id")), {})
                content_id = cls.find_tab_content_id(common, "干员展示图")
                if content_id:
                    image = cls.find_image_url(document_map.get(content_id))
                    if image:
                        return image
        return ""

    @staticmethod
    def find_tab_content_id(common, title):
        tab_data = common.get("tabDataMap") or {}
        tab_list = common.get("tabList") or common.get("tabs") or []
        for tab in tab_list:
            if str(tab.get("title", "")).strip() == title:
                tab_id = str(tab.get("id") or tab.get("tabId") or "")
                content = (tab_data.get(tab_id) or {}).get("content")
                if content:
                    return content
        # 某些版本的 tabDataMap 直接带标题，兼容该官方结构变体。
        for tab_id, tab in tab_data.items():
            if str(tab.get("title", "")).strip() == title and tab.get("content"):
                return tab["content"]
        return ""

    @classmethod
    def find_image_url(cls, value):
        if isinstance(value, dict):
            for key in ("url", "src", "imageUrl"):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
                    return candidate
            for child in value.values():
                image = cls.find_image_url(child)
                if image:
                    return image
        elif isinstance(value, list):
            for child in value:
                image = cls.find_image_url(child)
                if image:
                    return image
        return ""
