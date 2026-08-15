from scheduler.examples import EXAMPLE_SPEC
from scheduler.solver import (
    SOLVER_TIME_LIMIT_SECONDS,
    _Candidate,
    _conflicts,
    solve_schedule,
)
from scheduler.spec_models import Group, Instructor, LessonBlock, Location, TimeRange
from scheduler.spec_parser import parse_spec


def test_solver_has_two_minute_time_limit():
    assert SOLVER_TIME_LIMIT_SECONDS == 120


def test_solver_finds_schedule_for_example_spec():
    spec = parse_spec(EXAMPLE_SPEC).spec

    result = solve_schedule(spec)

    assert result.solved
    assert len(result.lessons) == 6
    assert {lesson.group_name for lesson in result.lessons} == {
        "LH1",
        "LH2",
        "LH3",
        "Charleston 1",
        "Balboa 1",
        "Solo Jazz",
    }
    for lesson in result.lessons:
        assert lesson.location_name in {"Swing Studio", "Jazz Loft"}
        assert lesson.room_index in {1, 2}
        if lesson.group_name == "Solo Jazz":
            assert lesson.instructor_names == ("Marysia",)
        else:
            assert len(lesson.instructor_names) == 2


def test_solver_requires_leader_and_follower_for_pair_dance_group():
    text = """lesson blocks
Monday 18:00-19:25

location Main Hall
rooms 1
instructor Anna
roles leader
can teach Lindy Hop beginner
available Monday 17:00-22:00

instructor Barbara
roles leader
can teach Lindy Hop beginner
available Monday 17:00-22:00

instructor Ivona
roles follower
can teach Lindy Hop beginner
available Monday 17:00-22:00

group Lindy Hop beginner #1
needs 1 lesson per week
duration 85 minutes
teacher roles leader, follower
"""
    spec = parse_spec(text).spec

    result = solve_schedule(spec)

    assert result.solved
    assert len(result.lessons) == 1
    assert "Ivona" in result.lessons[0].instructor_names


def test_solver_does_not_assign_instructor_with_zero_preferred_maximum():
    text = """lesson blocks
Monday 18:00-19:25

location Main Hall
rooms 1
instructor Anna
roles leader
prefers minimum 0 classes per week
prefers maximum 0 classes per week
can teach Lindy Hop beginner
available Monday 17:00-22:00

instructor Barbara
roles leader
can teach Lindy Hop beginner
available Monday 17:00-22:00

instructor Ivona
roles follower
can teach Lindy Hop beginner
available Monday 17:00-22:00

group Lindy Hop beginner #1
needs 1 lesson per week
duration 85 minutes
teacher roles leader, follower
"""
    spec = parse_spec(text).spec

    result = solve_schedule(spec)

    assert result.solved
    assert set(result.lessons[0].instructor_names) == {"Barbara", "Ivona"}


def test_solver_prefers_staying_under_instructor_maximum_when_possible():
    text = """lesson blocks
Monday 18:00-19:00
Monday 19:30-20:30

location Main Hall
rooms 1
instructor Anna
roles leader
prefers minimum 1 class per week
prefers maximum 1 class per week
can teach Lindy Hop beginner
available Monday 17:00-22:00

instructor Barbara
roles leader
prefers minimum 1 class per week
prefers maximum 3 classes per week
can teach Lindy Hop beginner
available Monday 17:00-22:00

instructor Ivona
roles follower
prefers minimum 1 class per week
prefers maximum 3 classes per week
can teach Lindy Hop beginner
available Monday 17:00-22:00

group Lindy Hop beginner #1
needs 1 lesson per week
duration 60 minutes
teacher roles leader, follower

group Lindy Hop beginner #2
needs 1 lesson per week
duration 60 minutes
teacher roles leader, follower
"""
    spec = parse_spec(text).spec

    result = solve_schedule(spec)

    assert result.solved
    assigned_leaders = {
        instructor_name
        for lesson in result.lessons
        for instructor_name in lesson.instructor_names
        if instructor_name in {"Anna", "Barbara"}
    }
    assert assigned_leaders == {"Anna", "Barbara"}


def test_solver_allows_same_location_room_on_different_blocks():
    text = """lesson blocks
Monday 18:00-19:25
Monday 19:30-20:55

location Main Hall
rooms 1
instructor Anna
can teach Lindy Hop beginner
available Monday 17:00-22:00

instructor Ivona
can teach Lindy Hop beginner
available Monday 17:00-22:00

group Lindy Hop beginner #1
needs 1 lesson per week
duration 85 minutes
teacher roles leader

group Lindy Hop beginner #2
needs 1 lesson per week
duration 85 minutes
teacher roles leader
"""
    spec = parse_spec(text).spec

    result = solve_schedule(spec)

    assert result.solved
    assert len(result.lessons) == 2
    assert {lesson.start for lesson in result.lessons} == {"18:00", "19:30"}


def test_solver_restricts_group_to_time_window():
    text = """lesson blocks
Monday 18:00-19:00
Monday 19:00-20:00

location Main Hall
rooms 1
instructor Anna
roles leader
can teach Lindy Hop beginner
available Monday 17:00-22:00

group Lindy Hop beginner #1
needs 1 lesson per week
duration 60 minutes
teacher roles leader
time window Monday 19:00-20:00
"""
    spec = parse_spec(text).spec

    result = solve_schedule(spec)

    assert result.solved
    assert result.lessons[0].start == "19:00"


def test_solver_allows_three_consecutive_classes_in_same_location():
    text = """lesson blocks
Monday 18:00-19:00
Monday 19:00-20:00
Monday 20:00-21:00

location Main Hall
rooms 1
instructor Anna
roles leader
prefers maximum 3 classes per week
can teach Lindy Hop beginner
available Monday 17:00-22:00

group Lindy Hop beginner #1
needs 1 lesson per week
duration 60 minutes
teacher roles leader

group Lindy Hop beginner #2
needs 1 lesson per week
duration 60 minutes
teacher roles leader

group Lindy Hop beginner #3
needs 1 lesson per week
duration 60 minutes
teacher roles leader
"""
    spec = parse_spec(text).spec

    result = solve_schedule(spec)

    assert result.solved
    assert len(result.lessons) == 3
    assert {lesson.location_name for lesson in result.lessons} == {"Main Hall"}


def test_solver_requires_travel_gap_between_different_locations():
    instructor = Instructor(name="Anna")
    group = Group(
        name="Lindy Hop beginner",
        lessons_per_week=1,
        duration_minutes=60,
        teacher_roles=("leader",),
    )
    first = _Candidate(
        group=group,
        location=Location(name="Main Hall", rooms_count=1),
        room_index=1,
        lesson_block=LessonBlock(TimeRange(day="Monday", start="18:00", end="19:00")),
        instructors=(instructor,),
        preference_score=0,
    )
    second = _Candidate(
        group=group,
        location=Location(name="Small Studio", rooms_count=1),
        room_index=1,
        lesson_block=LessonBlock(TimeRange(day="Monday", start="19:30", end="20:30")),
        instructors=(instructor,),
        preference_score=0,
    )
    third = _Candidate(
        group=group,
        location=Location(name="Small Studio", rooms_count=1),
        room_index=1,
        lesson_block=LessonBlock(TimeRange(day="Monday", start="20:00", end="21:00")),
        instructors=(instructor,),
        preference_score=0,
    )

    assert _conflicts(first, second)
    assert not _conflicts(first, third)


def test_solver_blocks_overlapping_room_assignments():
    text = """lesson blocks
Monday 18:00-19:00
Monday 18:30-19:30

location Main Hall
rooms 1
instructor Anna
can teach Lindy Hop beginner
available Monday 17:00-22:00

instructor Ivona
can teach Lindy Hop beginner
available Monday 17:00-22:00

group Lindy Hop beginner #1
needs 1 lesson per week
duration 60 minutes
teacher roles leader

group Lindy Hop beginner #2
needs 1 lesson per week
duration 60 minutes
teacher roles leader
"""
    spec = parse_spec(text).spec

    result = solve_schedule(spec)

    assert not result.solved
    assert result.message == "No complete schedule found. The combined constraints are too tight."


def test_solver_blocks_overlapping_group_assignments():
    text = """lesson blocks
Monday 18:00-19:00
Monday 18:30-19:30

location Main Hall
rooms 1

location Small Studio
rooms 1
instructor Anna
can teach Lindy Hop beginner
available Monday 17:00-22:00

instructor Ivona
can teach Lindy Hop beginner
available Monday 17:00-22:00

group Lindy Hop beginner #1
needs 2 lesson per week
duration 60 minutes
teacher roles leader
"""
    spec = parse_spec(text).spec

    result = solve_schedule(spec)

    assert not result.solved
    assert result.message == "No complete schedule found. The combined constraints are too tight."


def test_solver_reports_unsolved_when_room_conflict_is_forced():
    text = """lesson blocks
Monday 18:00-19:25

location Main Hall
rooms 1
instructor Anna
can teach Lindy Hop beginner
available Monday 17:00-22:00

instructor Ivona
can teach Lindy Hop beginner
available Monday 17:00-22:00

group Lindy Hop beginner #1
needs 1 lesson per week
duration 85 minutes
teacher roles leader

group Lindy Hop beginner #2
needs 1 lesson per week
duration 85 minutes
teacher roles leader
"""
    spec = parse_spec(text).spec

    result = solve_schedule(spec)

    assert not result.solved
    assert result.message == "No complete schedule found. The combined constraints are too tight."
