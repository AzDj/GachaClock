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
from spider.ys_mihoyo import YsMihoyoSpider
from spider.spiders.arknights_history import ArknightsHistorySpider
from spider.spiders.endfield_recruitment import EndfieldRecruitmentSpider

SPIDER_GROUPS = {
    "zzz": [ZzzSpider, ZzzHistorySpider],
    "sr": [SrSpider, SrHistorySpider, SrRoleSpider],
    "ww": [WwSpider, WwHistorySpider],
    # 首页原神数据使用官方当前卡池接口；历史抓取通过 ys-history 单独运行，避免 meta 写入竞争。
    "ys": [YsMihoyoSpider],
    "ys-history": [YsHistorySpider],
    "arknights": [ArknightsHistorySpider],
    "endfield": [EndfieldRecruitmentSpider],
}


def parse_args():
    parser = argparse.ArgumentParser(description="按游戏抓取卡池数据")
    parser.add_argument(
        "--games",
        default=",".join(SPIDER_GROUPS.keys()),
        help="要抓取的游戏，使用逗号分隔，可选值：zzz,sr,ww,ys,ys-history,arknights,endfield",
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


def ensure_spiders_produced_items(crawlers):
    """所有已执行爬虫都必须产出数据，禁止以成功状态发布旧文件。"""
    empty_spiders = [
        spider_name
        for spider_name, crawler in crawlers
        if crawler.stats.get_value("item_scraped_count", 0) == 0
    ]
    if empty_spiders:
        raise RuntimeError(f"以下爬虫未产出任何数据：{','.join(empty_spiders)}")


def main():
    spider_list = resolve_spiders(parse_args().games)
    if not spider_list:
        print("没有需要运行的爬虫")
        return

    # 获取项目的配置，并创建 CrawlerProcess 实例。
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    crawlers = []
    for spider_class in spider_list:
        crawler = process.create_crawler(spider_class)
        process.crawl(crawler)
        crawlers.append((spider_class.name, crawler))
    process.start()
    ensure_spiders_produced_items(crawlers)


if __name__ == "__main__":
    main()
