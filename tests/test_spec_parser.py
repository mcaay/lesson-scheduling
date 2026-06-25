from scheduler.examples import EXAMPLE_SPEC
from scheduler.spec_parser import parse_spec


def test_parse_example_spec():
    result = parse_spec(EXAMPLE_SPEC)

    assert result.is_valid
    assert len(result.spec.lesson_blocks) == 12
    assert [room.name for room in result.spec.rooms] == ["Main Hall", "Small Studio"]
    assert [instructor.name for instructor in result.spec.instructors] == ["Anna", "Ivona"]
    assert result.spec.groups[0].name == "Lindy Hop 1"
    assert result.spec.groups[0].duration_minutes == 85


def test_parse_reports_unknown_line_with_number():
    result = parse_spec("lesson blocks\nMonday 18:00-19:25\nnonsense")

    assert not result.is_valid
    assert result.errors[0].line == 3
    assert result.errors[0].message == "Unknown line: nonsense"


def test_parse_reports_missing_capacity():
    result = parse_spec("room Main Hall")

    assert not result.is_valid
    assert result.errors[0].line == 1
    assert result.errors[0].message == "Room Main Hall is missing capacity"


def test_parse_reports_missing_group_field():
    result = parse_spec("group Lindy Hop 1\nstudents 24")

    assert not result.is_valid
    assert result.spec is None
    assert result.errors[0].line == 1
    assert result.errors[0].message == "Group Lindy Hop 1 is missing style"


def test_parse_reports_invalid_day_without_crashing():
    result = parse_spec("lesson blocks\nFunday 18:00-19:25")

    assert not result.is_valid
    assert result.errors[0].line == 2
    assert result.errors[0].message == "Unknown day: Funday"


def test_parse_error_does_not_return_partial_spec():
    result = parse_spec("lesson blocks\nFunday 18:00-19:25")

    assert not result.is_valid
    assert result.spec is None


def test_parse_reports_off_grid_time_without_crashing():
    result = parse_spec("lesson blocks\nMonday 18:04-19:25")

    assert not result.is_valid
    assert result.errors[0].line == 2
    assert result.errors[0].message == "Time must use a 5-minute grid: 18:04"


def test_parse_reports_end_before_start():
    result = parse_spec("lesson blocks\nMonday 20:00-19:00")

    assert not result.is_valid
    assert result.errors[0].line == 2
    assert result.errors[0].message == "Time range end must be after start: 20:00-19:00"


def test_parse_reports_hour_out_of_range():
    result = parse_spec("lesson blocks\nMonday 25:00-26:00")

    assert not result.is_valid
    assert result.errors[0].line == 2
    assert result.errors[0].message == "Time must use HH:MM with hours from 00 to 23: 25:00"


def test_parse_reports_malformed_time_cleanly():
    result = parse_spec("lesson blocks\nMonday 18-19:25")

    assert not result.is_valid
    assert result.errors[0].line == 2
    assert result.errors[0].message == "Invalid lesson block: Monday 18-19:25"


def test_parse_invalid_capacity_has_single_clear_error():
    result = parse_spec("room Main Hall\ncapacity nope")

    assert not result.is_valid
    assert len(result.errors) == 1
    assert result.errors[0].line == 2
    assert result.errors[0].message == "Capacity must be a whole number: nope"
