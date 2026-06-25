from dataclasses import dataclass, field


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def to_slot(value):
    hour_text, minute_text = value.split(":", 1)
    hour = int(hour_text)
    minute = int(minute_text)
    if hour < 0 or hour > 23:
        raise ValueError(f"Time must use HH:MM with hours from 00 to 23: {value}")
    if minute < 0 or minute > 59:
        raise ValueError(f"Time must use HH:MM with minutes from 00 to 59: {value}")
    if minute % 5 != 0:
        raise ValueError(f"Time must use a 5-minute grid: {value}")
    return (hour * 60 + minute) // 5


def from_slot(slot):
    minutes = slot * 5
    hour = minutes // 60
    minute = minutes % 60
    return f"{hour:02d}:{minute:02d}"


@dataclass(frozen=True)
class TimeRange:
    day: str
    start: str
    end: str

    @property
    def duration_minutes(self):
        start_slot = to_slot(self.start)
        end_slot = to_slot(self.end)
        if end_slot <= start_slot:
            raise ValueError(
                f"Time range end must be after start: {self.start}-{self.end}"
            )
        return (end_slot - start_slot) * 5


@dataclass(frozen=True)
class Room:
    name: str
    capacity: int


@dataclass(frozen=True)
class Instructor:
    name: str
    can_teach: tuple[str, ...] = ()
    availability: tuple[TimeRange, ...] = ()
    prefers_with: tuple[str, ...] = ()
    avoids_with: tuple[str, ...] = ()
    cannot_teach_with: tuple[str, ...] = ()


@dataclass(frozen=True)
class Group:
    name: str
    students: int
    style: str
    level: str
    lessons_per_week: int
    duration_minutes: int
    teachers_required: int

    @property
    def teaching_key(self):
        return f"{self.style} {self.level}"


@dataclass(frozen=True)
class LessonBlock:
    time: TimeRange

    @property
    def duration_minutes(self):
        return self.time.duration_minutes


@dataclass(frozen=True)
class ScheduleSpec:
    lesson_blocks: tuple[LessonBlock, ...] = ()
    rooms: tuple[Room, ...] = ()
    instructors: tuple[Instructor, ...] = ()
    groups: tuple[Group, ...] = ()


@dataclass(frozen=True)
class SpecError:
    line: int | None
    message: str


@dataclass(frozen=True)
class ValidationResult:
    spec: ScheduleSpec | None
    errors: tuple[SpecError, ...] = field(default_factory=tuple)

    @property
    def is_valid(self):
        return not self.errors and self.spec is not None
