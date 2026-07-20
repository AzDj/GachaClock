from spider.pool_time import (
    extract_start_time,
    is_timer_ambiguous_and_unexpired,
    is_timer_overlapping_current_day,
    is_timer_started_and_unexpired,
)


def select_current_history_items(pool_list, current_time):
    """按精确时间、当天范围和模糊时间依次选择当前卡池。"""
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


def merge_history_items(existing_items, fetched_items, current_time):
    """合并历史池，并保护抓取期间仍生效的本地卡池数据。"""
    existing_items_by_identity = {}
    for item in existing_items:
        identity = get_history_pool_identity(item)
        existing_items_by_identity.setdefault(identity, []).append(item)

    protected_identities = {
        get_history_pool_identity(item)
        for item in select_current_history_items(existing_items, current_time)
    }
    fetched_identities = {
        get_history_pool_identity(item)
        for item in fetched_items
    }

    emitted_protected_identities = set()
    merged_items = []
    for item in fetched_items:
        identity = get_history_pool_identity(item)
        if identity not in protected_identities:
            merged_items.append(item)
            continue

        if identity not in emitted_protected_identities:
            merged_items.extend(existing_items_by_identity[identity])
            emitted_protected_identities.add(identity)

    for item in existing_items:
        if get_history_pool_identity(item) not in fetched_identities:
            merged_items.append(item)

    return merged_items


def get_history_pool_identity(item):
    """生成不依赖游戏名、栏目名或卡池数量的稳定卡池身份。"""
    title = str(item.get("title", "")).strip()
    pool_type = str(item.get("type", "")).strip()
    start_time = extract_start_time(item.get("timer"))
    if title and start_time is not None:
        return pool_type, title, start_time.isoformat()

    return (
        pool_type,
        title,
        str(item.get("version", "")).strip(),
        str(item.get("timer", "")).strip(),
        _normalize_value(item.get("s")),
    )


def _normalize_value(value):
    if isinstance(value, list):
        return tuple(sorted(str(item) for item in value))
    return str(value or "")
