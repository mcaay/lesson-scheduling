from scheduler.examples import EXAMPLE_SPEC
from scheduler.spec_models import TimeRange, to_slot


def test_to_slot_uses_five_minute_grid():
    assert to_slot("18:00") == 216
    assert to_slot("18:05") == 217


def test_time_range_duration_minutes():
    time_range = TimeRange(day="Monday", start="18:00", end="19:25")

    assert time_range.duration_minutes == 85


def test_example_spec_contains_required_sections():
    assert "lesson blocks" in EXAMPLE_SPEC
    assert "room Main Hall" in EXAMPLE_SPEC
    assert "instructor Anna" in EXAMPLE_SPEC
    assert "group Lindy Hop 1" in EXAMPLE_SPEC
