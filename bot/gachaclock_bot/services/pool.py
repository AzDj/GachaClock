"""读取并格式化 GachaClock 当前卡池数据。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import httpx

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
GAME_ORDER = ("zzz", "sr", "ww", "ys", "arknights", "endfield")
GAME_LABELS = {
    "zzz": "绝区零",
    "sr": "崩铁",
    "ww": "鸣潮",
    "ys": "原神",
    "arknights": "明日方舟",
    "endfield": "终末地",
}
GAME_ALIASES = {
    "zzz": "zzz",
    "绝区零": "zzz",
    "sr": "sr",
    "崩铁": "sr",
    "星铁": "sr",
    "崩坏星穹铁道": "sr",
    "ww": "ww",
    "鸣潮": "ww",
    "ys": "ys",
    "原神": "ys",
    "arknights": "arknights",
    "方舟": "arknights",
    "明日方舟": "arknights",
    "endfield": "endfield",
    "终末地": "endfield",
    "明日方舟终末地": "endfield",
}


class PoolDataError(RuntimeError):
    """卡池数据读取或解析失败。"""


@dataclass(frozen=True)
class CurrentPool:
    """单个游戏的当前角色卡池摘要。"""

    game: str
    role_names: tuple[str, ...]
    end_time: datetime
    has_multiple_end_times: bool = False


class PoolService:
    """从线上静态数据读取当前卡池。"""

    def __init__(
        self,
        base_url: str,
        *,
        client: httpx.AsyncClient | None = None,
        now: datetime | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self._client = client
        self.now = (now or datetime.now(SHANGHAI_TZ)).astimezone(SHANGHAI_TZ)

    async def query(self, game_name: str | None = None) -> str:
        """查询全部游戏或指定游戏，并返回适合微信的纯文本。"""
        game = self._resolve_game(game_name)
        if game_name and game is None:
            supported = "、".join(GAME_LABELS[key] for key in GAME_ORDER)
            return f"暂不支持“{game_name}”。可查询：{supported}。"

        try:
            meta = await self._get_json("data/meta.json")
        except (httpx.HTTPError, ValueError, TypeError) as error:
            raise PoolDataError("无法读取当前卡池索引，请稍后重试") from error
        if not isinstance(meta, dict):
            raise PoolDataError("当前卡池索引格式错误")

        games = (game,) if game else tuple(key for key in GAME_ORDER if key in meta)
        pools: list[CurrentPool] = []
        failures: list[str] = []
        for key in games:
            path = meta.get(key)
            if not isinstance(path, str):
                failures.append(GAME_LABELS[key])
                continue
            try:
                pools.append(await self._load_current_pool(key, path))
            except (PoolDataError, httpx.HTTPError, ValueError, TypeError, KeyError):
                failures.append(GAME_LABELS[key])

        if not pools:
            raise PoolDataError(f"未能解析{'、'.join(failures) or '任何游戏'}的数据")

        parts = [self._format_pool(pool) for pool in pools]
        if failures:
            parts.append(f"未能读取：{'、'.join(failures)}")
        parts.append("详情：https://new.zeroding.com/")
        return "\n\n".join(parts)

    async def _load_current_pool(self, game: str, path: str) -> CurrentPool:
        data = await self._get_json(path)
        if not isinstance(data, list):
            raise PoolDataError(f"{GAME_LABELS[game]}数据格式错误")

        if data and isinstance(data[0], dict) and "gachas" in data[0]:
            return await self._parse_meta_pool(game, data)
        return self._parse_history_pool(game, data)

    async def _parse_meta_pool(self, game: str, data: list[dict[str, Any]]) -> CurrentPool:
        current = [item for item in data if item.get("type") == "角色" and self._is_current(item.get("timer"))]
        if not current:
            raise PoolDataError(f"{GAME_LABELS[game]}没有进行中的角色卡池")

        names: list[str] = []
        for item in current:
            gachas = item.get("gachas") or []
            if game == "zzz":
                featured = [role for role in gachas if role.get("rank") == "S"]
            elif game == "sr":
                featured_names = self._get_sr_featured_role_names(item)
                featured = [role for role in gachas if role.get("title") in featured_names]
            else:
                featured = gachas[:1]
            names.extend(str(role.get("title", "")).strip() for role in featured)

        end_times = {self._parse_timer(item["timer"])[1] for item in current}
        return CurrentPool(game, self._unique_nonempty(names), min(end_times), len(end_times) > 1)

    def _parse_history_pool(self, game: str, data: list[dict[str, Any]]) -> CurrentPool:
        current = [item for item in data if item.get("type") == "角色" and self._is_current(item.get("timer"))]
        if not current:
            raise PoolDataError(f"{GAME_LABELS[game]}没有进行中的角色卡池")

        names: list[str] = []
        for item in current:
            value = item.get("s")
            if isinstance(value, list):
                names.extend(str(name).strip() for name in value)
            elif value is not None:
                names.extend(part.strip() for part in str(value).replace("·", "、").split("、"))
        end_times = {self._parse_timer(item["timer"])[1] for item in current}
        return CurrentPool(game, self._unique_nonempty(names), min(end_times), len(end_times) > 1)

    @staticmethod
    def _get_sr_featured_role_names(pool: dict[str, Any]) -> tuple[str, ...]:
        """按网页端规则提取崩铁五星：联合池解析标题，单池取首位。"""
        gacha_names = tuple(
            str(gacha.get("title", "")).strip()
            for gacha in pool.get("gachas") or []
            if str(gacha.get("title", "")).strip()
        )
        title_match = re.match(r"^「[^」]*?•([^」]+)」角色活动跃迁$", str(pool.get("title", "")))
        if title_match:
            title_names = tuple(
                name.strip()
                for name in title_match.group(1).split("、")
                if name.strip() in gacha_names
            )
            if title_names:
                return title_names
        return gacha_names[:1]

    async def _get_json(self, path: str) -> Any:
        url = urljoin(self.base_url, path)
        if self._client is not None:
            response = await self._client.get(url)
            response.raise_for_status()
            return response.json()
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    def _is_current(self, timer: Any) -> bool:
        try:
            start, end = self._parse_timer(timer)
        except (TypeError, ValueError):
            return False
        return start <= self.now <= end

    @staticmethod
    def _parse_timer(timer: Any) -> tuple[datetime, datetime]:
        if isinstance(timer, list) and len(timer) == 2:
            values = timer
        elif isinstance(timer, str) and "~" in timer:
            values = [part.strip() for part in timer.split("~", 1)]
        else:
            raise ValueError("无效的卡池时间")
        return tuple(PoolService._parse_datetime(value) for value in values)  # type: ignore[return-value]

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(value.strip(), fmt).replace(tzinfo=SHANGHAI_TZ)
            except ValueError:
                continue
        raise ValueError(f"无法解析时间：{value}")

    @staticmethod
    def _resolve_game(game_name: str | None) -> str | None:
        if not game_name:
            return None
        return GAME_ALIASES.get(game_name.strip().lower())

    @staticmethod
    def _unique_nonempty(values: list[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value for value in values if value))

    def _format_pool(self, pool: CurrentPool) -> str:
        roles = "、".join(pool.role_names) or "暂无角色信息"
        remaining = self._format_remaining(pool.end_time - self.now)
        end_label = "最近结束" if pool.has_multiple_end_times else "结束"
        return (
            f"【{GAME_LABELS[pool.game]}】{roles}\n"
            f"{end_label}：{pool.end_time:%m-%d %H:%M}（{remaining}）"
        )

    @staticmethod
    def _format_remaining(delta: Any) -> str:
        seconds = max(0, int(delta.total_seconds()))
        days, seconds = divmod(seconds, 86400)
        hours, _ = divmod(seconds, 3600)
        if days:
            return f"剩余{days}天{hours}小时"
        return f"剩余{hours}小时"
