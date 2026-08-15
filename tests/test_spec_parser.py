from scheduler.examples import EXAMPLE_SPEC
from scheduler.spec_parser import parse_spec


def test_parse_example_spec():
    result = parse_spec(EXAMPLE_SPEC)

    assert result.is_valid
    assert len(result.spec.lesson_blocks) == 12
    assert [
        (location.name, location.rooms_count)
        for location in result.spec.locations
    ] == [
        ("Swing Studio", 2),
        ("Jazz Loft", 1),
    ]
    assert [instructor.name for instructor in result.spec.instructors] == [
        "Ania",
        "Mateusz",
        "Marysia",
        "Rafał",
    ]
    assert [instructor.roles for instructor in result.spec.instructors] == [
        ("follower",),
        ("leader",),
        ("follower", "solo"),
        ("leader",),
    ]
    assert result.spec.instructors[0].preferred_min_classes_per_week == 1
    assert result.spec.instructors[0].preferred_max_classes_per_week == 3
    assert [instructor.prefers_with for instructor in result.spec.instructors] == [
        ("Mateusz",),
        ("Ania",),
        ("Rafał",),
        ("Marysia",),
    ]
    assert [group.name for group in result.spec.groups] == [
        "LH1",
        "LH2",
        "LH3",
        "Charleston 1",
        "Balboa 1",
        "Solo Jazz",
    ]
    assert {group.duration_minutes for group in result.spec.groups} == {85}
    assert {group.lessons_per_week for group in result.spec.groups} == {1}
    assert [group.teacher_roles for group in result.spec.groups] == [
        ("leader", "follower"),
        ("leader", "follower"),
        ("leader", "follower"),
        ("leader", "follower"),
        ("leader", "follower"),
        ("solo",),
    ]


def test_parse_instructor_class_preferences():
    result = parse_spec(
        """instructor Anna
prefers minimum 0 classes per week
prefers maximum 2 classes per week
"""
    )

    assert result.is_valid
    assert result.spec.instructors[0].preferred_min_classes_per_week == 0
    assert result.spec.instructors[0].preferred_max_classes_per_week == 2


def test_parse_instructor_class_preferences_default_to_one_and_three():
    result = parse_spec("instructor Anna")

    assert result.is_valid
    assert result.spec.instructors[0].roles == ("leader", "follower")
    assert result.spec.instructors[0].preferred_min_classes_per_week == 1
    assert result.spec.instructors[0].preferred_max_classes_per_week == 3


def test_parse_group_time_windows():
    result = parse_spec(
        """group LH1
needs 1 lesson per week
duration 85 minutes
teacher roles leader, follower
time window Monday-Tuesday 17:00-22:30
time window Thursday 18:00-21:00
"""
    )

    assert result.is_valid
    assert [
        (window.day, window.start, window.end)
        for window in result.spec.groups[0].time_windows
    ] == [
        ("Monday", "17:00", "22:30"),
        ("Tuesday", "17:00", "22:30"),
        ("Thursday", "18:00", "21:00"),
    ]


def test_parse_reports_unknown_line_with_number():
    result = parse_spec("lesson blocks\nMonday 18:00-19:25\nnonsense")

    assert not result.is_valid
    assert result.errors[0].line == 3
    assert result.errors[0].message == "Unknown line: nonsense"


def test_parse_accepts_location_with_room_count():
    result = parse_spec("location Main Hall\nrooms 3")

    assert result.is_valid
    assert result.spec.locations[0].name == "Main Hall"
    assert result.spec.locations[0].rooms_count == 3


def test_parse_reports_missing_location_rooms():
    result = parse_spec("location Main Hall")

    assert not result.is_valid
    assert result.spec is None
    assert result.errors[0].line == 1
    assert result.errors[0].message == "Location Main Hall is missing rooms"


def test_parse_reports_missing_group_field():
    result = parse_spec("group Lindy Hop 1\nneeds 1 lesson per week")

    assert not result.is_valid
    assert result.spec is None
    assert result.errors[0].line == 1
    assert result.errors[0].message == "Group Lindy Hop 1 is missing duration"


def test_parse_rejects_removed_group_fields():
    result = parse_spec(
        """group Lindy Hop 1
style Lindy Hop
level beginner
needs 1 lesson per week
duration 85 minutes
teachers 2
"""
    )

    assert not result.is_valid
    assert result.spec is None
    assert result.errors[0].line == 2
    assert result.errors[0].message == "Unknown line: style Lindy Hop"


def test_parse_rejects_students_line():
    result = parse_spec(
        """group Lindy Hop 1
students 24
needs 1 lesson per week
duration 85 minutes
teacher roles leader, follower
"""
    )

    assert not result.is_valid
    assert result.spec is None
    assert result.errors[0].line == 2
    assert result.errors[0].message == "Unknown line: students 24"


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


def test_parse_rejects_time_without_two_digit_hour():
    result = parse_spec("lesson blocks\nMonday 8:00-09:00")

    assert not result.is_valid
    assert result.errors[0].line == 2
    assert result.errors[0].message == "Invalid lesson block: Monday 8:00-09:00"


def test_parse_rejects_time_with_three_digit_hour():
    result = parse_spec("lesson blocks\nMonday 018:00-19:00")

    assert not result.is_valid
    assert result.errors[0].line == 2
    assert result.errors[0].message == "Invalid lesson block: Monday 018:00-19:00"


def test_parse_rejects_time_with_three_digit_minutes():
    result = parse_spec("lesson blocks\nMonday 18:000-19:00")

    assert not result.is_valid
    assert result.errors[0].line == 2
    assert result.errors[0].message == "Invalid lesson block: Monday 18:000-19:00"


def test_parse_rejects_removed_room_line():
    result = parse_spec("room Main Hall")

    assert not result.is_valid
    assert result.spec is None
    assert result.errors[0].line == 1
    assert result.errors[0].message == "Unknown line: room Main Hall"


def test_parse_rejects_capacity_line_on_location():
    result = parse_spec("location Main Hall\nrooms 1\ncapacity nope")

    assert not result.is_valid
    assert result.spec is None
    assert result.errors[0].line == 3
    assert result.errors[0].message == "Unknown line: capacity nope"
