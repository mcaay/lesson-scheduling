from dataclasses import dataclass
from itertools import combinations

from ortools.sat.python import cp_model

from scheduler.spec_models import instructor_can_teach_group, to_slot


UNSOLVED_MESSAGE = "No complete schedule found. The combined constraints are too tight."
MIN_TRAVEL_MINUTES_BETWEEN_LOCATIONS = 60
SOLVER_TIME_LIMIT_SECONDS = 120


@dataclass(frozen=True)
class ScheduledLesson:
    group_name: str
    day: str
    start: str
    end: str
    location_name: str
    room_index: int
    instructor_names: tuple[str, ...]


@dataclass(frozen=True)
class SolveResult:
    solved: bool
    lessons: tuple[ScheduledLesson, ...] = ()
    message: str = ""


@dataclass(frozen=True)
class _Candidate:
    group: object
    location: object
    room_index: int
    lesson_block: object
    instructors: tuple[object, ...]
    preference_score: int


def solve_schedule(spec):
    candidates = _build_candidates(spec)
    model = cp_model.CpModel()
    variables = [
        model.NewBoolVar(f"candidate_{index}")
        for index, _candidate in enumerate(candidates)
    ]

    _add_group_requirements(model, variables, candidates, spec.groups)
    _add_resource_conflicts(model, variables, candidates)

    preference_terms = [
        candidate.preference_score * variables[index]
        for index, candidate in enumerate(candidates)
        if candidate.preference_score
    ]
    preference_terms.extend(
        _instructor_load_preference_terms(model, variables, candidates, spec.instructors)
    )
    if preference_terms:
        model.Maximize(sum(preference_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return SolveResult(False, message=UNSOLVED_MESSAGE)

    lessons = tuple(
        _candidate_to_lesson(candidate)
        for index, candidate in enumerate(candidates)
        if solver.BooleanValue(variables[index])
    )
    return SolveResult(True, lessons=lessons)


def _build_candidates(spec):
    candidates = []
    for group in spec.groups:
        for location in spec.locations:
            for room_index in range(1, location.rooms_count + 1):
                candidates.extend(
                    _build_location_room_candidates(group, location, room_index, spec)
                )
    return tuple(candidates)


def _build_location_room_candidates(group, location, room_index, spec):
    candidates = []
    for lesson_block in spec.lesson_blocks:
        if not _group_allows_block(group, lesson_block):
            continue
        if lesson_block.duration_minutes != group.duration_minutes:
            continue
        for instructors in _instructor_choices(
            spec.instructors, group, lesson_block
        ):
            candidates.append(
                _Candidate(
                    group=group,
                    location=location,
                    room_index=room_index,
                    lesson_block=lesson_block,
                    instructors=instructors,
                    preference_score=_preference_score(instructors),
                )
            )
    return candidates


def _group_allows_block(group, lesson_block):
    if not group.time_windows:
        return True
    return any(
        time_window.day == lesson_block.time.day
        and to_slot(time_window.start) <= to_slot(lesson_block.time.start)
        and to_slot(time_window.end) >= to_slot(lesson_block.time.end)
        for time_window in group.time_windows
    )


def _instructor_choices(instructors, group, lesson_block):
    eligible = [
        instructor
        for instructor in instructors
        if instructor_can_teach_group(instructor, group)
        and instructor.preferred_max_classes_per_week > 0
        and _covers_block(instructor, lesson_block)
    ]

    if len(group.teacher_roles) == 1:
        role = group.teacher_roles[0]
        return tuple(
            (instructor,) for instructor in eligible if role in instructor.roles
        )

    if len(group.teacher_roles) == 2:
        return _role_pairs(eligible, group.teacher_roles)

    return ()


def _role_pairs(instructors, roles):
    first_role, second_role = roles
    pairs = []
    seen = set()
    for first, second in combinations(instructors, 2):
        if _pair_is_banned(first, second):
            continue
        if first_role in first.roles and second_role in second.roles:
            key = tuple(sorted([first.name, second.name]))
            if key not in seen:
                pairs.append((first, second))
                seen.add(key)
            continue
        if first_role in second.roles and second_role in first.roles:
            key = tuple(sorted([first.name, second.name]))
            if key not in seen:
                pairs.append((second, first))
                seen.add(key)
    return tuple(pairs)


def _covers_block(instructor, lesson_block):
    return any(
        availability.day == lesson_block.time.day
        and to_slot(availability.start) <= to_slot(lesson_block.time.start)
        and to_slot(availability.end) >= to_slot(lesson_block.time.end)
        for availability in instructor.availability
    )


def _pair_is_banned(first, second):
    return (
        second.name in first.cannot_teach_with
        or first.name in second.cannot_teach_with
    )


def _add_group_requirements(model, variables, candidates, groups):
    for group in groups:
        indices = [
            index
            for index, candidate in enumerate(candidates)
            if candidate.group.name == group.name
        ]
        if indices:
            model.Add(
                sum(variables[index] for index in indices) == group.lessons_per_week
            )
        else:
            model.Add(0 == group.lessons_per_week)


def _add_resource_conflicts(model, variables, candidates):
    for first_index, first in enumerate(candidates):
        for second_index in range(first_index + 1, len(candidates)):
            second = candidates[second_index]
            if _conflicts(first, second):
                model.Add(variables[first_index] + variables[second_index] <= 1)


def _instructor_load_preference_terms(model, variables, candidates, instructors):
    terms = []
    for instructor_index, instructor in enumerate(instructors):
        instructor_variables = [
            variables[index]
            for index, candidate in enumerate(candidates)
            if instructor.name in _candidate_instructor_names(candidate)
        ]
        if not instructor_variables:
            continue

        lesson_count = sum(instructor_variables)
        upper_bound = max(
            len(instructor_variables),
            instructor.preferred_min_classes_per_week,
        )
        shortage = model.NewIntVar(
            0,
            upper_bound,
            f"instructor_{instructor_index}_load_shortage",
        )
        excess = model.NewIntVar(
            0,
            upper_bound,
            f"instructor_{instructor_index}_load_excess",
        )
        model.Add(
            shortage >= instructor.preferred_min_classes_per_week - lesson_count
        )
        model.Add(
            excess >= lesson_count - instructor.preferred_max_classes_per_week
        )
        terms.extend([-10 * shortage, -10 * excess])
    return terms


def _candidate_instructor_names(candidate):
    return {instructor.name for instructor in candidate.instructors}


def _conflicts(first, second):
    if not _overlaps(first, second):
        return _has_travel_conflict(first, second)

    return (
        _same_room_slot(first, second)
        or first.group.name == second.group.name
        or _has_instructor_overlap(first, second)
    )


def _same_room_slot(first, second):
    return (
        first.location.name == second.location.name
        and first.room_index == second.room_index
    )


def _overlaps(first, second):
    first_time = first.lesson_block.time
    second_time = second.lesson_block.time

    return (
        first_time.day == second_time.day
        and to_slot(first_time.start) < to_slot(second_time.end)
        and to_slot(second_time.start) < to_slot(first_time.end)
    )


def _has_instructor_overlap(first, second):
    first_names = {instructor.name for instructor in first.instructors}
    second_names = {instructor.name for instructor in second.instructors}
    return bool(first_names & second_names)


def _has_travel_conflict(first, second):
    if first.location.name == second.location.name:
        return False
    if not _has_instructor_overlap(first, second):
        return False

    first_time = first.lesson_block.time
    second_time = second.lesson_block.time
    if first_time.day != second_time.day:
        return False

    travel_slots = MIN_TRAVEL_MINUTES_BETWEEN_LOCATIONS // 5
    return (
        abs(to_slot(second_time.start) - to_slot(first_time.end)) < travel_slots
        or abs(to_slot(first_time.start) - to_slot(second_time.end)) < travel_slots
    )


def _preference_score(instructors):
    if len(instructors) != 2:
        return 0

    first, second = instructors
    score = 0
    if second.name in first.prefers_with:
        score += 1
    if first.name in second.prefers_with:
        score += 1
    if second.name in first.avoids_with:
        score -= 1
    if first.name in second.avoids_with:
        score -= 1
    return score


def _candidate_to_lesson(candidate):
    time = candidate.lesson_block.time
    return ScheduledLesson(
        group_name=candidate.group.name,
        day=time.day,
        start=time.start,
        end=time.end,
        location_name=candidate.location.name,
        room_index=candidate.room_index,
        instructor_names=tuple(instructor.name for instructor in candidate.instructors),
    )
