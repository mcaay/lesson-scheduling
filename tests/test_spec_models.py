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


def test_time_range_duration_minutes():
    time_range = TimeRange(day="Monday", start="18:00", end="19:25")

    assert time_range.duration_minutes == 85


def test_example_spec_contains_required_sections():
    assert "lesson blocks" in EXAMPLE_SPEC
    assert "room Main Hall" in EXAMPLE_SPEC
    assert "instructor Anna" in EXAMPLE_SPEC
    assert "group Lindy Hop 1" in EXAMPLE_SPEC
    assert "cannot teach with Ana" not in EXAMPLE_SPEC
