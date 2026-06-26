from dataclasses import dataclass
from itertools import combinations

from ortools.sat.python import cp_model

from scheduler.spec_models import to_slot


UNSOLVED_MESSAGE = "No complete schedule found. The combined constraints are too tight."


@dataclass(frozen=True)
class ScheduledLesson:
    group_name: str
    day: str
    start: str
    end: str
    room_name: str
    instructor_names: tuple[str, ...]


@dataclass(frozen=True)
class SolveResult:
    solved: bool
    lessons: tuple[ScheduledLesson, ...] = ()
    message: str = ""


@dataclass(frozen=True)
class _Candidate:
    group: object
    room: object
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
    if preference_terms:
        model.Maximize(sum(preference_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5
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
        for room in spec.rooms:
            if room.capacity < group.students:
                continue
            for lesson_block in spec.lesson_blocks:
                if lesson_block.duration_minutes != group.duration_minutes:
                    continue
                for instructors in _instructor_choices(
                    spec.instructors, group, lesson_block
                ):
                    candidates.append(
                        _Candidate(
                            group=group,
                            room=room,
                            lesson_block=lesson_block,
                            instructors=instructors,
                            preference_score=_preference_score(instructors),
                        )
                    )
    return tuple(candidates)


def _instructor_choices(instructors, group, lesson_block):
    eligible = [
        instructor
        for instructor in instructors
        if group.teaching_key in instructor.can_teach
        and _covers_block(instructor, lesson_block)
    ]

    if group.teachers_required == 1:
        return tuple((instructor,) for instructor in eligible)

    if group.teachers_required == 2:
        return tuple(
            pair
            for pair in combinations(eligible, 2)
            if not _pair_is_banned(pair[0], pair[1])
        )

    return ()


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


def _same_block(first, second):
    return (
        first.lesson_block.time.day == second.lesson_block.time.day
        and first.lesson_block.time.start == second.lesson_block.time.start
        and first.lesson_block.time.end == second.lesson_block.time.end
    )


def _conflicts(first, second):
    # The first solver treats same-day blocks for one room as alternatives.
    if first.room.name == second.room.name and _same_day(first, second):
        return True

    return _same_block(first, second) and (
        first.group.name == second.group.name
        or _has_instructor_overlap(first, second)
    )


def _same_day(first, second):
    return first.lesson_block.time.day == second.lesson_block.time.day


def _has_instructor_overlap(first, second):
    first_names = {instructor.name for instructor in first.instructors}
    second_names = {instructor.name for instructor in second.instructors}
    return bool(first_names & second_names)


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
        room_name=candidate.room.name,
        instructor_names=tuple(instructor.name for instructor in candidate.instructors),
    )
