from scheduler.examples import EXAMPLE_SPEC
from scheduler.spec_models import (
    Group,
    Instructor,
    LessonBlock,
    Location,
    ScheduleSpec,
    TimeRange,
)
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

    assert errors[0].message == (
        "Group LH1 has no matching lesson block with all required instructors available"
    )


def test_validation_rejects_no_matching_duration_block():
    text = TWO_TEACHER_SPEC.replace("duration 85 minutes", "duration 60 minutes")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert errors[0].message == (
        "Group LH1 has no lesson block matching its duration and time windows"
    )


def test_validation_rejects_no_matching_group_time_window():
    text = TWO_TEACHER_SPEC + "time window Tuesday 18:00-19:25\n"
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert errors[0].message == (
        "Group LH1 has no lesson block matching its duration and time windows"
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


def test_validation_rejects_duplicate_names_with_source_line():
    text = TWO_TEACHER_SPEC + """
group LH1
needs 1 lesson per week
duration 85 minutes
teacher roles leader, follower
"""
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    duplicate_error = next(
        error for error in errors if "declared more than once" in error.message
    )
    assert duplicate_error.line == result.spec.groups[-1].line
    assert duplicate_error.message == "Group name LH1 is declared more than once"


def test_validation_allows_zero_maximum_to_disable_default_instructor():
    text = TWO_TEACHER_SPEC.replace(
        "prefers maximum 3 classes per week",
        "prefers maximum 0 classes per week",
        1,
    )
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert not any("preferred minimum" in error.message for error in errors)
    assert any("needs a follower teacher" in error.message for error in errors)


def test_validation_rejects_zero_lessons_and_off_grid_duration():
    text = TWO_TEACHER_SPEC.replace("needs 1 lesson", "needs 0 lessons")
    text = text.replace("duration 85 minutes", "duration 61 minutes")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert any("at least one lesson" in error.message for error in errors)
    assert any("duration must use 5-minute steps" in error.message for error in errors)
    assert all(error.line == result.spec.groups[0].line for error in errors)


def test_validation_rejects_empty_project():
    errors = validate_spec(ScheduleSpec())

    assert [error.message for error in errors] == [
        "At least one lesson block is required",
        "At least one location is required",
        "At least one instructor is required",
        "At least one group is required",
    ]


def test_validation_rejects_unsupported_instructor_role():
    text = TWO_TEACHER_SPEC.replace("roles follower", "roles follower, wizard")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert any(
        error.message == "Instructor Ania uses unsupported role wizard"
        for error in errors
    )


def test_validation_rejects_names_that_cannot_round_trip():
    text = TWO_TEACHER_SPEC.replace("group LH1", "group Swing, advanced")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert any("cannot contain commas" in error.message for error in errors)


def test_validation_rejects_excessive_room_count_before_solving():
    text = TWO_TEACHER_SPEC.replace("rooms 1", "rooms 1000000000")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert any("cannot have more than" in error.message for error in errors)


def test_validation_rejects_excessive_candidate_count():
    block = LessonBlock(TimeRange("Monday", "18:00", "19:00"))
    availability = (TimeRange("Monday", "17:00", "22:00"),)
    instructors = tuple(
        Instructor(
            name=f"Instructor {index}",
            can_teach=("Course",),
            availability=availability,
        )
        for index in range(100)
    )
    spec = ScheduleSpec(
        lesson_blocks=(block,),
        locations=(Location("Studio", 20),),
        instructors=instructors,
        groups=(Group("Course", 1, 60, ("leader", "follower")),),
    )

    errors = validate_spec(spec)

    assert any("too many possible assignments" in error.message for error in errors)


def test_validation_distinguishes_too_few_distinct_teachers_from_pair_ban():
    text = TWO_TEACHER_SPEC.replace(
        "instructor Mateusz",
        "instructor Disabled Mateusz",
    ).replace(
        "can teach LH1\navailable Monday 17:00-22:30\nprefers teaching with Ania",
        "can teach Other\navailable Monday 17:00-22:30\nprefers teaching with Ania",
        1,
    )
    text = text.replace("roles follower", "roles leader, follower")
    text = text.replace("prefers teaching with Mateusz", "")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert any("needs two distinct teachers" in error.message for error in errors)
