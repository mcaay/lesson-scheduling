from itertools import combinations

from scheduler.spec_models import (
    TEACHER_ROLES,
    SpecError,
    instructor_can_teach_group,
    to_slot,
)


def validate_spec(spec):
    errors = []

    if not spec.locations:
        return [SpecError(None, "At least one location is required")]

    for location in spec.locations:
        if location.rooms_count < 1:
            errors.append(
                SpecError(None, f"Location {location.name} must have at least one room")
            )

    instructor_names = {instructor.name for instructor in spec.instructors}
    for instructor in spec.instructors:
        if (
            instructor.preferred_min_classes_per_week
            > instructor.preferred_max_classes_per_week
        ):
            errors.append(
                SpecError(
                    None,
                    f"Instructor {instructor.name} preferred minimum classes per week "
                    "cannot be higher than preferred maximum",
                )
            )

        for referenced_name in _referenced_instructor_names(instructor):
            if referenced_name not in instructor_names:
                errors.append(
                    SpecError(
                        None,
                        f"Instructor {instructor.name} references unknown "
                        f"instructor {referenced_name}",
                    )
                )

    for group in spec.groups:
        eligible_instructors = [
            instructor
            for instructor in spec.instructors
            if instructor_can_teach_group(instructor, group)
            and instructor.preferred_max_classes_per_week > 0
        ]

        if group.teachers_required not in {1, 2}:
            errors.append(
                SpecError(
                    None,
                    f"Group {group.name} must require one or two teacher roles",
                )
            )
            continue

        invalid_roles = [
            role for role in group.teacher_roles if role not in TEACHER_ROLES
        ]
        if invalid_roles:
            errors.append(
                SpecError(
                    None,
                    f"Group {group.name} uses unsupported teacher role {invalid_roles[0]}",
                )
            )
            continue

        missing_role = _first_missing_role(group, eligible_instructors)
        if missing_role:
            errors.append(_missing_role_error(group, missing_role))
            continue

        if group.teachers_required == 2 and not _has_allowed_role_pair(
            eligible_instructors, group.teacher_roles
        ):
            errors.append(
                SpecError(
                    None,
                    f"Group {group.name} needs two teachers, but every eligible role pair is banned",
                )
            )
            continue

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


def _referenced_instructor_names(instructor):
    return (
        instructor.prefers_with
        + instructor.avoids_with
        + instructor.cannot_teach_with
    )


def _first_missing_role(group, eligible_instructors):
    for role in group.teacher_roles:
        if not any(role in instructor.roles for instructor in eligible_instructors):
            return role
    return None


def _missing_role_error(group, role):
    return SpecError(
        None,
        f"Group {group.name} needs a {role} teacher, but none are eligible",
    )


def _has_allowed_role_pair(instructors, roles):
    first_role, second_role = roles
    for first, second in combinations(instructors, 2):
        if _pair_is_banned(first, second):
            continue
        if first_role in first.roles and second_role in second.roles:
            return True
        if first_role in second.roles and second_role in first.roles:
            return True
    return False


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
        if group.teachers_required == 1 and _first_missing_role(
            group, available_instructors
        ) is None:
            return True

        if group.teachers_required == 2 and _has_allowed_role_pair(
            available_instructors, group.teacher_roles
        ):
            return True

    return False


def _instructor_covers_block(instructor, lesson_block):
    return any(
        availability.day == lesson_block.time.day
        and to_slot(availability.start) <= to_slot(lesson_block.time.start)
        and to_slot(availability.end) >= to_slot(lesson_block.time.end)
        for availability in instructor.availability
    )
