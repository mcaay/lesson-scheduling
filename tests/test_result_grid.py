from scheduler.examples import EXAMPLE_SPEC
from scheduler.result_grid import build_result_grid
from scheduler.solver import ScheduledLesson, SolveResult
from scheduler.spec_parser import parse_spec


def test_result_grid_groups_by_day_location_room_slot_and_lesson_block():
    spec = parse_spec(EXAMPLE_SPEC).spec
    result = SolveResult(
        solved=True,
        lessons=(
            ScheduledLesson(
                group_name="LH1",
                day="Monday",
                start="18:00",
                end="19:25",
                location_name="Swing Studio",
                room_index=1,
                instructor_names=("Ania", "Mateusz"),
            ),
        ),
    )

    grid = build_result_grid(spec, result)

    assert [day["name"] for day in grid["days"]] == [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
    ]
    assert [room_slot["name"] for room_slot in grid["room_slots"]] == [
        "Swing Studio 1",
        "Swing Studio 2",
        "Jazz Loft",
    ]
    assert [row["time"] for row in grid["rows"]] == [
        "18:00-19:25",
        "19:30-20:55",
        "21:00-22:25",
    ]
    assert grid["rows"][0]["days"][0]["room_slots"][0]["lesson"].group_name == "LH1"
    assert grid["rows"][0]["days"][0]["room_slots"][1]["lesson"] is None


def test_result_grid_marks_day_and_time_combinations_that_do_not_exist():
    spec = parse_spec(
        """lesson blocks
Monday 18:00-19:00
Tuesday 19:00-20:00

location Studio
rooms 1
"""
    ).spec
    result = SolveResult(solved=True)

    grid = build_result_grid(spec, result)

    monday_1800 = grid["rows"][0]["days"][0]["room_slots"][0]
    tuesday_1800 = grid["rows"][0]["days"][1]["room_slots"][0]
    assert monday_1800["is_defined"] is True
    assert tuesday_1800["is_defined"] is False
