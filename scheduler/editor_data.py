from collections import OrderedDict

from scheduler.spec_models import DAYS
from scheduler.spec_parser import parse_spec


def build_editor_data(raw_spec):
    result = parse_spec(raw_spec)
    if not result.spec:
        return {
            "lesson_blocks": [],
            "locations": [],
            "instructors": [],
            "groups": [],
        }

    return {
        "lesson_blocks": _time_range_rows(
            block.time for block in result.spec.lesson_blocks
        ),
        "locations": [
            {"name": location.name, "rooms_count": location.rooms_count}
            for location in result.spec.locations
        ],
        "instructors": [
            {
                "name": instructor.name,
                "roles": _join(instructor.roles),
                "preferred_min_classes_per_week": (
                    instructor.preferred_min_classes_per_week
                ),
                "preferred_max_classes_per_week": (
                    instructor.preferred_max_classes_per_week
                ),
                "can_teach": _join(instructor.can_teach),
                "available": _join_time_ranges(instructor.availability),
                "prefers_with": _join(instructor.prefers_with),
                "avoids_with": _join(instructor.avoids_with),
                "cannot_teach_with": _join(instructor.cannot_teach_with),
            }
            for instructor in result.spec.instructors
        ],
        "groups": [
            {
                "name": group.name,
                "lessons_per_week": group.lessons_per_week,
                "duration_minutes": group.duration_minutes,
                "teacher_roles": _join(group.teacher_roles),
                "time_windows": _join_time_ranges(group.time_windows),
            }
            for group in result.spec.groups
        ],
    }


def _join(values):
    return ", ".join(values)


def _join_time_ranges(time_ranges):
    return ", ".join(
        f"{row['days']} {row['start']}-{row['end']}"
        for row in _time_range_rows(time_ranges)
    )


def _time_range_rows(time_ranges):
    ranges_by_time = OrderedDict()
    for time_range in time_ranges:
        key = (time_range.start, time_range.end)
        ranges_by_time.setdefault(key, []).append(time_range.day)

    rows = []
    for (start, end), days in ranges_by_time.items():
        for day_range in _day_ranges(days):
            rows.append({"days": day_range, "start": start, "end": end})
    return rows


def _day_ranges(days):
    indexes = sorted(DAYS.index(day) for day in set(days))
    if not indexes:
        return []

    ranges = []
    start = indexes[0]
    previous = indexes[0]

    for index in indexes[1:]:
        if index == previous + 1:
            previous = index
            continue
        ranges.append(_format_day_range(start, previous))
        start = index
        previous = index

    ranges.append(_format_day_range(start, previous))
    return ranges


def _format_day_range(start, end):
    if start == end:
        return DAYS[start]
    return f"{DAYS[start]}-{DAYS[end]}"
