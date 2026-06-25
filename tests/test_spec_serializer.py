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
    assert "room Main Hall" in serialized
    assert "instructor Anna" in serialized
    assert "group Lindy Hop 1" in serialized
