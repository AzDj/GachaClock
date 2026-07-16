from spider.pool_time import (
    extract_end_time,
    is_timer_ambiguous_and_unexpired,
    is_timer_overlapping_current_day,
    is_timer_started_and_unexpired,
)


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
    protected_map = {
        get_arknights_item_key(item): item
        for item in select_current_arknights_items(existing_items, current_time)
    }
    seen_keys = set()
    merged_items = []

    for item in fetched_items:
        item_key = get_arknights_item_key(item)
        merged_items.append(protected_map.get(item_key, item))
        seen_keys.add(item_key)

    for item in existing_items:
        item_key = get_arknights_item_key(item)
        if item_key not in seen_keys:
            merged_items.append(item)
            seen_keys.add(item_key)

    return merged_items


def get_arknights_item_key(item):
    s_value = item.get("s")
    if isinstance(s_value, list):
        s_value = ",".join(sorted(str(value) for value in s_value))

    return (
        str(item.get("title", "")),
        str(item.get("timer", "")),
        str(s_value or ""),
    )
