from collections import defaultdict

from spider.pool_time import (
    extract_end_time,
    extract_start_time,
    is_timer_ambiguous_and_unexpired,
    is_timer_overlapping_current_day,
    is_timer_started_and_unexpired,
)


ARKNIGHTS_POSITION_SECTIONS = {
    "限时寻访",
    "常驻标准寻访",
    "常驻中坚寻访&中坚甄选",
}


def select_current_arknights_items(pool_list, current_time):
    active_items = [
        pool
        for pool in pool_list
        if is_timer_started_and_unexpired(pool.get("timer"), current_time)
    ]
    if active_items:
        return active_items

    same_day_items = [
        pool
        for pool in pool_list
        if is_timer_overlapping_current_day(pool.get("timer"), current_time)
    ]
    if same_day_items:
        return same_day_items

    return [
        pool
        for pool in pool_list
        if is_timer_ambiguous_and_unexpired(pool.get("timer"), current_time)
    ]


def get_arknights_maintenance_end_time(pool_list, current_time):
    current_items = select_current_arknights_items(pool_list, current_time)
    end_time_list = [
        end_time
        for end_time in (extract_end_time(pool.get("timer")) for pool in current_items)
        if end_time is not None
    ]

    if not end_time_list:
        return None

    return min(end_time_list)


def merge_arknights_history_items(existing_items, fetched_items, current_time):
    protected_position_map = defaultdict(list)
    for item in select_current_arknights_items(existing_items, current_time):
        position_key = get_arknights_position_key(item)
        if position_key is not None:
            protected_position_map[position_key].append(item)

    emitted_protected_positions = set()
    seen_keys = set()
    merged_items = []

    for item in fetched_items:
        position_key = get_arknights_position_key(item)
        if position_key in protected_position_map:
            if position_key not in emitted_protected_positions:
                for protected_item in protected_position_map[position_key]:
                    merged_items.append(protected_item)
                    seen_keys.add(get_arknights_item_key(protected_item))
                emitted_protected_positions.add(position_key)
            seen_keys.add(get_arknights_item_key(item))
            continue

        merged_items.append(item)
        seen_keys.add(get_arknights_item_key(item))

    for item in existing_items:
        item_key = get_arknights_item_key(item)
        if item_key not in seen_keys:
            merged_items.append(item)
            seen_keys.add(item_key)

    return merged_items


def get_arknights_position_key(item):
    section = get_arknights_section(item)
    if section not in ARKNIGHTS_POSITION_SECTIONS:
        return None

    start_time = extract_start_time(item.get("timer"))
    if start_time is None:
        return None

    return section, start_time.isoformat()


def get_arknights_section(item):
    version = str(item.get("version", ""))
    if " " not in version:
        return version

    return version.split(" ", 1)[1]


def get_arknights_item_key(item):
    s_value = item.get("s")
    if isinstance(s_value, list):
        s_value = ",".join(sorted(str(value) for value in s_value))

    return (
        str(item.get("title", "")),
        str(item.get("version", "")),
        str(item.get("timer", "")),
        str(s_value or ""),
    )
