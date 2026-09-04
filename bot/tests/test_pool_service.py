"""卡池数据服务测试。"""

import json
import unittest
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from gachaclock_bot.services.pool import PoolDataError, PoolService

NOW = datetime(2026, 8, 24, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


class PoolServiceTest(unittest.IsolatedAsyncioTestCase):
    """覆盖卡池查询的正常与异常分支。"""

    def make_service(self, responses: dict[str, Any]) -> PoolService:
        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            value = responses.get(path)
            if isinstance(value, int):
                return httpx.Response(value, request=request)
            if value is None:
                return httpx.Response(404, request=request)
            return httpx.Response(200, json=value, request=request)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        self.addAsyncCleanup(client.aclose)
        return PoolService("https://example.test/", client=client, now=NOW)

    async def test_query_all_parses_meta_and_history_pools(self) -> None:
        service = self.make_service(
            {
                "/data/meta.json": {
                    "zzz": "data/zzz/current.json",
                    "arknights": "data/arknights/history.json",
                },
                "/data/zzz/current.json": [
                    {
                        "type": "角色",
                        "timer": ["2026/08/20 10:00:00", "2026/09/01 15:00:00"],
                        "gachas": [
                            {"title": "五星甲", "rank": "S"},
                            {"title": "四星乙", "rank": "A"},
                        ],
                    },
                ],
                "/data/arknights/history.json": [
                    {
                        "type": "角色",
                        "timer": "2026-08-18 16:00 ~ 2026-09-01 03:59",
                        "s": "六星甲",
                    },
                    {
                        "type": "角色",
                        "timer": "2026-08-18 16:00 ~ 2026-09-01 03:59",
                        "s": "六星乙·六星甲",
                    },
                ],
            }
        )

        reply = await service.query()

        self.assertIn("【绝区零】五星甲", reply)
        self.assertNotIn("四星乙", reply)
        self.assertIn("【明日方舟】六星甲、六星乙", reply)
        self.assertIn("详情：https://new.zeroding.com/", reply)

    async def test_query_star_rail_filters_four_star_roles(self) -> None:
        service = self.make_service(
            {
                "/data/meta.json": {"sr": "data/sr/current.json"},
                "/data/sr/current.json": [
                    {
                        "type": "角色",
                        "timer": ["2026/08/20 10:00:00", "2026/09/01 15:00:00"],
                        "gachas": [{"title": "五星甲"}, {"title": "四星乙"}],
                    }
                ],
            }
        )

        reply = await service.query("星铁")

        self.assertIn("【崩铁】五星甲", reply)
        self.assertNotIn("四星乙", reply)

    async def test_query_uses_first_role_for_regular_meta_pool(self) -> None:
        service = self.make_service(
            {
                "/data/meta.json": {"ys": "data/ys/current.json"},
                "/data/ys/current.json": [
                    {
                        "type": "角色",
                        "timer": ["2026-08-20 10:00:00", "2026-09-01 15:00:00"],
                        "gachas": [{"title": "五星甲"}, {"title": "四星乙"}],
                    }
                ],
            }
        )

        reply = await service.query("原神")

        self.assertIn("【原神】五星甲", reply)
        self.assertNotIn("四星乙", reply)

    async def test_unknown_game_returns_help_without_network(self) -> None:
        service = self.make_service({})

        reply = await service.query("不存在")

        self.assertIn("暂不支持", reply)
        self.assertIn("终末地", reply)

    async def test_partial_failure_is_reported(self) -> None:
        service = self.make_service(
            {
                "/data/meta.json": {
                    "ys": "data/ys/current.json",
                    "ww": "data/ww/current.json",
                },
                "/data/ys/current.json": [
                    {
                        "type": "角色",
                        "timer": ["2026-08-20 10:00:00", "2026-09-01 15:00:00"],
                        "gachas": [{"title": "五星甲"}],
                    }
                ],
                "/data/ww/current.json": 500,
            }
        )

        reply = await service.query()

        self.assertIn("【原神】五星甲", reply)
        self.assertIn("未能读取：鸣潮", reply)

    async def test_invalid_or_unavailable_index_raises_business_error(self) -> None:
        for responses in ({"/data/meta.json": 500}, {"/data/meta.json": []}):
            with self.subTest(responses=responses):
                service = self.make_service(responses)
                with self.assertRaises(PoolDataError):
                    await service.query()

    async def test_no_current_pool_raises_business_error(self) -> None:
        service = self.make_service(
            {
                "/data/meta.json": {"ys": "data/ys/current.json"},
                "/data/ys/current.json": [
                    {
                        "type": "角色",
                        "timer": ["2026-01-01 10:00:00", "2026-01-02 15:00:00"],
                        "gachas": [{"title": "过期角色"}],
                    }
                ],
            }
        )

        with self.assertRaises(PoolDataError):
            await service.query("原神")

    async def test_invalid_game_data_and_missing_meta_path_are_reported(self) -> None:
        invalid_data = self.make_service(
            {
                "/data/meta.json": {"ys": "data/ys/current.json"},
                "/data/ys/current.json": {},
            }
        )
        with self.assertRaises(PoolDataError):
            await invalid_data.query("原神")

        missing_path = self.make_service({"/data/meta.json": {"ys": None}})
        with self.assertRaises(PoolDataError):
            await missing_path.query("原神")

    async def test_star_rail_extracts_multiple_roles_from_pool_title(self) -> None:
        service = self.make_service(
            {
                "/data/meta.json": {"sr": "data/sr/current.json"},
                "/data/sr/current.json": [
                    {
                        "title": "「铭心之萃•五星甲、五星乙」角色活动跃迁",
                        "type": "角色",
                        "timer": ["2026/08/20 10:00:00", "2026/09/01 15:00:00"],
                        "gachas": [{"title": "五星甲"}, {"title": "五星乙"}, {"title": "四星丙"}],
                    }
                ],
            }
        )

        reply = await service.query("sr")

        self.assertIn("【崩铁】五星甲、五星乙", reply)
        self.assertNotIn("四星丙", reply)

    def test_timer_parsing_and_remaining_hours(self) -> None:
        start, end = PoolService._parse_timer("2026/08/24 10:00 ~ 2026/08/24 15:30")

        self.assertEqual(start.hour, 10)
        self.assertEqual(end.minute, 30)
        self.assertEqual(PoolService._format_remaining(end - NOW), "剩余3小时")
        with self.assertRaises(ValueError):
            PoolService._parse_timer("错误时间")

    def test_json_fixture_is_valid_utf8(self) -> None:
        payload = json.dumps({"角色": "测试"}, ensure_ascii=False).encode()
        self.assertEqual(json.loads(payload), {"角色": "测试"})
