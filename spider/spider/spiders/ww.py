import logging

import scrapy
import requests

from spider.items import SpiderItem

logger = logging.getLogger(__name__)


class WwSpider(scrapy.Spider):
    name = "ww"
    allowed_domains = ["wiki.kurobbs.com", "api.kurobbs.com", "prod-alicdn-community.kurobbs.com"]
    source_url = "https://wiki.kurobbs.com/mc/home?bbs_clientSource=12"
    homepage_api_url = "https://api.kurobbs.com/wiki/core/homepage/getPage"
    custom_settings = {
        "ITEM_PIPELINES": {
            "spider.pipelines.SpiderPipeline": 300,
        },
        # kurobbs 为国内源，海外 CI runner 访问不稳定：缩短超时并加重试，
        # 避免单次网络抖动导致整个爬虫静默 0 产出。
        "DOWNLOAD_TIMEOUT": 30,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [408, 429, 500, 502, 503, 504, 522, 524],
    }
    headers = {
        'wiki_type': '9',
        'source': 'h5',
        'referer': source_url,
    }

    async def start(self):
        # Scrapy 2.13 起以 start() 取代旧的 start_requests() 钩子；
        # 继续使用旧钩子会导致爬虫启动即结束、静默 0 产出。
        yield scrapy.Request(
            self.homepage_api_url,
            headers=self.headers,
            method='POST',
            callback=self.parse,
        )

    def parse(self, response):
        try:
            data = response.json()
        except ValueError as e:
            raise ValueError(f"鸣潮首页接口返回非 JSON 响应：{response.text[:200]}") from e

        code = self.safe_get(data, 'code')
        if code != 200:
            raise ValueError(f"鸣潮首页接口返回异常 code={code}：{str(data)[:200]}")

        sideModules = self.safe_get(data, 'data', 'contentJson', 'sideModules')
        if not isinstance(sideModules, list) or not sideModules:
            raise ValueError("鸣潮首页接口未返回 sideModules，页面结构可能已变更")

        pool_modules = 0
        for sideModule in sideModules:
            content = self.safe_get(sideModule, 'content', default={})
            title = str(sideModule.get('title', '')).strip()

            if title not in {'角色活动唤取', '武器活动唤取'}:
                continue
            pool_modules += 1

            tabs = self.safe_get(content, 'tabs', default=[])
            for tab in tabs:
                # 官方接口偶尔会返回残缺的角色页签（图片没有 entryId）。
                # 这类页签不能被提升为独立限定卡池，否则首张图片会被误显示成角色卡。
                imgs = self.safe_get(tab, 'imgs', default=[])
                g = self.build_gachas(imgs)
                if not g:
                    logger.warning(
                        "鸣潮页签[%s]无可用的角色图列表，跳过：imgs=%s",
                        tab.get('name'),
                        [
                            {
                                'entry_id': self.safe_get(i, 'linkConfig', 'entryId'),
                                'img': bool(i.get('img')) if isinstance(i, dict) else False,
                            }
                            for i in imgs if isinstance(i, dict)
                        ],
                    )
                    continue
                if not self.is_featured_role_pool(title, g):
                    logger.warning(
                        "鸣潮页签[%s]缺少主推海报立绘，按非限定池跳过：gachas=%s",
                        tab.get('name'),
                        [(x['title'], bool(x.get('largeImg'))) for x in g],
                    )
                    continue

                timer = self.build_timer(tab)
                if not timer:
                    logger.warning(
                        "鸣潮页签[%s]缺少有效时间范围，跳过：countDown=%s",
                        tab.get('name'), self.safe_get(tab, 'countDown'),
                    )
                    continue
                item = SpiderItem()
                item["title"] = tab['name']
                item["type"] =  '角色' if '角色' in title else '武器'
                item["timer"] = timer
                item["gachas"] = g
                yield item

        # 模块整体消失说明页面结构变更或接口异常，必须显式报错，
        # 避免 run_spider.py 只给出笼统的“未产出任何数据”。
        if pool_modules == 0:
            titles = [str(m.get('title', '')).strip() for m in sideModules if isinstance(m, dict)]
            raise ValueError(f"鸣潮首页接口未找到卡池模块，当前模块标题：{titles}")

    def build_gachas(self, images):
        """构造完整角色列表；任一图片缺少角色详情时丢弃整个页签。"""
        if not isinstance(images, list) or not images:
            return []

        gachas = []
        for image in images:
            entry_id = self.safe_get(image, 'linkConfig', 'entryId', default='')
            if not entry_id:
                return []

            detail = self.get_entry_detail(entry_id)
            title = str(detail.get('name') or '').strip()
            image_url = str(image.get('img') or '').strip()
            if not title or not image_url:
                return []

            gachas.append({
                # 角色详情“基础信息”作为小图，海报立绘仅用于大图。
                'title': title,
                'img': self.get_avatar_image(detail) or image_url,
                'largeImg': self.get_poster_image(detail),
            })

        return gachas

    def is_featured_role_pool(self, module_title, gachas):
        """角色限定池必须有主推角色海报，过滤四星或残缺页签。"""
        return '角色' not in module_title or any(gacha.get('largeImg') for gacha in gachas)

    def build_timer(self, tab):
        """将官方模块的分钟级时间范围规范化为现有卡池时间格式。"""
        raw_timer = self.safe_get(tab, 'countDown', 'dateRange', default=[])
        if not isinstance(raw_timer, list) or len(raw_timer) < 2:
            return None

        start = self.normalize_timer_end(raw_timer[0], ':00')
        end = self.normalize_timer_end(raw_timer[1], ':59')
        if not start or not end:
            return None
        return [start, end]

    def normalize_timer_end(self, value, suffix):
        value = str(value or '').strip()
        if not value:
            return ''
        if len(value.split(':')) == 2:
            return value + suffix
        return value

    def safe_get(self, data, *keys, default=None):
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    def get_title(self, data):
        detail = self.get_entry_detail(data)
        return detail.get('name') or data

    def get_entry_detail(self, data):
        if not data:
            return {}
        url = f'https://api.kurobbs.com/wiki/core/catalogue/item/getEntryDetail'
        headers = {
            **self.headers,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        last_error = None
        for attempt in range(3):
            try:
                # 必须带超时，否则 CI runner 到 kurobbs 的网络抖动会把整个爬虫挂起数十分钟。
                response = requests.post(url, headers=headers, data=f'id={data}', timeout=30)
                response.raise_for_status()  # 检查响应状态码，如果不是 200 会抛出异常
                return self.safe_get(response.json(), 'data', default={}) or {}
            except requests.RequestException as e:
                last_error = e
                print(f"请求发生错误（第 {attempt + 1} 次）: {e}")
            except ValueError:
                print(f"无法解析响应的 JSON 数据，响应内容: {response.text}")
                return {}
            except KeyError:
                print(f"响应中缺少所需的键，响应内容: {response.text}")
                return {}
        print(f"详情接口重试耗尽：{last_error}")
        return {}

    def get_poster_image(self, detail):
        """从角色基础资料中选择“海报立绘”，避免把活动卡片图误当作大图。"""
        modules = self.safe_get(detail, 'content', 'modules', default=[])
        for module in modules if isinstance(modules, list) else []:
            role = module.get('components', []) if isinstance(module, dict) else []
            for component in role if isinstance(role, list) else []:
                figures = self.safe_get(component, 'role', 'figures', default=[])
                for figure in figures if isinstance(figures, list) else []:
                    if figure.get('name') == '海报立绘':
                        return figure.get('url') or figure.get('verticalFigureUrl') or ''
        return ''

    def get_avatar_image(self, detail):
        """从角色详情选择近方形的基础信息图，避免使用卡池横幅/卡片图。"""
        modules = self.safe_get(detail, 'content', 'modules', default=[])
        for module in modules if isinstance(modules, list) else []:
            components = module.get('components', []) if isinstance(module, dict) else []
            for component in components if isinstance(components, list) else []:
                figures = self.safe_get(component, 'role', 'figures', default=[])
                for figure in figures if isinstance(figures, list) else []:
                    if figure.get('name') == '基础信息':
                        return figure.get('url') or figure.get('verticalFigureUrl') or ''
        return ''
