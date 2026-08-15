from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations

from ortools.sat.python import cp_model

from scheduler.spec_models import instructor_can_teach_group, to_slot


INFEASIBLE_MESSAGE = "No complete schedule found. The combined constraints are too tight."
UNSOLVED_MESSAGE = INFEASIBLE_MESSAGE
TIME_LIMIT_MESSAGE = (
    "The solver reached its time limit before finding a complete schedule. "
    "Try reducing the number of rooms, lesson blocks, instructors, or groups."
)
MODEL_INVALID_MESSAGE = "The scheduling model is invalid. Please report this error."
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
    status: str = ""


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

    pair_preference_terms = [
        candidate.preference_score * variables[index]
        for index, candidate in enumerate(candidates)
        if candidate.preference_score
    ]
    gap_terms, maximum_gap_penalty = _instructor_gap_preference_terms(
        model,
        variables,
        candidates,
        spec.instructors,
    )
    load_terms, maximum_load_penalty = _instructor_load_preference_terms(
        model,
        variables,
        candidates,
        spec.instructors,
    )
    if pair_preference_terms or gap_terms or load_terms:
        # Each tier outweighs every possible change in the tiers below it.
        gap_weight = maximum_load_penalty + 1
        pair_weight = maximum_gap_penalty * gap_weight + maximum_load_penalty + 1
        model.Maximize(
            pair_weight * sum(pair_preference_terms)
            - gap_weight * sum(gap_terms)
            - sum(load_terms)
        )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return SolveResult(
            False,
            message=_message_for_status(status),
            status=solver.StatusName(status),
        )

    selected_candidates = tuple(
        candidate
        for index, candidate in enumerate(candidates)
        if solver.BooleanValue(variables[index])
    )
    _assert_valid_solution(selected_candidates, spec)
    lessons = tuple(_candidate_to_lesson(candidate) for candidate in selected_candidates)
    return SolveResult(True, lessons=lessons, status=solver.StatusName(status))


def _message_for_status(status):
    if status == cp_model.INFEASIBLE:
        return INFEASIBLE_MESSAGE
    if status == cp_model.MODEL_INVALID:
        return MODEL_INVALID_MESSAGE
    return TIME_LIMIT_MESSAGE


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
            key = frozenset((id(first), id(second)))
            if key not in seen:
                pairs.append((first, second))
                seen.add(key)
            continue
        if first_role in second.roles and second_role in first.roles:
            key = frozenset((id(first), id(second)))
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
            if candidate.group is group
        ]
        if indices:
            model.Add(
                sum(variables[index] for index in indices) == group.lessons_per_week
            )
        else:
            model.Add(0 == group.lessons_per_week)


def _add_resource_conflicts(model, variables, candidates):
    # Slot buckets express the same exclusions without comparing every pair.
    room_slots = defaultdict(list)
    group_slots = defaultdict(list)
    instructor_slots = defaultdict(list)
    travel_slots = defaultdict(lambda: defaultdict(list))
    travel_slot_count = MIN_TRAVEL_MINUTES_BETWEEN_LOCATIONS // 5

    for index, candidate in enumerate(candidates):
        time = candidate.lesson_block.time
        start = to_slot(time.start)
        end = to_slot(time.end)
        location_id = id(candidate.location)
        for slot in range(start, end):
            room_slots[(location_id, candidate.room_index, time.day, slot)].append(index)
            group_slots[(id(candidate.group), time.day, slot)].append(index)
            for instructor in candidate.instructors:
                instructor_slots[(id(instructor), time.day, slot)].append(index)
        for slot in range(start, end + travel_slot_count):
            # Extending occupancy after a lesson creates the travel interval.
            for instructor in candidate.instructors:
                key = (id(instructor), time.day, slot)
                travel_slots[key][location_id].append(index)

    seen_variable_sets = set()
    for buckets in (room_slots, group_slots, instructor_slots):
        for indices in buckets.values():
            variable_set = tuple(sorted(set(indices)))
            if len(variable_set) < 2 or variable_set in seen_variable_sets:
                continue
            model.AddAtMostOne(variables[index] for index in variable_set)
            seen_variable_sets.add(variable_set)

    for slot_index, locations in enumerate(travel_slots.values()):
        if len(locations) < 2:
            continue
        location_active_variables = []
        for location_index, indices in enumerate(locations.values()):
            location_active = model.NewBoolVar(
                f"travel_{slot_index}_location_{location_index}"
            )
            model.AddMaxEquality(
                location_active,
                [variables[index] for index in set(indices)],
            )
            location_active_variables.append(location_active)
        model.AddAtMostOne(location_active_variables)


def _instructor_load_preference_terms(model, variables, candidates, instructors):
    terms = []
    maximum_penalty = 0
    for instructor_index, instructor in enumerate(instructors):
        instructor_variables = [
            variables[index]
            for index, candidate in enumerate(candidates)
            if _candidate_has_instructor(candidate, instructor)
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
        terms.extend([shortage, excess])
        maximum_penalty += 2 * upper_bound
    return terms, maximum_penalty


def _instructor_gap_preference_terms(model, variables, candidates, instructors):
    terms = []
    maximum_penalty = 0
    for instructor_index, instructor in enumerate(instructors):
        days = sorted(
            {
                candidate.lesson_block.time.day
                for candidate in candidates
                if _candidate_has_instructor(candidate, instructor)
            }
        )
        for day_index, day in enumerate(days):
            day_candidates = [
                (index, candidate)
                for index, candidate in enumerate(candidates)
                if candidate.lesson_block.time.day == day
                and _candidate_has_instructor(candidate, instructor)
            ]
            starts = [
                to_slot(candidate.lesson_block.time.start)
                for _index, candidate in day_candidates
            ]
            ends = [
                to_slot(candidate.lesson_block.time.end)
                for _index, candidate in day_candidates
            ]
            day_start = min(starts)
            day_end = max(ends)
            first_start = model.NewIntVar(
                day_start,
                day_end,
                f"instructor_{instructor_index}_day_{day_index}_first_start",
            )
            last_end = model.NewIntVar(
                day_start,
                day_end,
                f"instructor_{instructor_index}_day_{day_index}_last_end",
            )
            idle_slots = model.NewIntVar(
                0,
                day_end - day_start,
                f"instructor_{instructor_index}_day_{day_index}_idle_slots",
            )

            duration_terms = []
            for candidate_index, candidate in day_candidates:
                variable = variables[candidate_index]
                start = to_slot(candidate.lesson_block.time.start)
                end = to_slot(candidate.lesson_block.time.end)
                model.Add(first_start <= start).OnlyEnforceIf(variable)
                model.Add(last_end >= end).OnlyEnforceIf(variable)
                duration_terms.append((end - start) * variable)

            model.Add(
                idle_slots >= last_end - first_start - sum(duration_terms)
            )
            terms.append(idle_slots)
            maximum_penalty += day_end - day_start
    return terms, maximum_penalty


def _candidate_has_instructor(candidate, instructor):
    return any(
        candidate_instructor is instructor
        for candidate_instructor in candidate.instructors
    )


def _conflicts(first, second):
    if not _overlaps(first, second):
        return _has_travel_conflict(first, second)

    return (
        _same_room_slot(first, second)
        or first.group is second.group
        or _has_instructor_overlap(first, second)
    )


def _same_room_slot(first, second):
    return (
        first.location is second.location
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
    return any(
        first_instructor is second_instructor
        for first_instructor in first.instructors
        for second_instructor in second.instructors
    )


def _has_travel_conflict(first, second):
    if first.location is second.location:
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


def _assert_valid_solution(selected_candidates, spec):
    for group in spec.groups:
        lesson_count = sum(
            candidate.group is group for candidate in selected_candidates
        )
        if lesson_count != group.lessons_per_week:
            raise RuntimeError(
                f"Solver returned {lesson_count} lessons for {group.name}; "
                f"expected {group.lessons_per_week}"
            )

    for candidate in selected_candidates:
        if not any(candidate.group is group for group in spec.groups):
            raise RuntimeError("Solver returned a lesson for an unknown group")
        if not any(candidate.location is location for location in spec.locations):
            raise RuntimeError("Solver returned a lesson at an unknown location")
        if candidate.room_index not in range(1, candidate.location.rooms_count + 1):
            raise RuntimeError("Solver returned a lesson in an unknown room")
        if not any(
            candidate.lesson_block is lesson_block
            for lesson_block in spec.lesson_blocks
        ):
            raise RuntimeError("Solver returned an unknown lesson block")
        if len({id(instructor) for instructor in candidate.instructors}) != len(
            candidate.instructors
        ):
            raise RuntimeError("Solver assigned the same instructor twice")
        if len(candidate.instructors) != candidate.group.teachers_required:
            raise RuntimeError("Solver returned the wrong number of instructors")
        for instructor, role in zip(
            candidate.instructors,
            candidate.group.teacher_roles,
        ):
            if not any(instructor is item for item in spec.instructors):
                raise RuntimeError("Solver returned an unknown instructor")
            if role not in instructor.roles:
                raise RuntimeError("Solver assigned an instructor to the wrong role")
            if not instructor_can_teach_group(instructor, candidate.group):
                raise RuntimeError("Solver assigned an ineligible instructor")
            if not _covers_block(instructor, candidate.lesson_block):
                raise RuntimeError("Solver assigned an unavailable instructor")
        if len(candidate.instructors) == 2 and _pair_is_banned(
            *candidate.instructors
        ):
            raise RuntimeError("Solver assigned a banned instructor pair")

    for first, second in combinations(selected_candidates, 2):
        if _conflicts(first, second):
            raise RuntimeError("Solver returned conflicting lessons")
