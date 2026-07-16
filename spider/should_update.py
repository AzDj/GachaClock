import json
import os
from datetime import datetime
from pathlib import Path

from spider.arknights_current import get_arknights_maintenance_end_time
from spider.pool_time import LOCAL_TIMEZONE, extract_end_time


DATA_DIR = Path(__file__).resolve().parent / "data"
AUTO_GAMES = ["zzz", "sr", "ww", "ys", "arknights"]
MANUAL_GAMES = ["endfield"]
ALL_GAMES = AUTO_GAMES + MANUAL_GAMES


def parse_bool(value):
    return str(value or "").lower() in {"1", "true", "yes", "y"}


def parse_force_games(value):
    normalized_value = str(value or "auto").strip().lower()
    if normalized_value in {"auto", ""}:
        return AUTO_GAMES
    if normalized_value == "all":
        return ALL_GAMES

    selected_games = []
    for game in normalized_value.split(","):
        normalized_game = game.strip()
        if not normalized_game:
            continue
        if normalized_game not in ALL_GAMES:
            raise ValueError(f"不支持的游戏标识：{normalized_game}")
        if normalized_game not in selected_games:
            selected_games.append(normalized_game)

    if not selected_games:
        raise ValueError("手动刷新游戏不能为空")

    return selected_games


def resolve_data_file(relative_path):
    normalized_path = str(relative_path).replace("\\", "/")
    if normalized_path.startswith("data/"):
        normalized_path = normalized_path[len("data/") :]
    return DATA_DIR / normalized_path


def get_game_end_time(game, relative_path, current_time=None):
    data_file = resolve_data_file(relative_path)
    with data_file.open("r", encoding="utf-8") as file:
        pool_list = json.load(file)

    if game == "arknights":
        return get_arknights_maintenance_end_time(
            pool_list,
            current_time or datetime.now(LOCAL_TIMEZONE),
        )

    end_time_list = [
        end_time
        for end_time in (extract_end_time(pool.get("timer")) for pool in pool_list)
        if end_time is not None
    ]
    if not end_time_list:
        raise ValueError(f"{game} 没有可解析的当前卡池结束时间：{relative_path}")

    return max(end_time_list)


def write_github_output(result):
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return

    with open(output_path, "a", encoding="utf-8") as output_file:
        for key, value in result.items():
            output_file.write(f"{key}={value}\n")


def main():
    force_update = parse_bool(os.getenv("FORCE_UPDATE"))
    force_games = parse_force_games(os.getenv("FORCE_GAMES"))
    now = datetime.now(LOCAL_TIMEZONE)

    if force_update:
        game_text = "全部游戏" if force_games == ALL_GAMES else "、".join(force_games)
        result = {
            "should_run": "true",
            "games": ",".join(force_games),
            "reason": f"强制触发，抓取游戏：{game_text}",
        }
        write_github_output(result)
        print(result["reason"])
        return

    meta_file = DATA_DIR / "meta.json"
    with meta_file.open("r", encoding="utf-8") as file:
        meta = json.load(file)

    due_games = []
    status_messages = []
    for game in AUTO_GAMES:
        if game not in meta:
            due_games.append(game)
            status_messages.append(f"{game}: meta 缺失，纳入维护")
            continue

        end_time = get_game_end_time(game, meta[game], now)
        if end_time is None:
            due_games.append(game)
            status_messages.append(f"{game}: 没有当前限时卡池结束时间，纳入维护")
        elif now >= end_time:
            due_games.append(game)
            status_messages.append(f"{game}: 已到期 {end_time.isoformat()}")
        else:
            status_messages.append(f"{game}: 未到期 {end_time.isoformat()}")

    result = {
        "should_run": "true" if due_games else "false",
        "games": ",".join(due_games),
        "reason": "；".join(status_messages),
    }
    write_github_output(result)
    print(result["reason"])


if __name__ == "__main__":
    main()
