from scheduler.spec_models import (
    DAYS,
    Group,
    Instructor,
    LessonBlock,
    Location,
    ScheduleSpec,
    SpecError,
    TimeRange,
    ValidationResult,
    is_hhmm_time,
)


GROUP_REQUIRED = (
    ("lessons_per_week", "lessons per week"),
    ("duration_minutes", "duration"),
    ("teacher_roles", "teacher roles"),
)


INVALID_NUMBER = object()


def parse_spec(text):
    errors = []
    lesson_blocks = []
    locations = []
    instructors = []
    groups = []
    section = None
    item = None

    def finish_item():
        nonlocal item

        if section == "location" and item is not None:
            if item["rooms_count"] is None:
                errors.append(
                    SpecError(item["line"], f"Location {item['name']} is missing rooms")
                )
            elif item["rooms_count"] is not INVALID_NUMBER:
                locations.append(
                    Location(
                        name=item["name"],
                        rooms_count=item["rooms_count"],
                        line=item["line"],
                    )
                )

        if section == "instructor" and item is not None:
            instructors.append(
                Instructor(
                    name=item["name"],
                    roles=tuple(item["roles"]),
                    preferred_min_classes_per_week=item[
                        "preferred_min_classes_per_week"
                    ],
                    preferred_max_classes_per_week=item[
                        "preferred_max_classes_per_week"
                    ],
                    can_teach=tuple(item["can_teach"]),
                    availability=tuple(item["availability"]),
                    prefers_with=tuple(item["prefers_with"]),
                    avoids_with=tuple(item["avoids_with"]),
                    cannot_teach_with=tuple(item["cannot_teach_with"]),
                    line=item["line"],
                )
            )

        if section == "group" and item is not None:
            missing = [label for field, label in GROUP_REQUIRED if item[field] is None]
            has_invalid_number = any(
                item[field] is INVALID_NUMBER
                for field in (
                    "lessons_per_week",
                    "duration_minutes",
                )
            )
            for field in missing:
                errors.append(
                    SpecError(item["line"], f"Group {item['name']} is missing {field}")
                )
            if not missing and not has_invalid_number:
                groups.append(
                    Group(
                        name=item["name"],
                        lessons_per_week=item["lessons_per_week"],
                        duration_minutes=item["duration_minutes"],
                        teacher_roles=tuple(item["teacher_roles"]),
                        time_windows=tuple(item["time_windows"]),
                        line=item["line"],
                    )
                )

        item = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        if line == "lesson blocks":
            finish_item()
            section = "lesson_blocks"
            continue

        if line.startswith("location "):
            finish_item()
            section = "location"
            item = {
                "line": line_number,
                "name": line.removeprefix("location ").strip(),
                "rooms_count": None,
            }
            continue

        if line.startswith("instructor "):
            finish_item()
            section = "instructor"
            item = {
                "line": line_number,
                "name": line.removeprefix("instructor ").strip(),
                "roles": ("leader", "follower"),
                "preferred_min_classes_per_week": 1,
                "preferred_max_classes_per_week": 3,
                "can_teach": (),
                "availability": [],
                "prefers_with": (),
                "avoids_with": (),
                "cannot_teach_with": (),
            }
            continue

        if line.startswith("group "):
            finish_item()
            section = "group"
            item = {
                "line": line_number,
                "name": line.removeprefix("group ").strip(),
                "lessons_per_week": None,
                "duration_minutes": None,
                "teacher_roles": None,
                "time_windows": [],
            }
            continue

        if section == "lesson_blocks":
            add_ranges(lesson_blocks, line, line_number, errors, LessonBlock)
        elif section == "location" and item is not None:
            parse_location_field(item, line, line_number, errors)
        elif section == "instructor" and item is not None:
            parse_instructor_field(item, line, line_number, errors)
        elif section == "group" and item is not None:
            parse_group_field(item, line, line_number, errors)
        else:
            errors.append(SpecError(line_number, f"Unknown line: {line}"))

    finish_item()
    if errors:
        return ValidationResult(spec=None, errors=tuple(errors))

    spec = ScheduleSpec(
        lesson_blocks=tuple(lesson_blocks),
        locations=tuple(locations),
        instructors=tuple(instructors),
        groups=tuple(groups),
    )
    return ValidationResult(spec=spec, errors=tuple(errors))


def parse_location_field(location, line, line_number, errors):
    if line.startswith("rooms "):
        location["rooms_count"] = parse_int(
            line.removeprefix("rooms "),
            line_number,
            errors,
            "Rooms",
        )
    else:
        errors.append(SpecError(line_number, f"Unknown line: {line}"))


def parse_instructor_field(instructor, line, line_number, errors):
    if line.startswith("roles "):
        instructor["roles"] = parse_list(line.removeprefix("roles "))
    elif line.startswith("prefers minimum "):
        parse_instructor_int(
            instructor,
            "preferred_min_classes_per_week",
            line,
            line_number,
            errors,
            "prefers minimum ",
            "Preferred minimum classes per week",
        )
    elif line.startswith("prefers maximum "):
        parse_instructor_int(
            instructor,
            "preferred_max_classes_per_week",
            line,
            line_number,
            errors,
            "prefers maximum ",
            "Preferred maximum classes per week",
        )
    elif line.startswith("can teach "):
        instructor["can_teach"] = parse_list(line.removeprefix("can teach "))
    elif line.startswith("available "):
        add_ranges(
            instructor["availability"],
            line.removeprefix("available ").strip(),
            line_number,
            errors,
        )
    elif line.startswith("prefers teaching with "):
        instructor["prefers_with"] = parse_list(
            line.removeprefix("prefers teaching with ")
        )
    elif line.startswith("avoids teaching with "):
        instructor["avoids_with"] = parse_list(
            line.removeprefix("avoids teaching with ")
        )
    elif line.startswith("cannot teach with "):
        instructor["cannot_teach_with"] = parse_list(
            line.removeprefix("cannot teach with ")
        )
    else:
        errors.append(SpecError(line_number, f"Unknown line: {line}"))


def parse_instructor_int(instructor, field, line, line_number, errors, prefix, label):
    value = strip_suffix(
        line.removeprefix(prefix),
        (" class per week", " classes per week"),
    )
    if value is None:
        errors.append(SpecError(line_number, f"Unknown line: {line}"))
    else:
        instructor[field] = parse_int(value, line_number, errors, label)


def parse_group_field(group, line, line_number, errors):
    if line.startswith("needs "):
        parse_group_int(
            group,
            "lessons_per_week",
            line,
            line_number,
            errors,
            "needs ",
            (" lesson per week", " lessons per week"),
            "Lessons per week",
        )
    elif line.startswith("duration "):
        parse_group_int(
            group,
            "duration_minutes",
            line,
            line_number,
            errors,
            "duration ",
            (" minute", " minutes"),
            "Duration",
        )
    elif line.startswith("teacher roles "):
        group["teacher_roles"] = parse_list(line.removeprefix("teacher roles "))
    elif line.startswith("time window "):
        add_ranges(
            group["time_windows"],
            line.removeprefix("time window ").strip(),
            line_number,
            errors,
        )
    else:
        errors.append(SpecError(line_number, f"Unknown line: {line}"))


def parse_group_int(group, field, line, line_number, errors, prefix, suffixes, label):
    value = strip_suffix(line.removeprefix(prefix), suffixes)
    if value is None:
        errors.append(SpecError(line_number, f"Unknown line: {line}"))
    else:
        group[field] = parse_int(value, line_number, errors, label)


def add_ranges(target, line, line_number, errors, wrapper=None):
    time_ranges, line_errors = parse_time_ranges(line, line_number)
    errors.extend(line_errors)
    for time_range in time_ranges:
        target.append(
            wrapper(time_range, line=line_number) if wrapper else time_range
        )


def parse_time_ranges(line, line_number):
    parts = line.split()
    if len(parts) != 2 or "-" not in parts[1]:
        return (), (SpecError(line_number, f"Unknown line: {line}"),)

    day_text, time_text = parts
    days, day_error = expand_days(day_text, line_number)
    if day_error is not None:
        return (), (day_error,)

    start, end = time_text.split("-", 1)
    if not start or not end:
        return (), (SpecError(line_number, f"Unknown line: {line}"),)
    if not is_time_text(start) or not is_time_text(end):
        return (), (SpecError(line_number, f"Invalid lesson block: {line}"),)

    try:
        TimeRange(day=days[0], start=start, end=end).duration_minutes
    except ValueError as error:
        return (), (SpecError(line_number, str(error)),)

    return tuple(TimeRange(day=day, start=start, end=end) for day in days), ()


def is_time_text(value):
    return is_hhmm_time(value)


def expand_days(day_text, line_number):
    if "-" not in day_text:
        if day_text not in DAYS:
            return (), SpecError(line_number, f"Unknown day: {day_text}")
        return (day_text,), None

    start_day, end_day = day_text.split("-", 1)
    if start_day not in DAYS:
        return (), SpecError(line_number, f"Unknown day: {start_day}")
    if end_day not in DAYS:
        return (), SpecError(line_number, f"Unknown day: {end_day}")

    start_index = DAYS.index(start_day)
    end_index = DAYS.index(end_day)
    if start_index > end_index:
        return (), SpecError(line_number, f"Unknown day: {day_text}")

    return tuple(DAYS[start_index : end_index + 1]), None


def parse_int(value, line_number, errors, label):
    stripped = value.strip()
    try:
        return int(stripped)
    except ValueError:
        errors.append(
            SpecError(line_number, f"{label} must be a whole number: {stripped}")
        )
        return INVALID_NUMBER


def parse_list(value):
    return tuple(item.strip() for item in value.split(",") if item.strip())


def strip_suffix(value, suffixes):
    for suffix in suffixes:
        if value.endswith(suffix):
            return value.removesuffix(suffix).strip()
    return None
