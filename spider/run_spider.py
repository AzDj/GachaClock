import argparse

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from spider.spiders.zzz import ZzzSpider
from spider.spiders.sr import SrSpider
from spider.spiders.ww import WwSpider
from spider.spiders.sr_history import SrHistorySpider
from spider.spiders.zzz_history import ZzzHistorySpider
from spider.spiders.ww_history import WwHistorySpider
from spider.spiders.sr_role import SrRoleSpider
from spider.spiders.ys_history import YsHistorySpider
from spider.spiders.arknights_history import ArknightsHistorySpider
from spider.spiders.endfield_calendar import EndfieldCalendarSpider

SPIDER_GROUPS = {
    "zzz": [ZzzSpider, ZzzHistorySpider],
    "sr": [SrSpider, SrHistorySpider, SrRoleSpider],
    "ww": [WwSpider, WwHistorySpider],
    "ys": [YsHistorySpider],
    "arknights": [ArknightsHistorySpider],
    "endfield": [EndfieldCalendarSpider],
}


def parse_args():
    parser = argparse.ArgumentParser(description="按游戏抓取卡池数据")
    parser.add_argument(
        "--games",
        default=",".join(SPIDER_GROUPS.keys()),
        help="要抓取的游戏，使用逗号分隔，可选值：zzz,sr,ww,ys,arknights,endfield",
    )
    return parser.parse_args()


def resolve_spiders(games):
    spider_list = []
    for game in games.split(","):
        normalized_game = game.strip()
        if not normalized_game:
            continue
        if normalized_game not in SPIDER_GROUPS:
            raise ValueError(f"不支持的游戏标识：{normalized_game}")
        spider_list.extend(SPIDER_GROUPS[normalized_game])
    return spider_list


def main():
    spider_list = resolve_spiders(parse_args().games)
    if not spider_list:
        print("没有需要运行的爬虫")
        return

    # 获取项目的配置，并创建 CrawlerProcess 实例。
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    for spider in spider_list:
        process.crawl(spider)
    process.start()


if __name__ == "__main__":
    main()
