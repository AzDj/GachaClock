"""机器人进程入口测试。"""

import unittest
from unittest.mock import MagicMock, patch

from gachaclock_bot import __main__ as entrypoint


class EntrypointTest(unittest.TestCase):
    """验证初始化、适配器注册和启动顺序。"""

    @patch.object(entrypoint, "nonebot")
    def test_create_bot_registers_adapter_and_plugin(self, nonebot: MagicMock) -> None:
        driver = nonebot.get_driver.return_value

        entrypoint.create_bot()

        nonebot.init.assert_called_once_with()
        driver.register_adapter.assert_called_once_with(entrypoint.ClaWeixinAdapter)
        nonebot.load_plugin.assert_called_once_with("gachaclock_bot.plugins.pool")

    @patch.object(entrypoint, "create_bot")
    @patch.object(entrypoint.nonebot, "run")
    def test_main_initializes_before_run(self, run: MagicMock, create_bot: MagicMock) -> None:
        entrypoint.main()

        create_bot.assert_called_once_with()
        run.assert_called_once_with()
