"""微信卡池查询命令。"""

import os

from nonebot import on_regex
from nonebot.adapters import Event

from gachaclock_bot.services.pool import PoolDataError, PoolService

pool_query = on_regex(r"^\s*卡池(?:\s+\S+)?\s*$", priority=10, block=True)


@pool_query.handle()
async def handle_pool_query(event: Event) -> None:
    """处理“卡池”及“卡池 游戏名”私聊命令。"""
    message = event.get_plaintext().strip()
    game_name = message.removeprefix("卡池").strip() or None
    service = PoolService(
        base_url=os.getenv("GACHACLOCK_DATA_BASE_URL", "https://new.zeroding.com/"),
    )

    try:
        reply = await service.query(game_name)
    except PoolDataError as error:
        reply = f"卡池数据暂时不可用：{error}"

    await pool_query.finish(reply)
