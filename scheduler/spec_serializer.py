def serialize_spec(spec):
    lines = []
    lines.extend(_lesson_block_lines(spec.lesson_blocks))
    lines.append("")

    for location in spec.locations:
        lines.extend(
            [
                f"location {location.name}",
                f"rooms {location.rooms_count}",
                "",
            ]
        )

    for instructor in spec.instructors:
        lines.extend(_instructor_lines(instructor))
        lines.append("")

    for group in spec.groups:
        lines.extend(_group_lines(group))
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _lesson_block_lines(lesson_blocks):
    lines = ["lesson blocks"]
    for block in lesson_blocks:
        lines.append(f"{block.time.day} {block.time.start}-{block.time.end}")
    return lines


def _instructor_lines(instructor):
    lines = [f"instructor {instructor.name}"]
    if instructor.roles:
        lines.append(f"roles {', '.join(instructor.roles)}")
    lines.append(
        _plural_line(
            "prefers minimum",
            instructor.preferred_min_classes_per_week,
            "class per week",
            "classes per week",
        )
    )
    lines.append(
        _plural_line(
            "prefers maximum",
            instructor.preferred_max_classes_per_week,
            "class per week",
            "classes per week",
        )
    )
    if instructor.can_teach:
        lines.append(f"can teach {', '.join(instructor.can_teach)}")
    for availability in instructor.availability:
        lines.append(f"available {availability.day} {availability.start}-{availability.end}")
    if instructor.prefers_with:
        lines.append(f"prefers teaching with {', '.join(instructor.prefers_with)}")
    if instructor.avoids_with:
        lines.append(f"avoids teaching with {', '.join(instructor.avoids_with)}")
    if instructor.cannot_teach_with:
        lines.append(f"cannot teach with {', '.join(instructor.cannot_teach_with)}")
    return lines


def _group_lines(group):
    lines = [
        f"group {group.name}",
        f"needs {group.lessons_per_week} lesson per week",
        f"duration {group.duration_minutes} minutes",
        f"teacher roles {', '.join(group.teacher_roles)}",
    ]
    for time_window in group.time_windows:
        lines.append(
            f"time window {time_window.day} {time_window.start}-{time_window.end}"
        )
    return lines


def _plural_line(prefix, value, singular, plural):
    suffix = singular if value == 1 else plural
    return f"{prefix} {value} {suffix}"
