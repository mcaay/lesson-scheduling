from itertools import combinations

from scheduler.spec_models import SpecError, to_slot


def validate_spec(spec):
    errors = []

    if not spec.rooms:
        return [SpecError(None, "At least one room is required")]

    for group in spec.groups:
        eligible_instructors = [
            instructor
            for instructor in spec.instructors
            if group.teaching_key in instructor.can_teach
        ]

        if all(room.capacity < group.students for room in spec.rooms):
            errors.append(
                SpecError(
                    None,
                    f"Group {group.name} has {group.students} students, "
                    "but no room can hold that many",
                )
            )

        if len(eligible_instructors) < group.teachers_required:
            eligible_count = len(eligible_instructors)
            instructor_text = (
                "eligible instructor is available"
                if eligible_count == 1
                else "eligible instructors are available"
            )
            errors.append(
                SpecError(
                    None,
                    f"Group {group.name} needs {group.teachers_required} teachers, "
                    f"but only {eligible_count} {instructor_text}",
                )
            )
            continue

        if group.teachers_required == 2 and not _has_allowed_pair(
            eligible_instructors
        ):
            errors.append(
                SpecError(
                    None,
                    f"Group {group.name} needs two teachers, but every eligible pair is banned",
                )
            )

        if not _has_matching_lesson_block(
            spec.lesson_blocks, group, eligible_instructors
        ):
            errors.append(
                SpecError(
                    None,
                    f"Group {group.name} has no lesson block that matches "
                    "duration and instructor availability",
                )
            )

    return errors


def _has_allowed_pair(instructors):
    return any(
        not _pair_is_banned(first, second)
        for first, second in combinations(instructors, 2)
    )


def _pair_is_banned(first, second):
    return (
        second.name in first.cannot_teach_with
        or first.name in second.cannot_teach_with
    )


def _has_matching_lesson_block(lesson_blocks, group, eligible_instructors):
    for lesson_block in lesson_blocks:
        if lesson_block.duration_minutes != group.duration_minutes:
            continue

        available_instructors = [
            instructor
            for instructor in eligible_instructors
            if _instructor_covers_block(instructor, lesson_block)
        ]
        if group.teachers_required == 1 and available_instructors:
            return True

        if group.teachers_required == 2 and _has_allowed_pair(available_instructors):
            return True

    return False


def _instructor_covers_block(instructor, lesson_block):
    return any(
        availability.day == lesson_block.time.day
        and to_slot(availability.start) <= to_slot(lesson_block.time.start)
        and to_slot(availability.end) >= to_slot(lesson_block.time.end)
        for availability in instructor.availability
    )
