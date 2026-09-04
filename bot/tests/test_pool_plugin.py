"""微信卡池命令插件测试。"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import nonebot

nonebot.init(_env_file=None, driver="~httpx")

from gachaclock_bot.plugins import pool as pool_plugin  # noqa: E402


class PoolPluginTest(unittest.IsolatedAsyncioTestCase):
    """验证命令参数传递、正常回复和异常回复。"""

    async def test_handler_queries_specific_game_and_replies(self) -> None:
        event = MagicMock()
        event.get_plaintext.return_value = "卡池 原神"
        service = MagicMock()
        service.query = AsyncMock(return_value="原神卡池回复")

        with (
            patch.object(pool_plugin, "PoolService", return_value=service) as service_class,
            patch.object(pool_plugin.pool_query, "finish", new=AsyncMock()) as finish,
        ):
            await pool_plugin.handle_pool_query(event)

        service_class.assert_called_once()
        service.query.assert_awaited_once_with("原神")
        finish.assert_awaited_once_with("原神卡池回复")

    async def test_handler_returns_business_error_message(self) -> None:
        event = MagicMock()
        event.get_plaintext.return_value = "卡池"
        service = MagicMock()
        service.query = AsyncMock(side_effect=pool_plugin.PoolDataError("读取失败"))

        with (
            patch.object(pool_plugin, "PoolService", return_value=service),
            patch.object(pool_plugin.pool_query, "finish", new=AsyncMock()) as finish,
        ):
            await pool_plugin.handle_pool_query(event)

        service.query.assert_awaited_once_with(None)
        finish.assert_awaited_once_with("卡池数据暂时不可用：读取失败")
