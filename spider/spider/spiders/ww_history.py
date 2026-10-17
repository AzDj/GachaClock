import json
import re
from datetime import datetime, timedelta, timezone

import scrapy

from spider.items import HistoryItem

LOCAL_TIMEZONE = timezone(timedelta(hours=8))

# phase 1/2 为常规上下半；phase 3 与特殊 kind（复刻、联动、周年）需要后缀，
# 避免与同版本常规池的标题/图片文件名冲突。
PHASE_LABELS = {1: "上半", 2: "下半"}
KIND_LABELS = {"legacy": "复刻", "collab": "联动", "anniversary": "周年"}
ICON_BASE_URL = "https://bannerhistory.app"


class WwHistorySpider(scrapy.Spider):
    """鸣潮历史卡池爬虫。

    原 biligame「UP记录」页面已停止维护（最后条目 2025-02-13），
    改用 bannerhistory.app 的唤取历史页；该页为 Next.js SSR，
    完整卡池数据以 JSON 形式内嵌在 flight payload 中。
    """

    name = "ww/history"
    custom_settings = {
        "ITEM_PIPELINES": {
            "spider.pipelines.HistoryPipeline": 300,
        },
    }
    allowed_domains = ["bannerhistory.app"]
    source_url = "https://bannerhistory.app/zh/wuwa-pickup-history"
    flight_payload_pattern = re.compile(
        r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)'
    )
    banner_start_pattern = re.compile(r'\{"id":"wuwa-')

    async def start(self):
        # Scrapy 2.13 起以 start() 取代旧的 start_requests() 钩子；
        # 继续使用旧钩子会导致爬虫启动即结束、静默 0 产出。
        yield scrapy.Request(self.source_url, callback=self.parse)

    def parse(self, response):
        banners = self.extract_banners(response.text)
        if not banners:
            raise ValueError("bannerhistory 页面未解析到卡池数据，页面结构可能已变更")

        for banner in banners:
            item = self.build_item(banner)
            if item:
                yield item

    def extract_banners(self, html):
        payloads = self.flight_payload_pattern.findall(html)
        flight = "".join(json.loads(payload) for payload in payloads)

        banners = []
        seen_ids = set()
        decoder = json.JSONDecoder()
        for match in self.banner_start_pattern.finditer(flight):
            try:
                banner, _ = decoder.raw_decode(flight[match.start():])
            except json.JSONDecodeError:
                continue

            banner_id = str(banner.get("id", "")).strip()
            if banner_id and banner_id not in seen_ids:
                seen_ids.add(banner_id)
                banners.append(banner)

        # 历史页与其他游戏的 history.json 保持一致，按开始时间倒序。
        banners.sort(key=lambda banner: banner.get("startAt") or 0, reverse=True)
        return banners

    def build_item(self, banner):
        names = [
            str(character.get("zhName") or character.get("enName") or "").strip()
            for character in banner.get("characters") or []
        ]
        names = [name for name in names if name]

        start_ms = banner.get("startAt")
        end_ms = banner.get("endAt")
        if not names or not start_ms or not end_ms:
            return None

        version_label = self.build_version_label(banner)
        item = HistoryItem()
        item["img"] = self.pick_banner_image(banner)
        item["title"] = f"角色唤取 {version_label}"
        item["type"] = "角色"
        item["version"] = version_label
        item["timer"] = (
            f"{self.format_millisecond(start_ms)} ~ {self.format_millisecond(end_ms)}"
        )
        item["s"] = names
        item["a"] = []
        return item

    def build_version_label(self, banner):
        version = str(banner.get("version", "")).strip()
        phase_label = PHASE_LABELS.get(banner.get("phase"), "")
        kind_label = KIND_LABELS.get(str(banner.get("kind") or "").strip(), "")

        if kind_label and phase_label:
            return f"{version}{kind_label}{phase_label}"
        if kind_label:
            return f"{version}{kind_label}"
        return f"{version}{phase_label}"

    def pick_banner_image(self, banner):
        art = banner.get("art")
        images = art.get("images", []) if isinstance(art, dict) else []
        visible_images = [
            image
            for image in images
            if isinstance(image, dict) and str(image.get("src", "")).strip() and not image.get("hidden")
        ]
        if visible_images:
            return str(visible_images[0]["src"]).strip()

        # 个别复刻/联动池没有官方宣传图，回退到首位角色图标，保证历史页有图可展示。
        for character in banner.get("characters") or []:
            icon = str(character.get("icon") or "").strip()
            if icon:
                if icon.startswith("http"):
                    return icon
                return f"{ICON_BASE_URL}{icon}"
        return ""

    def format_millisecond(self, millisecond_timestamp):
        local_time = datetime.fromtimestamp(
            millisecond_timestamp / 1000, tz=LOCAL_TIMEZONE
        )
        return local_time.strftime("%Y-%m-%d %H:%M:%S")
