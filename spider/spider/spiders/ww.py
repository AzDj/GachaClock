import scrapy
import requests

from spider.items import SpiderItem


class WwSpider(scrapy.Spider):
    name = "ww"
    allowed_domains = ["wiki.kurobbs.com", "api.kurobbs.com", "prod-alicdn-community.kurobbs.com"]
    source_url = "https://wiki.kurobbs.com/mc/home?bbs_clientSource=12"
    homepage_api_url = "https://api.kurobbs.com/wiki/core/homepage/getPage"
    custom_settings = {
        "ITEM_PIPELINES": {
            "spider.pipelines.SpiderPipeline": 300,
        },
    }
    headers = {
        'wiki_type': '9',
        'source': 'h5',
        'referer': source_url,
    }

    def start_requests(self):
        yield scrapy.Request(
            self.homepage_api_url,
            headers=self.headers,
            method='POST',
            callback=self.parse,
        )

    def parse(self, response):
        data = response.json()
        sideModules = self.safe_get(data, 'data', 'contentJson', 'sideModules', default=[])
        for sideModule in sideModules:
            content = self.safe_get(sideModule, 'content', default={})
            title = str(sideModule.get('title', '')).strip()
            
            if title not in {'角色活动唤取', '武器活动唤取'}:
                continue
            
            tabs = self.safe_get(content, 'tabs', default=[])
            for tab in tabs:
                
                g = []
                for img in tab['imgs']:
                    # title 
                    entryId = self.safe_get(img, 'linkConfig', 'entryId', default='')
                    sub_title = self.get_title(entryId)
                    g.append({
                        'title': sub_title,
                        'img': img['img']
                    })
                

                timer = self.build_timer(tab)
                if not timer:
                    continue
                item = SpiderItem()
                item["title"] = tab['name']
                item["type"] =  '角色' if '角色' in title else '武器'
                item["timer"] = timer
                item["gachas"] = g
                yield item
            
        pass

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
        url = f'https://api.kurobbs.com/wiki/core/catalogue/item/getEntryDetail'
        headers = {
            **self.headers,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        try:
            response = requests.post(url, headers=headers, data=f'id={data}')
            response.raise_for_status()  # 检查响应状态码，如果不是 200 会抛出异常
            json_data = response.json()
            name = self.safe_get(json_data, 'data', 'name', default='')
            return name
        except requests.RequestException as e:
            print(f"请求发生错误: {e}")
        except ValueError:
            print(f"无法解析响应的 JSON 数据，响应内容: {response.text}")
        except KeyError:
            print(f"响应中缺少所需的键，响应内容: {response.text}")
        return data
