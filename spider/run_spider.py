import argparse
import os
import subprocess
import sys

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


# 防止重试子进程再次重试导致无限循环。
RETRY_FLAG_ENV = "RUN_SPIDER_RETRIED"


def parse_args():
    parser = argparse.ArgumentParser(description="按游戏抓取卡池数据")
    parser.add_argument(
        "--games",
        default=",".join(SPIDER_GROUPS.keys()),
        help="要抓取的游戏，使用逗号分隔，可选值：zzz,sr,ww,ys,ys-history,arknights,endfield",
    )
    parser.add_argument(
        "--allow-empty",
        default="",
        help="允许 0 产出的爬虫名（逗号分隔）。这些爬虫接口瞬时失败时只警告不判失败，"
        "既有数据由 pipeline 保留，避免连累其他游戏的抓取成果被丢弃。",
    )
    return parser.parse_args()


def parse_allow_empty(value):
    return {name.strip() for name in (value or "").split(",") if name.strip()}


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


def partition_spider_output(crawlers, allow_empty=()):
    """按产出把爬虫分为（未产出, 已容忍）两组。"""
    empty_spiders = []
    tolerated = []
    for spider_name, crawler in crawlers:
        if crawler.stats.get_value("item_scraped_count", 0) != 0:
            continue
        if spider_name in allow_empty:
            tolerated.append(spider_name)
        else:
            empty_spiders.append(spider_name)
    return empty_spiders, tolerated


def warn_tolerated(tolerated):
    for spider_name in tolerated:
        # GitHub annotation：告警直接展示在运行摘要中，避免静默降级。
        print(
            f"::warning::{spider_name} 未产出任何数据（接口瞬时失败，"
            f"已列入 --allow-empty 容忍名单，保留既有数据）"
        )


def ensure_spiders_produced_items(crawlers, allow_empty=()):
    """所有已执行爬虫都必须产出数据，禁止以成功状态发布旧文件。

    ``allow_empty`` 中的爬虫属于接口瞬时失败可容忍的场景（如终末地寻访，
    认证失败时由 HistoryMetaPipeline 保留既有历史），只警告不判失败。
    """
    empty_spiders, tolerated = partition_spider_output(crawlers, allow_empty)
    warn_tolerated(tolerated)
    if empty_spiders:
        raise RuntimeError(f"以下爬虫未产出任何数据：{','.join(empty_spiders)}")


def resolve_retry_groups(empty_spider_names):
    """把 0 产出的爬虫名映射回需要重跑的游戏组。"""
    targets = set(empty_spider_names)
    return sorted(
        game
        for game, classes in SPIDER_GROUPS.items()
        if {cls.name for cls in classes} & targets
    )


def main():
    args = parse_args()
    allow_empty = parse_allow_empty(args.allow_empty)
    spider_list = resolve_spiders(args.games)
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
    empty_spiders, tolerated = partition_spider_output(crawlers, allow_empty)
    warn_tolerated(tolerated)

    # CI runner 到国内源（米哈游/kurobbs/库街区等）的瞬时超时是红叉的主要来源。
    # 只重跑 0 产出的游戏组一次：瞬时故障大概率恢复，确定性 bug（如配置漏项）
    # 重试后依旧失败、job 保持红叉，严格性不降级。
    if empty_spiders and not os.environ.get(RETRY_FLAG_ENV):
        retry_groups = resolve_retry_groups(empty_spiders)
        print(f"以下爬虫未产出任何数据，疑似瞬时网络故障，自动重试一次：{','.join(retry_groups)}")
        env = dict(os.environ, RETRY_FLAG_ENV="1")
        exit_code = subprocess.call(
            [
                sys.executable,
                os.path.abspath(__file__),
                "--games",
                ",".join(retry_groups),
                "--allow-empty",
                args.allow_empty,
            ],
            env=env,
        )
        # 其余游戏首轮已产出并写好数据文件，重试子进程只补写失败组的文件。
        sys.exit(exit_code)

    ensure_spiders_produced_items(crawlers, allow_empty)


if __name__ == "__main__":
    main()
