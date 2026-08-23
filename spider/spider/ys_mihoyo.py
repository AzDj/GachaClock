"""原神米游社观测枢当前限时祈愿与角色大图抓取。"""

import json
import re

import requests
import scrapy

from spider.items import SpiderItem


GACHA_POOL_URL = "https://act-api-takumi-static.mihoyo.com/common/blackboard/ys_obc/v1/gacha_pool"
ENTRY_PAGE_URL = "https://act-api-takumi-static.mihoyo.com/hoyowiki/genshin/wapi/entry_page"


def extract_image_urls(value):
    """从百科富文本或结构化图片字段中提取图片地址。"""
    if isinstance(value, dict):
        value = value.get("image", "")
    if not isinstance(value, str):
        return []

    return re.findall(r'(?:data-image-url|src)=["\']([^"\']+)', value) or re.findall(
        r'https?://[^\s"\'<>]+\.(?:png|jpe?g|webp|gif)', value, flags=re.IGNORECASE
    )


def select_display_image(page):
    """按“角色登场”优先、角色展示大图回退的规则选择图片。"""
    modules = page.get("modules", []) if isinstance(page, dict) else []
    timeline_images = []
    fallback_images = []

    for module in modules:
        module_name = module.get("name", "")
        for component in module.get("components", []):
            try:
                data = json.loads(component.get("data") or "{}")
            except (TypeError, ValueError):
                continue

            for tab in data.get("list", []):
                tab_name = tab.get("tab_name", "")
                if module_name == "角色宣发时间轴" and "角色登场" in tab_name:
                    for attr in tab.get("attr", []):
                        for value in attr.get("value", []):
                            timeline_images.extend(extract_image_urls(value))
                elif module_name == "角色展示":
                    for image in [tab]:
                        image_url = image.get("image", "")
                        if image_url and not image_url.lower().endswith(".gif"):
                            fallback_images.append(image_url)

    return timeline_images[0] if timeline_images else (fallback_images[0] if fallback_images else "")


def build_frequency_items(payload, fetch_page):
    """将官方 gacha_pool 响应转换为项目当前卡池格式。"""
    result = []
    for pool in payload.get("data", {}).get("list", []):
        gachas = []
        for role in pool.get("pool", []):
            match = re.search(r"/content/(\d+)/detail", role.get("url", ""))
            if not match:
                continue
            page = fetch_page(int(match.group(1)))
            title = page.get("name", "")
            if not title:
                continue
            gachas.append(
                {
                    "title": title,
                    "img": role.get("icon", ""),
                    "display_img": select_display_image(page),
                }
            )
        if gachas:
            result.append(
                {
                    "title": pool.get("title", ""),
                    "type": "角色",
                    "timer": [pool.get("start_time", ""), pool.get("end_time", "")],
                    "gachas": gachas,
                }
            )
    return result


class YsMihoyoSpider(scrapy.Spider):
    """抓取原神官方当前限时祈愿，并解析角色百科大图。"""

    name = "ys"
    start_urls = [GACHA_POOL_URL + "?app_sn=ys_obc"]
    custom_settings = {
        "ITEM_PIPELINES": {
            "spider.pipelines.SpiderPipeline": 300,
        },
    }

    def parse(self, response):
        payload = response.json()
        for item in build_frequency_items(payload, self.fetch_page):
            spider_item = SpiderItem()
            spider_item.update(item)
            yield spider_item

    def fetch_page(self, entry_page_id):
        response = requests.get(ENTRY_PAGE_URL, params={"entry_page_id": entry_page_id}, timeout=30)
        response.raise_for_status()
        return response.json().get("data", {}).get("page", {})
