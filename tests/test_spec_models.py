from scheduler.examples import EXAMPLE_SPEC
from scheduler.spec_models import TimeRange, to_slot


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


def test_example_spec_contains_required_sections():
    assert "lesson blocks" in EXAMPLE_SPEC
    assert "room Main Hall" in EXAMPLE_SPEC
    assert "instructor Anna" in EXAMPLE_SPEC
    assert "group Lindy Hop 1" in EXAMPLE_SPEC
    assert "cannot teach with Ana" not in EXAMPLE_SPEC
