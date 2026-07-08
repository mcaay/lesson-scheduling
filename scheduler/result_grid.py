from scheduler.spec_models import DAYS, to_slot


def build_result_grid(spec, result):
    days = _ordered_days(spec.lesson_blocks)
    room_slots = _room_slots(spec.locations)
    lesson_lookup = {
        (
            lesson.day,
            lesson.start,
            lesson.end,
            lesson.location_name,
            lesson.room_index,
        ): lesson
        for lesson in result.lessons
    }

    rows = []
    for start, end in _ordered_time_blocks(spec.lesson_blocks):
        rows.append(
            {
                "time": f"{start}-{end}",
                "days": [
                    {
                        "name": day,
                        "room_slots": [
                            {
                                "name": room_slot["name"],
                                "location_name": room_slot["location_name"],
                                "room_index": room_slot["room_index"],
                                "lesson": lesson_lookup.get(
                                    (
                                        day,
                                        start,
                                        end,
                                        room_slot["location_name"],
                                        room_slot["room_index"],
                                    )
                                ),
                            }
                            for room_slot in room_slots
                        ],
                    }
                    for day in days
                ],
            }
        )

    return {
        "days": [{"name": day} for day in days],
        "room_slots": room_slots,
        "rows": rows,
    }


def _room_slots(locations):
    slots = []
    for location in locations:
        for room_index in range(1, location.rooms_count + 1):
            name = location.name
            if location.rooms_count > 1:
                name = f"{location.name} {room_index}"
            slots.append(
                {
                    "name": name,
                    "location_name": location.name,
                    "room_index": room_index,
                }
            )
    return slots


def _ordered_days(lesson_blocks):
    days = {block.time.day for block in lesson_blocks}
    return [day for day in DAYS if day in days]


def _ordered_time_blocks(lesson_blocks):
    blocks = {(block.time.start, block.time.end) for block in lesson_blocks}
    return sorted(blocks, key=lambda block: (to_slot(block[0]), to_slot(block[1])))
