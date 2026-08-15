from scheduler.examples import EXAMPLE_SPEC
from scheduler.spec_parser import parse_spec
from scheduler.spec_validation import validate_spec


TWO_TEACHER_SPEC = """lesson blocks
Monday 18:00-19:25

location Swing Studio
rooms 1

instructor Ania
roles follower
prefers minimum 1 class per week
prefers maximum 3 classes per week
can teach LH1
available Monday 17:00-22:30
prefers teaching with Mateusz

instructor Mateusz
roles leader
prefers minimum 1 class per week
prefers maximum 3 classes per week
can teach LH1
available Monday 17:00-22:30
prefers teaching with Ania

group LH1
needs 1 lesson per week
duration 85 minutes
teacher roles leader, follower
"""


def test_validation_accepts_example_spec():
    result = parse_spec(EXAMPLE_SPEC)

    errors = validate_spec(result.spec)

    assert errors == []


def test_validation_reports_no_eligible_instructors_for_two_teacher_group():
    text = TWO_TEACHER_SPEC.replace("can teach LH1", "can teach Solo Jazz")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert errors[0].message == "Group LH1 needs a leader teacher, but none are eligible"


def test_validation_reports_too_few_eligible_instructors_for_two_teacher_group():
    text = TWO_TEACHER_SPEC.replace("can teach LH1", "can teach Solo Jazz", 1)
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group LH1 needs a follower teacher, but none are eligible"
    )


def test_validation_rejects_two_teacher_group_with_pair_ban():
    text = TWO_TEACHER_SPEC.replace(
        "prefers teaching with Mateusz", "cannot teach with Mateusz"
    )
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group LH1 needs two teachers, but every eligible role pair is banned"
    )


def test_validation_rejects_unknown_instructor_in_pair_reference():
    text = TWO_TEACHER_SPEC.replace(
        "prefers teaching with Mateusz", "cannot teach with Iwona"
    )
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert errors[0].message == "Instructor Ania references unknown instructor Iwona"


def test_validation_rejects_instructor_minimum_higher_than_maximum():
    text = TWO_TEACHER_SPEC.replace(
        "prefers minimum 1 class per week",
        "prefers minimum 4 classes per week",
        1,
    )
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Instructor Ania preferred minimum classes per week cannot be higher than preferred maximum"
    )


def test_validation_treats_zero_maximum_as_not_available_for_assignments():
    text = TWO_TEACHER_SPEC.replace(
        "prefers minimum 1 class per week\nprefers maximum 3 classes per week",
        "prefers minimum 0 classes per week\nprefers maximum 0 classes per week",
        1,
    )
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group LH1 needs a follower teacher, but none are eligible"
    )


def test_validation_pair_ban_error_does_not_add_duration_error():
    text = TWO_TEACHER_SPEC.replace(
        "prefers teaching with Mateusz", "cannot teach with Mateusz"
    )
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert [error.message for error in errors] == [
        "Group LH1 needs two teachers, but every eligible role pair is banned"
    ]


def test_validation_reports_no_eligible_instructor_for_one_teacher_group():
    text = TWO_TEACHER_SPEC.replace("teacher roles leader, follower", "teacher roles leader")
    text = text.replace("can teach LH1", "can teach Solo Jazz")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert errors[0].message == "Group LH1 needs a leader teacher, but none are eligible"


def test_validation_rejects_unsupported_teacher_roles():
    text = TWO_TEACHER_SPEC.replace(
        "teacher roles leader, follower",
        "teacher roles leader, follower, assistant",
    )
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert errors[0].message == "Group LH1 must require one or two teacher roles"


def test_validation_rejects_available_pair_when_pair_is_banned():
    text = TWO_TEACHER_SPEC + """
instructor Solo
can teach LH1
available Friday 18:00-19:25
"""
    text = text.replace("prefers teaching with Mateusz", "cannot teach with Mateusz")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group LH1 has no lesson block that matches duration and instructor availability"
    )


def test_validation_rejects_no_matching_duration_block():
    text = TWO_TEACHER_SPEC.replace("duration 85 minutes", "duration 60 minutes")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group LH1 has no lesson block that matches duration and instructor availability"
    )


def test_validation_rejects_no_matching_group_time_window():
    text = TWO_TEACHER_SPEC + "time window Tuesday 18:00-19:25\n"
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group LH1 has no lesson block that matches duration and instructor availability"
    )


def test_validation_rejects_missing_follower_role():
    text = TWO_TEACHER_SPEC.replace("roles follower", "roles leader")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group LH1 needs a follower teacher, but none are eligible"
    )


def test_validation_rejects_location_without_rooms():
    text = TWO_TEACHER_SPEC.replace("rooms 1", "rooms 0")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert errors[0].message == "Location Swing Studio must have at least one room"
