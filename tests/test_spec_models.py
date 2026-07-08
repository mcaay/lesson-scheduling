from scheduler.examples import EXAMPLE_SPEC
from scheduler.spec_models import (
    Group,
    Instructor,
    TimeRange,
    instructor_can_teach_group,
    to_slot,
)


def test_to_slot_uses_five_minute_grid():
    assert to_slot("18:00") == 216
    assert to_slot("18:05") == 217


def test_to_slot_rejects_off_grid_minutes():
    try:
        to_slot("18:04")
    except ValueError as error:
        assert str(error) == "Time must use a 5-minute grid: 18:04"
    else:
        raise AssertionError("Expected ValueError")


def test_to_slot_rejects_invalid_minutes():
    try:
        to_slot("18:60")
    except ValueError as error:
        assert str(error) == "Time must use HH:MM with minutes from 00 to 59: 18:60"
    else:
        raise AssertionError("Expected ValueError")


def test_to_slot_rejects_invalid_hours():
    try:
        to_slot("25:00")
    except ValueError as error:
        assert str(error) == "Time must use HH:MM with hours from 00 to 23: 25:00"
    else:
        raise AssertionError("Expected ValueError")


def test_to_slot_rejects_overlong_time_before_integer_conversion():
    value = f"{'1' * 5000}:00"

    try:
        to_slot(value)
    except ValueError as error:
        assert str(error) == f"Time must use HH:MM: {value}"
    else:
        raise AssertionError("Expected ValueError")


def test_time_range_duration_minutes():
    time_range = TimeRange(day="Monday", start="18:00", end="19:25")

    assert time_range.duration_minutes == 85


def test_time_range_rejects_end_before_start():
    time_range = TimeRange(day="Monday", start="20:00", end="19:00")

    try:
        time_range.duration_minutes
    except ValueError as error:
        assert str(error) == "Time range end must be after start: 20:00-19:00"
    else:
        raise AssertionError("Expected ValueError")


def test_group_level_name_strips_trailing_instance_number():
    group = Group(
        name="Let's Start 1 #3",
        lessons_per_week=1,
        duration_minutes=85,
    )

    assert group.level_name == "Let's Start 1"
    assert group.instance_number == 3


def test_group_level_name_without_instance_is_group_name():
    group = Group(
        name="Solo Jazz",
        lessons_per_week=1,
        duration_minutes=85,
    )

    assert group.level_name == "Solo Jazz"
    assert group.instance_number is None


def test_instructor_can_teach_group_uses_exact_level_name():
    instructor = Instructor(name="Anna", can_teach=("Let's Start 1",))

    assert instructor_can_teach_group(
        instructor,
        Group(name="Let's Start 1 #1", lessons_per_week=1, duration_minutes=85),
    )
    assert not instructor_can_teach_group(
        instructor,
        Group(name="Let's Start 10 #1", lessons_per_week=1, duration_minutes=85),
    )


def test_example_spec_contains_required_sections():
    assert "lesson blocks" in EXAMPLE_SPEC
    assert "location Swing Studio" in EXAMPLE_SPEC
    assert "rooms 2" in EXAMPLE_SPEC
    assert "location Jazz Loft" in EXAMPLE_SPEC
    assert "rooms 1" in EXAMPLE_SPEC
    assert "instructor Ania" in EXAMPLE_SPEC
    assert "instructor Mateusz" in EXAMPLE_SPEC
    assert "instructor Marysia" in EXAMPLE_SPEC
    assert "instructor Rafał" in EXAMPLE_SPEC
    assert "group LH1" in EXAMPLE_SPEC
    assert "group LH2" in EXAMPLE_SPEC
    assert "group LH3" in EXAMPLE_SPEC
    assert "group Charleston 1" in EXAMPLE_SPEC
    assert "group Balboa 1" in EXAMPLE_SPEC
    assert "group Solo Jazz" in EXAMPLE_SPEC
    assert "teacher roles solo" in EXAMPLE_SPEC
    assert "cannot teach with Ana" not in EXAMPLE_SPEC
