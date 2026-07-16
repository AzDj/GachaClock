import re
from datetime import datetime, timedelta, timezone


LOCAL_TIMEZONE = timezone(timedelta(hours=8))


def ensure_local_timezone(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=LOCAL_TIMEZONE)

    return value.astimezone(LOCAL_TIMEZONE)


def parse_datetime(value):
    normalized_value = re.sub(r"\s+", " ", str(value or "").strip())
    normalized_value = normalized_value.replace("-", "/")
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(normalized_value, fmt).replace(tzinfo=LOCAL_TIMEZONE)
        except ValueError:
            continue
    return None


def get_timer_range(timer):
    if isinstance(timer, list) and len(timer) >= 2:
        return parse_datetime(timer[0]), parse_datetime(timer[-1])

    if isinstance(timer, str) and "~" in timer:
        start_timer, end_timer = timer.split("~", 1)
        return parse_datetime(start_timer), parse_datetime(end_timer)

    return None, None


def extract_end_time(timer):
    return get_timer_range(timer)[1]


def extract_start_time(timer):
    return get_timer_range(timer)[0]


def is_timer_started_and_unexpired(timer, current_time):
    start_time, end_time = get_timer_range(timer)
    local_current_time = ensure_local_timezone(current_time)

    return (
        start_time is not None
        and start_time <= local_current_time
        and (end_time is None or local_current_time <= end_time)
    )


def is_timer_ambiguous_and_unexpired(timer, current_time):
    start_time, end_time = get_timer_range(timer)
    local_current_time = ensure_local_timezone(current_time)

    return start_time is None and end_time is not None and local_current_time <= end_time


def is_timer_overlapping_current_day(timer, current_time):
    start_time, end_time = get_timer_range(timer)
    day_start, day_end = get_local_day_range(current_time)

    return is_range_overlapping(start_time, end_time, day_start, day_end)


def get_local_day_range(current_time):
    local_current_time = ensure_local_timezone(current_time)
    day_start = datetime(
        local_current_time.year,
        local_current_time.month,
        local_current_time.day,
        tzinfo=LOCAL_TIMEZONE,
    )
    day_end = day_start + timedelta(days=1) - timedelta(microseconds=1)

    return day_start, day_end


def is_range_overlapping(start_time, end_time, target_start, target_end):
    if end_time is not None and end_time < target_start:
        return False

    if start_time is not None and target_end < start_time:
        return False

    return True
