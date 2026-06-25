def serialize_spec(spec):
    lines = []
    lines.extend(_lesson_block_lines(spec.lesson_blocks))
    lines.append("")

    for room in spec.rooms:
        lines.extend([f"room {room.name}", f"capacity {room.capacity}", ""])

    for instructor in spec.instructors:
        lines.extend(_instructor_lines(instructor))
        lines.append("")

    for group in spec.groups:
        lines.extend(
            [
                f"group {group.name}",
                f"students {group.students}",
                f"style {group.style}",
                f"level {group.level}",
                f"needs {group.lessons_per_week} lesson per week",
                f"duration {group.duration_minutes} minutes",
                f"teachers {group.teachers_required}",
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def _lesson_block_lines(lesson_blocks):
    lines = ["lesson blocks"]
    for block in lesson_blocks:
        lines.append(f"{block.time.day} {block.time.start}-{block.time.end}")
    return lines


def _instructor_lines(instructor):
    lines = [f"instructor {instructor.name}"]
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
