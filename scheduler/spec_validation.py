from itertools import combinations

from scheduler.spec_limits import (
    MAX_DURATION_MINUTES,
    MAX_GROUPS,
    MAX_INSTRUCTORS,
    MAX_LESSON_BLOCKS,
    MAX_LESSONS_PER_GROUP,
    MAX_LOCATIONS,
    MAX_PREFERRED_CLASSES_PER_WEEK,
    MAX_ROOMS_PER_LOCATION,
    MAX_SOLVER_CANDIDATES,
)
from scheduler.spec_models import (
    TEACHER_ROLES,
    SpecError,
    instructor_can_teach_group,
    to_slot,
)


def validate_spec(spec):
    errors = []
    errors.extend(_collection_errors(spec))
    errors.extend(_duplicate_name_errors(spec.locations, "Location"))
    errors.extend(_duplicate_name_errors(spec.instructors, "Instructor"))
    errors.extend(_duplicate_name_errors(spec.groups, "Group"))

    for location in spec.locations:
        errors.extend(_location_errors(location))

    instructor_names = {instructor.name for instructor in spec.instructors}
    for instructor in spec.instructors:
        errors.extend(_instructor_errors(instructor, instructor_names))

    for group in spec.groups:
        errors.extend(_group_errors(spec, group))

    if not errors:
        candidate_count = estimate_candidate_count(
            spec,
            stop_after=MAX_SOLVER_CANDIDATES,
        )
        if candidate_count > MAX_SOLVER_CANDIDATES:
            errors.append(
                SpecError(
                    None,
                    "This project creates too many possible assignments "
                    f"({candidate_count:,}; limit {MAX_SOLVER_CANDIDATES:,}). "
                    "Reduce rooms, lesson blocks, eligible instructors, or groups.",
                )
            )

    return errors


def _collection_errors(spec):
    errors = []
    collections = (
        (spec.lesson_blocks, "lesson block", MAX_LESSON_BLOCKS),
        (spec.locations, "location", MAX_LOCATIONS),
        (spec.instructors, "instructor", MAX_INSTRUCTORS),
        (spec.groups, "group", MAX_GROUPS),
    )
    for values, label, maximum in collections:
        if not values:
            errors.append(SpecError(None, f"At least one {label} is required"))
        elif len(values) > maximum:
            errors.append(
                SpecError(
                    None,
                    f"At most {maximum} {label}s are allowed; found {len(values)}",
                )
            )
    return errors


def _duplicate_name_errors(items, label):
    errors = []
    seen = set()
    for item in items:
        if item.name in seen:
            errors.append(
                SpecError(
                    item.line,
                    f"{label} name {item.name} is declared more than once",
                )
            )
        seen.add(item.name)
    return errors


def _name_errors(item, label, *, referenced=False):
    if not item.name.strip():
        return [SpecError(item.line, f"{label} name cannot be empty")]
    if referenced and any(character in item.name for character in (",", "\n", "\r")):
        return [
            SpecError(
                item.line,
                f"{label} name {item.name} cannot contain commas or line breaks",
            )
        ]
    return []


def _location_errors(location):
    errors = _name_errors(location, "Location")
    if location.rooms_count < 1:
        errors.append(
            SpecError(
                location.line,
                f"Location {location.name} must have at least one room",
            )
        )
    elif location.rooms_count > MAX_ROOMS_PER_LOCATION:
        errors.append(
            SpecError(
                location.line,
                f"Location {location.name} cannot have more than "
                f"{MAX_ROOMS_PER_LOCATION} rooms",
            )
        )
    return errors


def _instructor_errors(instructor, instructor_names):
    errors = _name_errors(instructor, "Instructor", referenced=True)
    invalid_roles = [role for role in instructor.roles if role not in TEACHER_ROLES]
    if not instructor.roles:
        errors.append(
            SpecError(instructor.line, f"Instructor {instructor.name} needs at least one role")
        )
    elif invalid_roles:
        errors.append(
            SpecError(
                instructor.line,
                f"Instructor {instructor.name} uses unsupported role {invalid_roles[0]}",
            )
        )
    elif len(set(instructor.roles)) != len(instructor.roles):
        errors.append(
            SpecError(instructor.line, f"Instructor {instructor.name} repeats a role")
        )

    minimum = instructor.preferred_min_classes_per_week
    maximum = instructor.preferred_max_classes_per_week
    if minimum < 0:
        errors.append(
            SpecError(
                instructor.line,
                f"Instructor {instructor.name} preferred minimum cannot be negative",
            )
        )
    elif minimum > MAX_PREFERRED_CLASSES_PER_WEEK:
        errors.append(
            SpecError(
                instructor.line,
                f"Instructor {instructor.name} preferred minimum cannot exceed "
                f"{MAX_PREFERRED_CLASSES_PER_WEEK}",
            )
        )

    if maximum < 0:
        errors.append(
            SpecError(
                instructor.line,
                f"Instructor {instructor.name} preferred maximum cannot be negative",
            )
        )
    elif maximum > MAX_PREFERRED_CLASSES_PER_WEEK:
        errors.append(
            SpecError(
                instructor.line,
                f"Instructor {instructor.name} preferred maximum cannot exceed "
                f"{MAX_PREFERRED_CLASSES_PER_WEEK}",
            )
        )
    elif maximum != 0 and minimum > maximum:
        errors.append(
            SpecError(
                instructor.line,
                f"Instructor {instructor.name} preferred minimum classes per week "
                "cannot be higher than preferred maximum",
            )
        )

    referenced_names = _referenced_instructor_names(instructor)
    for referenced_name in referenced_names:
        if referenced_name not in instructor_names:
            errors.append(
                SpecError(
                    instructor.line,
                    f"Instructor {instructor.name} references unknown "
                    f"instructor {referenced_name}",
                )
            )
        elif referenced_name == instructor.name:
            errors.append(
                SpecError(
                    instructor.line,
                    f"Instructor {instructor.name} cannot reference themselves",
                )
            )

    contradictory_names = set(instructor.prefers_with) & (
        set(instructor.avoids_with) | set(instructor.cannot_teach_with)
    )
    for name in sorted(contradictory_names):
        errors.append(
            SpecError(
                instructor.line,
                f"Instructor {instructor.name} has contradictory preferences for {name}",
            )
        )
    return errors


def _group_errors(spec, group):
    errors = _name_errors(group, "Group", referenced=True)
    if group.lessons_per_week < 1:
        errors.append(
            SpecError(
                group.line,
                f"Group {group.name} must need at least one lesson per week",
            )
        )
    elif group.lessons_per_week > MAX_LESSONS_PER_GROUP:
        errors.append(
            SpecError(
                group.line,
                f"Group {group.name} cannot need more than "
                f"{MAX_LESSONS_PER_GROUP} lessons per week",
            )
        )

    if group.duration_minutes < 5:
        errors.append(
            SpecError(group.line, f"Group {group.name} duration must be at least 5 minutes")
        )
    elif group.duration_minutes > MAX_DURATION_MINUTES:
        errors.append(
            SpecError(
                group.line,
                f"Group {group.name} duration cannot exceed {MAX_DURATION_MINUTES} minutes",
            )
        )
    elif group.duration_minutes % 5:
        errors.append(
            SpecError(
                group.line,
                f"Group {group.name} duration must use 5-minute steps",
            )
        )

    roles_are_valid = True
    if group.teachers_required not in {1, 2}:
        errors.append(
            SpecError(
                group.line,
                f"Group {group.name} must require one or two teacher roles",
            )
        )
        roles_are_valid = False
    else:
        invalid_roles = [role for role in group.teacher_roles if role not in TEACHER_ROLES]
        if invalid_roles:
            errors.append(
                SpecError(
                    group.line,
                    f"Group {group.name} uses unsupported teacher role {invalid_roles[0]}",
                )
            )
            roles_are_valid = False
        elif len(set(group.teacher_roles)) != len(group.teacher_roles):
            errors.append(
                SpecError(group.line, f"Group {group.name} repeats a teacher role")
            )
            roles_are_valid = False

    if not roles_are_valid or group.duration_minutes < 5 or group.duration_minutes % 5:
        return errors

    eligible_instructors = [
        instructor
        for instructor in spec.instructors
        if instructor_can_teach_group(instructor, group)
        and instructor.preferred_max_classes_per_week > 0
    ]
    missing_role = _first_missing_role(group, eligible_instructors)
    pair_is_possible = True
    if missing_role:
        errors.append(_missing_role_error(group, missing_role))
        pair_is_possible = False
    elif group.teachers_required == 2:
        if not _has_role_pair(eligible_instructors, group.teacher_roles, allow_banned=True):
            errors.append(
                SpecError(
                    group.line,
                    f"Group {group.name} needs two distinct teachers, but too few "
                    "eligible instructors can fill the roles",
                )
            )
            pair_is_possible = False
        elif not _has_role_pair(eligible_instructors, group.teacher_roles):
            errors.append(
                SpecError(
                    group.line,
                    f"Group {group.name} needs two teachers, but every eligible "
                    "role pair is banned",
                )
            )
            pair_is_possible = False

    matching_blocks = [
        lesson_block
        for lesson_block in spec.lesson_blocks
        if _group_allows_block(group, lesson_block)
        and lesson_block.duration_minutes == group.duration_minutes
    ]
    if not matching_blocks:
        errors.append(
            SpecError(
                group.line,
                f"Group {group.name} has no lesson block matching its duration and time windows",
            )
        )
    elif not missing_role and pair_is_possible and not _has_assignable_block(
        matching_blocks,
        group,
        eligible_instructors,
    ):
        errors.append(
            SpecError(
                group.line,
                f"Group {group.name} has no matching lesson block with all "
                "required instructors available",
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
        group.line,
        f"Group {group.name} needs a {role} teacher, but none are eligible",
    )


def _has_role_pair(instructors, roles, *, allow_banned=False):
    return any(
        (allow_banned or not _pair_is_banned(first, second))
        and _pair_can_fill_roles(first, second, roles)
        for first, second in combinations(instructors, 2)
    )


def _pair_can_fill_roles(first, second, roles):
    first_role, second_role = roles
    return (
        first_role in first.roles and second_role in second.roles
    ) or (
        first_role in second.roles and second_role in first.roles
    )


def _pair_is_banned(first, second):
    return (
        second.name in first.cannot_teach_with
        or first.name in second.cannot_teach_with
    )


def _has_assignable_block(lesson_blocks, group, eligible_instructors):
    for lesson_block in lesson_blocks:
        available_instructors = [
            instructor
            for instructor in eligible_instructors
            if _instructor_covers_block(instructor, lesson_block)
        ]
        if group.teachers_required == 1 and _first_missing_role(
            group, available_instructors
        ) is None:
            return True
        if group.teachers_required == 2 and _has_role_pair(
            available_instructors, group.teacher_roles
        ):
            return True
    return False


def estimate_candidate_count(spec, *, stop_after=None):
    total_rooms = sum(location.rooms_count for location in spec.locations)
    candidate_count = 0
    for group in spec.groups:
        eligible_instructors = [
            instructor
            for instructor in spec.instructors
            if instructor_can_teach_group(instructor, group)
            and instructor.preferred_max_classes_per_week > 0
        ]
        for lesson_block in spec.lesson_blocks:
            if not _group_allows_block(group, lesson_block):
                continue
            if lesson_block.duration_minutes != group.duration_minutes:
                continue
            available = [
                instructor
                for instructor in eligible_instructors
                if _instructor_covers_block(instructor, lesson_block)
            ]
            choices = _instructor_choice_count(available, group.teacher_roles)
            candidate_count += total_rooms * choices
            if stop_after is not None and candidate_count > stop_after:
                return candidate_count
    return candidate_count


def _instructor_choice_count(instructors, roles):
    if len(roles) == 1:
        return sum(roles[0] in instructor.roles for instructor in instructors)
    if len(roles) == 2:
        return sum(
            not _pair_is_banned(first, second)
            and _pair_can_fill_roles(first, second, roles)
            for first, second in combinations(instructors, 2)
        )
    return 0


def _group_allows_block(group, lesson_block):
    if not group.time_windows:
        return True
    return any(
        time_window.day == lesson_block.time.day
        and to_slot(time_window.start) <= to_slot(lesson_block.time.start)
        and to_slot(time_window.end) >= to_slot(lesson_block.time.end)
        for time_window in group.time_windows
    )


def _instructor_covers_block(instructor, lesson_block):
    return any(
        availability.day == lesson_block.time.day
        and to_slot(availability.start) <= to_slot(lesson_block.time.start)
        and to_slot(availability.end) >= to_slot(lesson_block.time.end)
        for availability in instructor.availability
    )
