from scheduler.examples import EXAMPLE_SPEC
from scheduler.spec_parser import parse_spec
from scheduler.spec_serializer import serialize_spec


def test_serialize_round_trips_example_spec():
    parsed = parse_spec(EXAMPLE_SPEC)

    serialized = serialize_spec(parsed.spec)
    reparsed = parse_spec(serialized)

    assert reparsed.is_valid
    assert reparsed.spec == parsed.spec


def test_serializer_writes_human_readable_sections():
    parsed = parse_spec(EXAMPLE_SPEC)

    serialized = serialize_spec(parsed.spec)

    assert "lesson blocks" in serialized
    assert "location Swing Studio" in serialized
    assert "rooms 2" in serialized
    assert "location Jazz Loft" in serialized
    assert "rooms 1" in serialized
    assert "\ncapacity " not in serialized
    assert "instructor Ania" in serialized
    assert "instructor Mateusz" in serialized
    assert "instructor Marysia" in serialized
    assert "instructor Rafał" in serialized
    assert "roles leader" in serialized
    assert "prefers minimum 1 class per week" in serialized
    assert "prefers maximum 3 classes per week" in serialized
    assert "group LH1" in serialized
    assert "group LH2" in serialized
    assert "group LH3" in serialized
    assert "group Charleston 1" in serialized
    assert "group Balboa 1" in serialized
    assert "group Solo Jazz" in serialized
    assert "\nstudents " not in serialized
    assert "teacher roles leader, follower" in serialized
    assert "teacher roles solo" in serialized
    assert "style " not in serialized
    assert "level " not in serialized


def test_serializer_writes_group_time_windows():
    parsed = parse_spec(
        """group LH1
needs 1 lesson per week
duration 85 minutes
teacher roles leader, follower
time window Monday 18:00-19:25
"""
    )

    serialized = serialize_spec(parsed.spec)

    assert "time window Monday 18:00-19:25" in serialized
