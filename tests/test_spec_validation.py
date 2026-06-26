from scheduler.examples import EXAMPLE_SPEC
from scheduler.spec_parser import parse_spec
from scheduler.spec_validation import validate_spec


def test_validation_accepts_example_spec():
    result = parse_spec(EXAMPLE_SPEC)

    errors = validate_spec(result.spec)

    assert errors == []


def test_validation_rejects_group_too_large_for_all_rooms():
    text = EXAMPLE_SPEC.replace("students 24", "students 99")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group Lindy Hop 1 has 99 students, but no room can hold that many"
    )


def test_validation_reports_no_eligible_instructors_for_two_teacher_group():
    text = EXAMPLE_SPEC.replace(
        "can teach Lindy Hop beginner, Solo Jazz beginner",
        "can teach Solo Jazz beginner",
    ).replace(
        "instructor Ivona\ncan teach Lindy Hop beginner",
        "instructor Ivona\ncan teach Solo Jazz beginner",
    )
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group Lindy Hop 1 needs 2 teachers, but only 0 eligible instructors are available"
    )


def test_validation_reports_too_few_eligible_instructors_for_two_teacher_group():
    text = EXAMPLE_SPEC.replace(
        "instructor Ivona\ncan teach Lindy Hop beginner",
        "instructor Ivona\ncan teach Solo Jazz beginner",
    )
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group Lindy Hop 1 needs 2 teachers, but only 1 eligible instructor is available"
    )


def test_validation_rejects_two_teacher_group_with_pair_ban():
    text = EXAMPLE_SPEC.replace("prefers teaching with Ivona", "cannot teach with Ivona")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group Lindy Hop 1 needs two teachers, but every eligible pair is banned"
    )


def test_validation_rejects_unknown_instructor_in_pair_reference():
    text = EXAMPLE_SPEC.replace("prefers teaching with Ivona", "cannot teach with Iwona")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert errors[0].message == "Instructor Anna references unknown instructor Iwona"


def test_validation_pair_ban_error_does_not_add_duration_error():
    text = EXAMPLE_SPEC.replace("prefers teaching with Ivona", "cannot teach with Ivona")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert [error.message for error in errors] == [
        "Group Lindy Hop 1 needs two teachers, but every eligible pair is banned"
    ]


def test_validation_reports_no_eligible_instructor_for_one_teacher_group():
    text = EXAMPLE_SPEC.replace("teachers 2", "teachers 1")
    text = text.replace(
        "can teach Lindy Hop beginner, Solo Jazz beginner", "can teach Solo Jazz beginner"
    )
    text = text.replace("can teach Lindy Hop beginner", "can teach Solo Jazz beginner")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group Lindy Hop 1 has no eligible instructors for Lindy Hop beginner"
    )


def test_validation_rejects_unsupported_teacher_count():
    text = EXAMPLE_SPEC.replace("teachers 2", "teachers 3")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert errors[0].message == "Group Lindy Hop 1 must require 1 or 2 teachers"


def test_validation_rejects_available_pair_when_pair_is_banned():
    text = EXAMPLE_SPEC + """
instructor Solo
can teach Lindy Hop beginner
available Friday 18:00-19:25
"""
    text = text.replace("prefers teaching with Ivona", "cannot teach with Ivona")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group Lindy Hop 1 has no lesson block that matches duration and instructor availability"
    )


def test_validation_rejects_no_matching_duration_block():
    text = EXAMPLE_SPEC.replace("duration 85 minutes", "duration 60 minutes")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group Lindy Hop 1 has no lesson block that matches duration and instructor availability"
    )
