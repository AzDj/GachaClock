from spider.history_merge import select_current_history_items
from spider.pool_time import (
    extract_end_time,
    is_timer_started_and_unexpired,
)


ARKNIGHTS_POSITION_SECTIONS = {
    "限时寻访",
    "常驻标准寻访",
    "常驻中坚寻访&中坚甄选",
}


def get_arknights_maintenance_end_time(pool_list, current_time):
    current_items_by_section = get_current_arknights_items_by_section(pool_list, current_time)
    if any(not current_items_by_section[section] for section in ARKNIGHTS_POSITION_SECTIONS):
        return None

    end_time_list = []
    for current_items in current_items_by_section.values():
        end_time_list.extend(
            end_time
            for end_time in (extract_end_time(pool.get("timer")) for pool in current_items)
            if end_time is not None
        )

    if not end_time_list:
        return None

    return min(end_time_list)


def get_current_arknights_items_by_section(pool_list, current_time):
    current_items_by_section = {section: [] for section in ARKNIGHTS_POSITION_SECTIONS}
    for pool in pool_list:
        section = get_arknights_section(pool)
        if section not in current_items_by_section:
            continue
        if is_timer_started_and_unexpired(pool.get("timer"), current_time):
            current_items_by_section[section].append(pool)

    return current_items_by_section


def get_arknights_section(item):
    version = str(item.get("version", ""))
    if " " not in version:
        return version

    return version.split(" ", 1)[1]
