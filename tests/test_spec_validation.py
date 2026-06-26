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


def test_validation_rejects_no_eligible_instructor():
    text = EXAMPLE_SPEC.replace(
        "can teach Lindy Hop beginner, Solo Jazz beginner",
        "can teach Solo Jazz beginner",
    )
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group Lindy Hop 1 has no eligible instructors for Lindy Hop beginner"
    )


def test_validation_rejects_two_teacher_group_with_pair_ban():
    text = EXAMPLE_SPEC.replace("prefers teaching with Ivona", "cannot teach with Ivona")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group Lindy Hop 1 needs two teachers, but every eligible pair is banned"
    )


def test_validation_rejects_no_matching_duration_block():
    text = EXAMPLE_SPEC.replace("duration 85 minutes", "duration 60 minutes")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert (
        errors[0].message
        == "Group Lindy Hop 1 has no lesson block that matches duration and instructor availability"
    )
