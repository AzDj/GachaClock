import re

import scrapy

from spider.items import HistoryItem


def extract_link_titles(cell):
    role_title_list = []
    fallback_title_list = []

    for link in cell.xpath(".//a"):
        raw_title = (link.xpath("./@title").extract_first() or "").strip()
        title = normalize_link_title(raw_title)
        if not title:
            title = normalize_link_title("".join(link.xpath(".//text()").extract()).strip())

        if not title:
            continue

        target_list = fallback_title_list if is_file_link_title(raw_title) else role_title_list
        if title not in target_list:
            target_list.append(title)

    return role_title_list or fallback_title_list


def is_file_link_title(value):
    return (value or "").strip().startswith("文件:")


def normalize_link_title(value):
    title = (value or "").strip()

    if title.startswith("文件:"):
        title = title[len("文件:") :]
    if title.startswith("角色头像-"):
        title = title[len("角色头像-") :]

    for suffix in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        if title.lower().endswith(suffix):
            title = title[: -len(suffix)]
            break

    return title.strip()


def normalize_single_or_list(value_list):
    if len(value_list) == 1:
        return value_list[0]

    return value_list


def extract_image_urls(cell):
    image_url_map = {}
    raw_url_list = cell.xpath(".//img/@srcset | .//img/@src | .//img/@data-src").extract()

    for raw_url in raw_url_list:
        image_url = normalize_image_url(raw_url)
        image_key = get_image_key(image_url)
        image_width = get_image_width(image_url)

        if not image_url:
            continue

        previous_image = image_url_map.get(image_key)
        if not previous_image or previous_image[0] < image_width:
            image_url_map[image_key] = (image_width, image_url)

    return [image_url for _, image_url in image_url_map.values()]


def normalize_image_url(value):
    image_url = (value or "").strip().split(" ", 1)[0]

    if image_url.startswith("//"):
        return f"https:{image_url}"

    return image_url


def get_image_key(image_url):
    match = re.match(r"^(.+)/\d+px-[^/]+$", image_url or "")

    return match.group(1) if match else image_url


def get_image_width(image_url):
    match = re.search(r"/(\d+)px-[^/]+$", image_url or "")

    return int(match.group(1)) if match else 0


class SrHistorySpider(scrapy.Spider):
    name = "sr/history"
    custom_settings = {
        "ITEM_PIPELINES": {
            "spider.pipelines.HistoryPipeline": 300,
        },
    }
    allowed_domains = ["wiki.biligame.com"]
    start_urls = ["https://wiki.biligame.com/sr/%E5%8E%86%E5%8F%B2%E8%B7%83%E8%BF%81"]

    def parse(self, response):
        row_list = response.xpath('//*[@id="mw-content-text"]/div/div[@class="row"]')

        # 每个版本
        for row in row_list:
            # 每个卡池
            tb_list = row.xpath(".//tbody")
            for tb in tb_list:
                try:
                    tr_list = tb.xpath(".//tr")
                    # 每行数据，兼容两种结构：tr[0] 可能包含 img（旧版banner图）或只有 th 纯文本（新版）
                    img_srcset = tr_list[0].xpath(".//img/@srcset").extract_first()
                    img_alt = tr_list[0].xpath(".//img/@alt").extract_first()
                    th_text = tr_list[0].xpath(".//th/text()").extract_first()

                    if img_srcset:
                        img = img_srcset.strip().split(' ', 1)[0]
                        title = img_alt.strip() if img_alt else ''
                    else:
                        img = ''
                        title = th_text.strip() if th_text else ''
                    timer = tr_list[1].xpath(".//td/text()").extract_first().strip()
                    version = tr_list[2].xpath(".//td/text()").extract_first().strip()
                    s_cell = tr_list[3].xpath(".//td")[0]
                    s_title_list = extract_link_titles(s_cell)
                    s_img_list = extract_image_urls(s_cell)
                    a = extract_link_titles(tr_list[4].xpath(".//td")[0])

                    item = HistoryItem()
                    
                    item["img"] = img
                    item["title"] = title
                    item["type"] =  '角色' if '角色' in title else '武器'
                    item["version"] = version
                    item["timer"] = timer
                    item["s"] = normalize_single_or_list(s_title_list)
                    item["s_imgs"] = s_img_list
                    item["a"] = a
                    yield item
                except Exception as e:
                    print('error: 解析异常: ' + str(e))
                    pass
