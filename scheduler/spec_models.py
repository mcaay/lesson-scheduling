import re
from dataclasses import dataclass, field


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
TIME_RE = re.compile(r"\d{2}:\d{2}")
GROUP_INSTANCE_RE = re.compile(r"^(?P<level>.+)\s+#(?P<number>\d+)$")
TEACHER_ROLES = ("leader", "follower", "solo")
DEFAULT_TEACHER_ROLES = ("leader", "follower")


def is_hhmm_time(value):
    return TIME_RE.fullmatch(value) is not None


def to_slot(value):
    if not is_hhmm_time(value):
        raise ValueError(f"Time must use HH:MM: {value}")
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
class Location:
    name: str
    rooms_count: int


@dataclass(frozen=True)
class Instructor:
    name: str
    roles: tuple[str, ...] = DEFAULT_TEACHER_ROLES
    preferred_min_classes_per_week: int = 1
    preferred_max_classes_per_week: int = 3
    can_teach: tuple[str, ...] = ()
    availability: tuple[TimeRange, ...] = ()
    prefers_with: tuple[str, ...] = ()
    avoids_with: tuple[str, ...] = ()
    cannot_teach_with: tuple[str, ...] = ()


@dataclass(frozen=True)
class Group:
    name: str
    lessons_per_week: int
    duration_minutes: int
    teacher_roles: tuple[str, ...] = ("leader",)

    @property
    def level_name(self):
        match = GROUP_INSTANCE_RE.fullmatch(self.name)
        if match:
            return match.group("level")
        return self.name

    @property
    def instance_number(self):
        match = GROUP_INSTANCE_RE.fullmatch(self.name)
        if match:
            return int(match.group("number"))
        return None

    @property
    def teachers_required(self):
        return len(self.teacher_roles)


@dataclass(frozen=True)
class LessonBlock:
    time: TimeRange

    @property
    def duration_minutes(self):
        return self.time.duration_minutes


@dataclass(frozen=True)
class ScheduleSpec:
    lesson_blocks: tuple[LessonBlock, ...] = ()
    locations: tuple[Location, ...] = ()
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


def instructor_can_teach_group(instructor, group):
    return group.level_name in instructor.can_teach
