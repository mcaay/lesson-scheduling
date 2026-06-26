from scheduler.examples import EXAMPLE_SPEC
from scheduler.solver import solve_schedule
from scheduler.spec_parser import parse_spec


def test_solver_finds_schedule_for_example_spec():
    spec = parse_spec(EXAMPLE_SPEC).spec

    result = solve_schedule(spec)

    assert result.solved
    assert len(result.lessons) == 1
    lesson = result.lessons[0]
    assert lesson.group_name == "Lindy Hop 1"
    assert lesson.room_name == "Main Hall"
    assert set(lesson.instructor_names) == {"Anna", "Ivona"}


def test_solver_allows_same_room_on_different_blocks():
    text = """lesson blocks
Monday 18:00-19:25
Monday 19:30-20:55

room Main Hall
capacity 30

instructor Anna
can teach Lindy Hop beginner
available Monday 17:00-22:00

instructor Ivona
can teach Lindy Hop beginner
available Monday 17:00-22:00

group Lindy Hop 1
students 20
style Lindy Hop
level beginner
needs 1 lesson per week
duration 85 minutes
teachers 1

group Lindy Hop 2
students 20
style Lindy Hop
level beginner
needs 1 lesson per week
duration 85 minutes
teachers 1
"""
    spec = parse_spec(text).spec

    result = solve_schedule(spec)

    assert result.solved
    assert len(result.lessons) == 2
    assert {lesson.start for lesson in result.lessons} == {"18:00", "19:30"}


def test_solver_reports_unsolved_when_room_conflict_is_forced():
    text = """lesson blocks
Monday 18:00-19:25

room Main Hall
capacity 30

instructor Anna
can teach Lindy Hop beginner
available Monday 17:00-22:00

instructor Ivona
can teach Lindy Hop beginner
available Monday 17:00-22:00

group Lindy Hop 1
students 20
style Lindy Hop
level beginner
needs 1 lesson per week
duration 85 minutes
teachers 1

group Lindy Hop 2
students 20
style Lindy Hop
level beginner
needs 1 lesson per week
duration 85 minutes
teachers 1
"""
    spec = parse_spec(text).spec

    result = solve_schedule(spec)

    assert not result.solved
    assert result.message == "No complete schedule found. The combined constraints are too tight."
