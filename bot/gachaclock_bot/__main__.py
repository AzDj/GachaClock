"""NoneBot2 进程入口。"""

import nonebot
from nonebot.adapters.claweixin import Adapter as ClaWeixinAdapter


def create_bot() -> None:
    """初始化 NoneBot2 并注册 ClawWeixin 适配器。"""
    nonebot.init()
    driver = nonebot.get_driver()
    driver.register_adapter(ClaWeixinAdapter)
    nonebot.load_plugin("gachaclock_bot.plugins.pool")


def main() -> None:
    """启动机器人进程。"""
    create_bot()
    nonebot.run()


if __name__ == "__main__":
    main()
