# Dance Scheduler MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable Django MVP for account-free dance lesson scheduling with form input, editable raw spec, validation, CP-SAT solving, schedule display, and spec import/download.

**Architecture:** Keep scheduling logic in plain Python modules under `scheduler/` and keep Django views thin. The browser posts form/spec data, the app parses and validates it, the solver produces an in-memory result, and the result is rendered without saving scheduling data to the database.

**Tech Stack:** Python, Django, sqlite, OR-Tools CP-SAT, pytest, pytest-django, Django templates, small plain JavaScript helpers.

---

## File Structure

- Create `pyproject.toml`: project metadata, runtime dependencies, test dependencies, pytest config.
- Create `manage.py`: Django command entrypoint.
- Create `lesson_scheduling/__init__.py`: Django project package marker.
- Create `lesson_scheduling/settings.py`: simple Django settings using sqlite.
- Create `lesson_scheduling/urls.py`: route root URLs into `scheduler.urls`.
- Create `lesson_scheduling/wsgi.py`: WSGI entrypoint.
- Create `scheduler/__init__.py`: app package marker.
- Create `scheduler/apps.py`: Django app config.
- Create `scheduler/urls.py`: app routes.
- Create `scheduler/views.py`: function-based views for editor, run, import, and download.
- Create `scheduler/spec_models.py`: plain dataclasses for the scheduling spec and parsed errors.
- Create `scheduler/spec_parser.py`: raw text spec parser.
- Create `scheduler/spec_serializer.py`: stable raw spec serializer.
- Create `scheduler/spec_validation.py`: deterministic validation before solving.
- Create `scheduler/solver.py`: OR-Tools model builder and result extraction.
- Create `scheduler/examples.py`: default raw spec shown on first load.
- Create `scheduler/forms.py`: Django forms for raw spec upload and form-first editor payload.
- Create `scheduler/static/scheduler/app.js`: small JavaScript for toggling raw spec and downloading generated text.
- Create `scheduler/static/scheduler/styles.css`: restrained product styling.
- Create `scheduler/templates/scheduler/base.html`: base shell.
- Create `scheduler/templates/scheduler/editor.html`: form-first page with raw spec toggle.
- Create `scheduler/templates/scheduler/result.html`: weekly schedule result view.
- Create `tests/conftest.py`: pytest-django setup.
- Create `tests/test_spec_parser.py`: parser tests.
- Create `tests/test_spec_serializer.py`: serializer tests.
- Create `tests/test_spec_validation.py`: validation tests.
- Create `tests/test_solver.py`: CP-SAT solver tests.
- Create `tests/test_views.py`: workflow tests for editor, run, import, and download.

## Task 1: Django Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `manage.py`
- Create: `lesson_scheduling/__init__.py`
- Create: `lesson_scheduling/settings.py`
- Create: `lesson_scheduling/urls.py`
- Create: `lesson_scheduling/wsgi.py`
- Create: `scheduler/__init__.py`
- Create: `scheduler/apps.py`
- Create: `scheduler/urls.py`
- Create: `scheduler/views.py`
- Create: `scheduler/templates/scheduler/base.html`
- Create: `scheduler/templates/scheduler/editor.html`
- Create: `tests/conftest.py`
- Create: `tests/test_project_boot.py`

- [ ] **Step 1: Write the failing boot test**

Create `tests/conftest.py`:

```python
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lesson_scheduling.settings")
```

Create `tests/test_project_boot.py`:

```python
from django.urls import reverse


def test_editor_page_loads(client):
    response = client.get(reverse("scheduler:editor"))

    assert response.status_code == 200
    assert b"Dance Lesson Scheduler" in response.content
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_project_boot.py -v`

Expected: failure because Django, settings, URLs, and views are not created yet.

- [ ] **Step 3: Add project dependencies**

Create `pyproject.toml`:

```toml
[project]
name = "lesson-scheduling"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "django>=5.2,<6.0",
    "ortools>=9.10,<10.0",
]

[project.optional-dependencies]
test = [
    "pytest>=8.0,<9.0",
    "pytest-django>=4.8,<5.0",
]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "lesson_scheduling.settings"
python_files = ["test_*.py"]
testpaths = ["tests"]
```

- [ ] **Step 4: Add the minimal Django project**

Create `manage.py`:

```python
#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lesson_scheduling.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

Create `lesson_scheduling/__init__.py`:

```python
```

Create `lesson_scheduling/settings.py`:

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "development-only-secret-key"
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "scheduler",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "lesson_scheduling.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "lesson_scheduling.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

Create `lesson_scheduling/urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    path("", include("scheduler.urls")),
]
```

Create `lesson_scheduling/wsgi.py`:

```python
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lesson_scheduling.settings")

application = get_wsgi_application()
```

Create `scheduler/__init__.py`:

```python
```

Create `scheduler/apps.py`:

```python
from django.apps import AppConfig


class SchedulerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "scheduler"
```

Create `scheduler/urls.py`:

```python
from django.urls import path

from . import views

app_name = "scheduler"

urlpatterns = [
    path("", views.editor, name="editor"),
]
```

Create `scheduler/views.py`:

```python
from django.shortcuts import render


def editor(request):
    return render(request, "scheduler/editor.html")
```

Create `scheduler/templates/scheduler/base.html`:

```html
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Dance Lesson Scheduler</title>
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
```

Create `scheduler/templates/scheduler/editor.html`:

```html
{% extends "scheduler/base.html" %}

{% block content %}
<main>
    <h1>Dance Lesson Scheduler</h1>
</main>
{% endblock %}
```

- [ ] **Step 5: Run the boot test**

Run: `python -m pytest tests/test_project_boot.py -v`

Expected: `1 passed`.

- [ ] **Step 6: Run Django system check**

Run: `python manage.py check`

Expected: `System check identified no issues`.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml manage.py lesson_scheduling scheduler tests
git commit -m "Build Django project skeleton"
```

## Task 2: Spec Data Model And Example Fixture

**Files:**
- Create: `scheduler/spec_models.py`
- Create: `scheduler/examples.py`
- Create: `tests/test_spec_models.py`

- [ ] **Step 1: Write the failing model tests**

Create `tests/test_spec_models.py`:

```python
from scheduler.examples import EXAMPLE_SPEC
from scheduler.spec_models import TimeRange, to_slot


def test_to_slot_uses_five_minute_grid():
    assert to_slot("18:00") == 216
    assert to_slot("18:05") == 217


def test_time_range_duration_minutes():
    time_range = TimeRange(day="Monday", start="18:00", end="19:25")

    assert time_range.duration_minutes == 85


def test_example_spec_contains_required_sections():
    assert "lesson blocks" in EXAMPLE_SPEC
    assert "room Main Hall" in EXAMPLE_SPEC
    assert "instructor Anna" in EXAMPLE_SPEC
    assert "group Lindy Hop 1" in EXAMPLE_SPEC
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_spec_models.py -v`

Expected: failure because `scheduler.spec_models` and `scheduler.examples` do not exist.

- [ ] **Step 3: Add the spec model**

Create `scheduler/spec_models.py`:

```python
from dataclasses import dataclass, field


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def to_slot(value):
    hour_text, minute_text = value.split(":", 1)
    hour = int(hour_text)
    minute = int(minute_text)
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
        return (to_slot(self.end) - to_slot(self.start)) * 5


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
```

- [ ] **Step 4: Add the example spec**

Create `scheduler/examples.py`:

```python
EXAMPLE_SPEC = """lesson blocks
Monday-Thursday 18:00-19:25
Monday-Thursday 19:30-20:55
Monday-Thursday 21:00-22:25

room Main Hall
capacity 30

room Small Studio
capacity 16

instructor Anna
can teach Lindy Hop beginner, Solo Jazz beginner
available Monday-Thursday 17:00-22:30
prefers teaching with Ivona
cannot teach with Ana

instructor Ivona
can teach Lindy Hop beginner
available Monday-Thursday 17:00-22:30
prefers teaching with Anna

group Lindy Hop 1
students 24
style Lindy Hop
level beginner
needs 1 lesson per week
duration 85 minutes
teachers 2
"""
```

- [ ] **Step 5: Run the model tests**

Run: `python -m pytest tests/test_spec_models.py -v`

Expected: `3 passed`.

- [ ] **Step 6: Commit**

```bash
git add scheduler/spec_models.py scheduler/examples.py tests/test_spec_models.py
git commit -m "Define scheduling spec model"
```

## Task 3: Raw Spec Parser

**Files:**
- Create: `scheduler/spec_parser.py`
- Create: `tests/test_spec_parser.py`

- [ ] **Step 1: Write parser tests**

Create `tests/test_spec_parser.py`:

```python
from scheduler.examples import EXAMPLE_SPEC
from scheduler.spec_parser import parse_spec


def test_parse_example_spec():
    result = parse_spec(EXAMPLE_SPEC)

    assert result.is_valid
    assert len(result.spec.lesson_blocks) == 12
    assert [room.name for room in result.spec.rooms] == ["Main Hall", "Small Studio"]
    assert [instructor.name for instructor in result.spec.instructors] == ["Anna", "Ivona"]
    assert result.spec.groups[0].name == "Lindy Hop 1"
    assert result.spec.groups[0].duration_minutes == 85


def test_parse_reports_unknown_line_with_number():
    result = parse_spec("lesson blocks\nMonday 18:00-19:25\nnonsense")

    assert not result.is_valid
    assert result.errors[0].line == 3
    assert result.errors[0].message == "Unknown line: nonsense"


def test_parse_reports_missing_capacity():
    result = parse_spec("room Main Hall")

    assert not result.is_valid
    assert result.errors[0].line == 1
    assert result.errors[0].message == "Room Main Hall is missing capacity"
```

- [ ] **Step 2: Run the parser tests to verify they fail**

Run: `python -m pytest tests/test_spec_parser.py -v`

Expected: failure because `parse_spec` does not exist.

- [ ] **Step 3: Add the parser**

Create `scheduler/spec_parser.py`:

```python
import re

from .spec_models import (
    DAYS,
    Group,
    Instructor,
    LessonBlock,
    Room,
    ScheduleSpec,
    SpecError,
    TimeRange,
    ValidationResult,
)


DAY_ALIASES = {day: day for day in DAYS}


def parse_spec(text):
    parser = _Parser(text)
    return parser.parse()


class _Parser:
    def __init__(self, text):
        self.lines = [(number, line.strip()) for number, line in enumerate(text.splitlines(), start=1)]
        self.errors = []
        self.lesson_blocks = []
        self.rooms = []
        self.instructors = []
        self.groups = []
        self.current = None

    def parse(self):
        for line_number, line in self.lines:
            if not line:
                continue
            if line == "lesson blocks":
                self.current = ("lesson_blocks", None, line_number)
                continue
            if line.startswith("room "):
                self.current = ("room", {"name": line[5:], "capacity": None}, line_number)
                self.rooms.append(self.current[1])
                continue
            if line.startswith("instructor "):
                self.current = ("instructor", self._new_instructor(line[11:]), line_number)
                self.instructors.append(self.current[1])
                continue
            if line.startswith("group "):
                self.current = ("group", self._new_group(line[6:]), line_number)
                self.groups.append(self.current[1])
                continue
            self._parse_body_line(line_number, line)

        self._check_required_fields()
        if self.errors:
            return ValidationResult(spec=None, errors=tuple(self.errors))
        return ValidationResult(spec=self._build_spec())

    def _new_instructor(self, name):
        return {
            "name": name,
            "can_teach": [],
            "availability": [],
            "prefers_with": [],
            "avoids_with": [],
            "cannot_teach_with": [],
        }

    def _new_group(self, name):
        return {
            "name": name,
            "students": None,
            "style": None,
            "level": None,
            "lessons_per_week": None,
            "duration_minutes": None,
            "teachers_required": None,
        }

    def _parse_body_line(self, line_number, line):
        if self.current is None:
            self.errors.append(SpecError(line_number, f"Unknown line: {line}"))
            return
        section, data, section_line = self.current
        if section == "lesson_blocks":
            self._parse_lesson_block(line_number, line)
        elif section == "room":
            self._parse_room_line(line_number, line, data)
        elif section == "instructor":
            self._parse_instructor_line(line_number, line, data)
        elif section == "group":
            self._parse_group_line(line_number, line, data)

    def _parse_lesson_block(self, line_number, line):
        match = re.fullmatch(r"(.+) (\d\d:\d\d)-(\d\d:\d\d)", line)
        if not match:
            self.errors.append(SpecError(line_number, f"Invalid lesson block: {line}"))
            return
        day_text, start, end = match.groups()
        for day in self._expand_days(line_number, day_text):
            self.lesson_blocks.append(LessonBlock(TimeRange(day=day, start=start, end=end)))

    def _parse_room_line(self, line_number, line, data):
        if line.startswith("capacity "):
            data["capacity"] = int(line[9:])
            return
        self.errors.append(SpecError(line_number, f"Unknown line: {line}"))

    def _parse_instructor_line(self, line_number, line, data):
        if line.startswith("can teach "):
            data["can_teach"] = self._split_list(line[10:])
            return
        if line.startswith("available "):
            data["availability"].extend(self._parse_time_ranges(line_number, line[10:]))
            return
        if line.startswith("prefers teaching with "):
            data["prefers_with"].extend(self._split_list(line[22:]))
            return
        if line.startswith("avoid teaching with "):
            data["avoids_with"].extend(self._split_list(line[20:]))
            return
        if line.startswith("cannot teach with "):
            data["cannot_teach_with"].extend(self._split_list(line[18:]))
            return
        self.errors.append(SpecError(line_number, f"Unknown line: {line}"))

    def _parse_group_line(self, line_number, line, data):
        if line.startswith("students "):
            data["students"] = int(line[9:])
            return
        if line.startswith("style "):
            data["style"] = line[6:]
            return
        if line.startswith("level "):
            data["level"] = line[6:]
            return
        if line.startswith("needs ") and line.endswith(" lesson per week"):
            data["lessons_per_week"] = int(line[6:-16])
            return
        if line.startswith("duration ") and line.endswith(" minutes"):
            data["duration_minutes"] = int(line[9:-8])
            return
        if line.startswith("teachers "):
            data["teachers_required"] = int(line[9:])
            return
        self.errors.append(SpecError(line_number, f"Unknown line: {line}"))

    def _parse_time_ranges(self, line_number, text):
        match = re.fullmatch(r"(.+) (\d\d:\d\d)-(\d\d:\d\d)", text)
        if not match:
            self.errors.append(SpecError(line_number, f"Invalid time range: {text}"))
            return []
        day_text, start, end = match.groups()
        return [TimeRange(day=day, start=start, end=end) for day in self._expand_days(line_number, day_text)]

    def _expand_days(self, line_number, text):
        if "-" not in text:
            return [DAY_ALIASES[text]]
        start_text, end_text = text.split("-", 1)
        start_index = DAYS.index(DAY_ALIASES[start_text])
        end_index = DAYS.index(DAY_ALIASES[end_text])
        return DAYS[start_index : end_index + 1]

    def _split_list(self, text):
        return [item.strip() for item in text.split(",") if item.strip()]

    def _check_required_fields(self):
        for room in self.rooms:
            if room["capacity"] is None:
                self.errors.append(SpecError(self._section_line("room", room), f"Room {room['name']} is missing capacity"))
        for group in self.groups:
            for field_name in ["students", "style", "level", "lessons_per_week", "duration_minutes", "teachers_required"]:
                if group[field_name] is None:
                    self.errors.append(SpecError(self._section_line("group", group), f"Group {group['name']} is missing {field_name}"))

    def _section_line(self, section, data):
        for name, value, line_number in [self.current] + []:
            if name == section and value is data:
                return line_number
        for line_number, line in self.lines:
            if line == f"{section} {data['name']}":
                return line_number
        return None

    def _build_spec(self):
        return ScheduleSpec(
            lesson_blocks=tuple(self.lesson_blocks),
            rooms=tuple(Room(name=item["name"], capacity=item["capacity"]) for item in self.rooms),
            instructors=tuple(
                Instructor(
                    name=item["name"],
                    can_teach=tuple(item["can_teach"]),
                    availability=tuple(item["availability"]),
                    prefers_with=tuple(item["prefers_with"]),
                    avoids_with=tuple(item["avoids_with"]),
                    cannot_teach_with=tuple(item["cannot_teach_with"]),
                )
                for item in self.instructors
            ),
            groups=tuple(
                Group(
                    name=item["name"],
                    students=item["students"],
                    style=item["style"],
                    level=item["level"],
                    lessons_per_week=item["lessons_per_week"],
                    duration_minutes=item["duration_minutes"],
                    teachers_required=item["teachers_required"],
                )
                for item in self.groups
            ),
        )
```

- [ ] **Step 4: Run parser tests**

Run: `python -m pytest tests/test_spec_parser.py -v`

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add scheduler/spec_parser.py tests/test_spec_parser.py
git commit -m "Parse raw schedule specs"
```

## Task 4: Stable Spec Serializer

**Files:**
- Create: `scheduler/spec_serializer.py`
- Create: `tests/test_spec_serializer.py`

- [ ] **Step 1: Write serializer tests**

Create `tests/test_spec_serializer.py`:

```python
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
```

- [ ] **Step 2: Run serializer tests to verify they fail**

Run: `python -m pytest tests/test_spec_serializer.py -v`

Expected: failure because `serialize_spec` does not exist.

- [ ] **Step 3: Add serializer**

Create `scheduler/spec_serializer.py`:

```python
def serialize_spec(spec):
    lines = []
    lines.extend(_lesson_block_lines(spec.lesson_blocks))
    lines.append("")
    for room in spec.rooms:
        lines.extend([f"room {room.name}", f"capacity {room.capacity}", ""])
    for instructor in spec.instructors:
        lines.extend(_instructor_lines(instructor))
        lines.append("")
    for group in spec.groups:
        lines.extend(
            [
                f"group {group.name}",
                f"students {group.students}",
                f"style {group.style}",
                f"level {group.level}",
                f"needs {group.lessons_per_week} lesson per week",
                f"duration {group.duration_minutes} minutes",
                f"teachers {group.teachers_required}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _lesson_block_lines(lesson_blocks):
    lines = ["lesson blocks"]
    for block in lesson_blocks:
        lines.append(f"{block.time.day} {block.time.start}-{block.time.end}")
    return lines


def _instructor_lines(instructor):
    lines = [f"instructor {instructor.name}"]
    if instructor.can_teach:
        lines.append(f"can teach {', '.join(instructor.can_teach)}")
    for availability in instructor.availability:
        lines.append(f"available {availability.day} {availability.start}-{availability.end}")
    if instructor.prefers_with:
        lines.append(f"prefers teaching with {', '.join(instructor.prefers_with)}")
    if instructor.avoids_with:
        lines.append(f"avoid teaching with {', '.join(instructor.avoids_with)}")
    if instructor.cannot_teach_with:
        lines.append(f"cannot teach with {', '.join(instructor.cannot_teach_with)}")
    return lines
```

- [ ] **Step 4: Run serializer tests**

Run: `python -m pytest tests/test_spec_serializer.py -v`

Expected: `2 passed`.

- [ ] **Step 5: Run parser and serializer tests together**

Run: `python -m pytest tests/test_spec_parser.py tests/test_spec_serializer.py -v`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add scheduler/spec_serializer.py tests/test_spec_serializer.py
git commit -m "Serialize raw schedule specs"
```

## Task 5: Deterministic Validation

**Files:**
- Create: `scheduler/spec_validation.py`
- Create: `tests/test_spec_validation.py`

- [ ] **Step 1: Write validation tests**

Create `tests/test_spec_validation.py`:

```python
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

    assert errors[0].message == "Group Lindy Hop 1 has 99 students, but no room can hold that many"


def test_validation_rejects_no_eligible_instructor():
    text = EXAMPLE_SPEC.replace("can teach Lindy Hop beginner, Solo Jazz beginner", "can teach Solo Jazz beginner")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert errors[0].message == "Group Lindy Hop 1 has no eligible instructors for Lindy Hop beginner"


def test_validation_rejects_two_teacher_group_with_pair_ban():
    text = EXAMPLE_SPEC.replace("prefers teaching with Ivona", "cannot teach with Ivona")
    result = parse_spec(text)

    errors = validate_spec(result.spec)

    assert errors[0].message == "Group Lindy Hop 1 needs two teachers, but every eligible pair is banned"
```

- [ ] **Step 2: Run validation tests to verify they fail**

Run: `python -m pytest tests/test_spec_validation.py -v`

Expected: failure because `validate_spec` does not exist.

- [ ] **Step 3: Add validation**

Create `scheduler/spec_validation.py`:

```python
from itertools import combinations

from .spec_models import SpecError


def validate_spec(spec):
    errors = []
    errors.extend(_validate_rooms(spec))
    errors.extend(_validate_groups(spec))
    return errors


def _validate_rooms(spec):
    if spec.rooms:
        return []
    return [SpecError(None, "At least one room is required")]


def _validate_groups(spec):
    errors = []
    max_capacity = max(room.capacity for room in spec.rooms)
    for group in spec.groups:
        if group.students > max_capacity:
            errors.append(SpecError(None, f"Group {group.name} has {group.students} students, but no room can hold that many"))
            continue
        eligible = [instructor for instructor in spec.instructors if group.teaching_key in instructor.can_teach]
        if not eligible:
            errors.append(SpecError(None, f"Group {group.name} has no eligible instructors for {group.teaching_key}"))
            continue
        if group.teachers_required == 2 and not _has_allowed_pair(eligible):
            errors.append(SpecError(None, f"Group {group.name} needs two teachers, but every eligible pair is banned"))
            continue
        if not _has_matching_block(spec, group, eligible):
            errors.append(SpecError(None, f"Group {group.name} has no lesson block that matches duration and instructor availability"))
    return errors


def _has_allowed_pair(instructors):
    for first, second in combinations(instructors, 2):
        if second.name in first.cannot_teach_with or first.name in second.cannot_teach_with:
            continue
        return True
    return False


def _has_matching_block(spec, group, eligible):
    matching_blocks = [block for block in spec.lesson_blocks if block.duration_minutes == group.duration_minutes]
    if not matching_blocks:
        return False
    for block in matching_blocks:
        available = [instructor for instructor in eligible if _covers_block(instructor.availability, block.time)]
        if group.teachers_required == 1 and available:
            return True
        if group.teachers_required == 2 and _has_allowed_pair(available):
            return True
    return False


def _covers_block(ranges, block_time):
    for time_range in ranges:
        if time_range.day != block_time.day:
            continue
        if time_range.start <= block_time.start and time_range.end >= block_time.end:
            return True
    return False
```

- [ ] **Step 4: Run validation tests**

Run: `python -m pytest tests/test_spec_validation.py -v`

Expected: `4 passed`.

- [ ] **Step 5: Run parser, serializer, and validation tests**

Run: `python -m pytest tests/test_spec_parser.py tests/test_spec_serializer.py tests/test_spec_validation.py -v`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add scheduler/spec_validation.py tests/test_spec_validation.py
git commit -m "Validate raw schedule specs"
```

## Task 6: First CP-SAT Solver

**Files:**
- Create: `scheduler/solver.py`
- Create: `tests/test_solver.py`

- [ ] **Step 1: Write solver tests**

Create `tests/test_solver.py`:

```python
from scheduler.examples import EXAMPLE_SPEC
from scheduler.solver import solve_schedule
from scheduler.spec_parser import parse_spec


def test_solver_finds_schedule_for_example_spec():
    spec = parse_spec(EXAMPLE_SPEC).spec

    result = solve_schedule(spec)

    assert result.solved
    assert len(result.lessons) == 1
    lesson = result.lessons[0]
    assert lesson.group_name == "Lindy Hop 1"
    assert lesson.room_name == "Main Hall"
    assert set(lesson.instructor_names) == {"Anna", "Ivona"}


def test_solver_reports_unsolved_when_room_conflict_is_forced():
    text = EXAMPLE_SPEC + """
group Lindy Hop 2
students 24
style Lindy Hop
level beginner
needs 4 lesson per week
duration 85 minutes
teachers 2
"""
    spec = parse_spec(text).spec

    result = solve_schedule(spec)

    assert not result.solved
    assert result.message == "No complete schedule found. The combined constraints are too tight."
```

- [ ] **Step 2: Run solver tests to verify they fail**

Run: `python -m pytest tests/test_solver.py -v`

Expected: failure because `solve_schedule` does not exist.

- [ ] **Step 3: Add solver result dataclasses**

Create `scheduler/solver.py`:

```python
from dataclasses import dataclass
from itertools import combinations

from ortools.sat.python import cp_model

from .spec_validation import _covers_block


@dataclass(frozen=True)
class ScheduledLesson:
    group_name: str
    day: str
    start: str
    end: str
    room_name: str
    instructor_names: tuple[str, ...]


@dataclass(frozen=True)
class SolveResult:
    solved: bool
    lessons: tuple[ScheduledLesson, ...] = ()
    message: str = ""


def solve_schedule(spec):
    candidates = _build_candidates(spec)
    model = cp_model.CpModel()
    variables = {}
    for index, candidate in enumerate(candidates):
        variables[index] = model.NewBoolVar(f"candidate_{index}")
    _add_group_requirements(model, variables, candidates, spec)
    _add_resource_conflicts(model, variables, candidates)
    _add_pair_preferences(model, variables, candidates)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return SolveResult(solved=False, message="No complete schedule found. The combined constraints are too tight.")
    lessons = tuple(_candidate_to_lesson(candidate) for index, candidate in enumerate(candidates) if solver.Value(variables[index]))
    return SolveResult(solved=True, lessons=lessons)
```

- [ ] **Step 4: Add candidate generation and constraints**

Append to `scheduler/solver.py`:

```python
def _build_candidates(spec):
    candidates = []
    for group in spec.groups:
        rooms = [room for room in spec.rooms if room.capacity >= group.students]
        blocks = [block for block in spec.lesson_blocks if block.duration_minutes == group.duration_minutes]
        instructors = [instructor for instructor in spec.instructors if group.teaching_key in instructor.can_teach]
        for room in rooms:
            for block in blocks:
                available = [instructor for instructor in instructors if _covers_block(instructor.availability, block.time)]
                for instructor_names in _instructor_choices(group.teachers_required, available):
                    candidates.append(
                        {
                            "group": group,
                            "room": room,
                            "block": block,
                            "instructor_names": instructor_names,
                            "preference_score": _preference_score(instructor_names, available),
                        }
                    )
    return candidates


def _instructor_choices(required_count, instructors):
    if required_count == 1:
        return [(instructor.name,) for instructor in instructors]
    choices = []
    for first, second in combinations(instructors, 2):
        if second.name in first.cannot_teach_with or first.name in second.cannot_teach_with:
            continue
        choices.append(tuple(sorted([first.name, second.name])))
    return choices


def _add_group_requirements(model, variables, candidates, spec):
    for group in spec.groups:
        group_indexes = [index for index, candidate in enumerate(candidates) if candidate["group"].name == group.name]
        model.Add(sum(variables[index] for index in group_indexes) == group.lessons_per_week)


def _add_resource_conflicts(model, variables, candidates):
    for first_index, first in enumerate(candidates):
        for second_index, second in enumerate(candidates):
            if second_index <= first_index:
                continue
            if not _same_block(first, second):
                continue
            if _conflicts(first, second):
                model.Add(variables[first_index] + variables[second_index] <= 1)


def _same_block(first, second):
    return first["block"].time == second["block"].time


def _conflicts(first, second):
    if first["room"].name == second["room"].name:
        return True
    if first["group"].name == second["group"].name:
        return True
    return bool(set(first["instructor_names"]) & set(second["instructor_names"]))


def _add_pair_preferences(model, variables, candidates):
    objective_terms = []
    for index, candidate in enumerate(candidates):
        score = candidate["preference_score"]
        if score:
            objective_terms.append(score * variables[index])
    if objective_terms:
        model.Maximize(sum(objective_terms))


def _preference_score(instructor_names, instructors):
    if len(instructor_names) != 2:
        return 0
    lookup = {instructor.name: instructor for instructor in instructors}
    first = lookup[instructor_names[0]]
    second = lookup[instructor_names[1]]
    score = 0
    if second.name in first.prefers_with:
        score += 1
    if first.name in second.prefers_with:
        score += 1
    if second.name in first.avoids_with:
        score -= 1
    if first.name in second.avoids_with:
        score -= 1
    return score


def _candidate_to_lesson(candidate):
    block = candidate["block"]
    return ScheduledLesson(
        group_name=candidate["group"].name,
        day=block.time.day,
        start=block.time.start,
        end=block.time.end,
        room_name=candidate["room"].name,
        instructor_names=candidate["instructor_names"],
    )
```

- [ ] **Step 5: Run solver tests**

Run: `python -m pytest tests/test_solver.py -v`

Expected: `2 passed`.

- [ ] **Step 6: Run all non-view tests**

Run: `python -m pytest tests/test_spec_models.py tests/test_spec_parser.py tests/test_spec_serializer.py tests/test_spec_validation.py tests/test_solver.py -v`

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add scheduler/solver.py tests/test_solver.py
git commit -m "Solve simple dance schedules"
```

## Task 7: Editor, Validation, Run, Import, And Download Views

**Files:**
- Create: `scheduler/forms.py`
- Modify: `scheduler/urls.py`
- Modify: `scheduler/views.py`
- Modify: `scheduler/templates/scheduler/editor.html`
- Create: `scheduler/templates/scheduler/result.html`
- Create: `tests/test_views.py`

- [ ] **Step 1: Write view tests**

Create `tests/test_views.py`:

```python
from django.urls import reverse

from scheduler.examples import EXAMPLE_SPEC


def test_editor_shows_example_spec(client):
    response = client.get(reverse("scheduler:editor"))

    assert response.status_code == 200
    assert b"Raw spec" in response.content
    assert b"Lindy Hop 1" in response.content


def test_run_schedule_shows_result(client):
    response = client.post(reverse("scheduler:run"), {"raw_spec": EXAMPLE_SPEC})

    assert response.status_code == 200
    assert b"Generated schedule" in response.content
    assert b"Lindy Hop 1" in response.content


def test_run_schedule_shows_validation_errors(client):
    response = client.post(reverse("scheduler:run"), {"raw_spec": "room Main Hall"})

    assert response.status_code == 200
    assert b"Room Main Hall is missing capacity" in response.content


def test_download_spec_returns_text_file(client):
    response = client.post(reverse("scheduler:download_spec"), {"raw_spec": EXAMPLE_SPEC})

    assert response.status_code == 200
    assert response["Content-Type"] == "text/plain"
    assert response["Content-Disposition"].startswith("attachment;")
    assert b"group Lindy Hop 1" in response.content


def test_import_spec_file_loads_editor(client):
    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile("schedule.txt", EXAMPLE_SPEC.encode("utf-8"), content_type="text/plain")

    response = client.post(reverse("scheduler:import_spec"), {"spec_file": upload})

    assert response.status_code == 200
    assert b"group Lindy Hop 1" in response.content
```

- [ ] **Step 2: Run view tests to verify they fail**

Run: `python -m pytest tests/test_views.py -v`

Expected: failure because routes and view behavior are not complete.

- [ ] **Step 3: Add form**

Create `scheduler/forms.py`:

```python
from django import forms


class RawSpecForm(forms.Form):
    raw_spec = forms.CharField(widget=forms.Textarea, strip=False)
```

- [ ] **Step 4: Add routes**

Modify `scheduler/urls.py`:

```python
from django.urls import path

from . import views

app_name = "scheduler"

urlpatterns = [
    path("", views.editor, name="editor"),
    path("run/", views.run_schedule, name="run"),
    path("download-spec/", views.download_spec, name="download_spec"),
    path("import-spec/", views.import_spec, name="import_spec"),
]
```

- [ ] **Step 5: Add views**

Modify `scheduler/views.py`:

```python
from datetime import date

from django.http import HttpResponse
from django.shortcuts import render

from .examples import EXAMPLE_SPEC
from .forms import RawSpecForm
from .solver import solve_schedule
from .spec_parser import parse_spec
from .spec_validation import validate_spec


def editor(request):
    form = RawSpecForm(initial={"raw_spec": EXAMPLE_SPEC})
    return render(request, "scheduler/editor.html", {"form": form, "errors": []})


def run_schedule(request):
    form = RawSpecForm(request.POST)
    if not form.is_valid():
        return render(request, "scheduler/editor.html", {"form": form, "errors": ["Raw spec is required"]})
    raw_spec = form.cleaned_data["raw_spec"]
    parsed = parse_spec(raw_spec)
    if not parsed.is_valid:
        return render(request, "scheduler/editor.html", {"form": form, "errors": parsed.errors})
    validation_errors = validate_spec(parsed.spec)
    if validation_errors:
        return render(request, "scheduler/editor.html", {"form": form, "errors": validation_errors})
    result = solve_schedule(parsed.spec)
    return render(request, "scheduler/result.html", {"form": form, "result": result})


def download_spec(request):
    form = RawSpecForm(request.POST)
    raw_spec = form.data.get("raw_spec", "")
    filename = f"{date.today().isoformat()}-lesson-schedule.txt"
    response = HttpResponse(raw_spec, content_type="text/plain")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def import_spec(request):
    uploaded_file = request.FILES.get("spec_file")
    raw_spec = uploaded_file.read().decode("utf-8") if uploaded_file else EXAMPLE_SPEC
    form = RawSpecForm(initial={"raw_spec": raw_spec})
    return render(request, "scheduler/editor.html", {"form": form, "errors": []})
```

- [ ] **Step 6: Add editor template**

Modify `scheduler/templates/scheduler/editor.html`:

```html
{% extends "scheduler/base.html" %}

{% block content %}
<main class="page">
    <header class="page-header">
        <h1>Dance Lesson Scheduler</h1>
        <p>Build a weekly dance-class schedule from a readable spec.</p>
    </header>

    {% if errors %}
        <section class="errors">
            <h2>Fix these before running</h2>
            <ul>
                {% for error in errors %}
                    <li>{% if error.line %}Line {{ error.line }}: {% endif %}{{ error.message|default:error }}</li>
                {% endfor %}
            </ul>
        </section>
    {% endif %}

    <form method="post" action="{% url 'scheduler:run' %}">
        {% csrf_token %}
        <section class="panel">
            <div class="panel-heading">
                <h2>Raw spec</h2>
                <p>Edit or paste your saved schedule spec.</p>
            </div>
            {{ form.raw_spec }}
        </section>

        <div class="actions">
            <button type="submit">Run scheduler</button>
            <button type="submit" formaction="{% url 'scheduler:download_spec' %}">Download spec</button>
        </div>
    </form>
</main>
{% endblock %}
```

- [ ] **Step 7: Add result template**

Create `scheduler/templates/scheduler/result.html`:

```html
{% extends "scheduler/base.html" %}

{% block content %}
<main class="page">
    <header class="page-header">
        <h1>Generated schedule</h1>
        <p>The schedule is viewable here. Save your work by downloading the raw spec.</p>
    </header>

    {% if result.solved %}
        <table>
            <thead>
                <tr>
                    <th>Day</th>
                    <th>Time</th>
                    <th>Group</th>
                    <th>Room</th>
                    <th>Instructors</th>
                </tr>
            </thead>
            <tbody>
                {% for lesson in result.lessons %}
                    <tr>
                        <td>{{ lesson.day }}</td>
                        <td>{{ lesson.start }}-{{ lesson.end }}</td>
                        <td>{{ lesson.group_name }}</td>
                        <td>{{ lesson.room_name }}</td>
                        <td>{{ lesson.instructor_names|join:", " }}</td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
    {% else %}
        <section class="errors">
            <h2>No complete schedule found</h2>
            <p>{{ result.message }}</p>
            <p>Try adding lesson blocks, relaxing instructor availability, adding rooms, or loosening pair bans.</p>
        </section>
    {% endif %}

    <form method="post" action="{% url 'scheduler:run' %}">
        {% csrf_token %}
        {{ form.raw_spec }}
        <div class="actions">
            <button type="submit">Run again</button>
            <button type="submit" formaction="{% url 'scheduler:download_spec' %}">Download spec</button>
            <a href="{% url 'scheduler:editor' %}">Start over</a>
        </div>
    </form>
</main>
{% endblock %}
```

- [ ] **Step 8: Run view tests**

Run: `python -m pytest tests/test_views.py -v`

Expected: `5 passed`.

- [ ] **Step 9: Run all tests**

Run: `python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 10: Commit**

```bash
git add scheduler/forms.py scheduler/urls.py scheduler/views.py scheduler/templates tests/test_views.py
git commit -m "Add schedule editor workflow"
```

## Task 8: Form-First Editor And Raw Spec Toggle

**Files:**
- Modify: `scheduler/views.py`
- Create: `scheduler/static/scheduler/app.js`
- Create: `scheduler/static/scheduler/styles.css`
- Modify: `scheduler/templates/scheduler/base.html`
- Modify: `scheduler/templates/scheduler/editor.html`
- Modify: `tests/test_views.py`

- [ ] **Step 1: Add a view test for form-first sections**

Append to `tests/test_views.py`:

```python
def test_editor_has_form_first_sections(client):
    response = client.get(reverse("scheduler:editor"))

    assert b"Lesson blocks" in response.content
    assert b"Rooms" in response.content
    assert b"Instructors" in response.content
    assert b"Groups" in response.content
    assert b"Raw spec" in response.content
    assert b'name="lesson_block_days"' in response.content
    assert b'name="room_name"' in response.content
    assert b'name="instructor_name"' in response.content
    assert b'name="group_name"' in response.content
```

- [ ] **Step 2: Run the new view test to verify it fails**

Run: `python -m pytest tests/test_views.py::test_editor_has_form_first_sections -v`

Expected: failure because the structured sections do not exist.

- [ ] **Step 3: Load static assets in the base template**

Modify `scheduler/templates/scheduler/base.html`:

```html
{% load static %}
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Dance Lesson Scheduler</title>
    <link rel="stylesheet" href="{% static 'scheduler/styles.css' %}">
    <script defer src="{% static 'scheduler/app.js' %}"></script>
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
```

- [ ] **Step 4: Add JavaScript that generates raw spec from form fields**

Create `scheduler/static/scheduler/app.js`:

```javascript
document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector("[data-raw-spec-toggle]");
    const rawSpecPanel = document.querySelector("[data-raw-spec-panel]");
    const rawSpecInput = document.querySelector("[data-raw-spec-input]");
    const specForm = document.querySelector("[data-spec-form]");

    if (!toggle || !rawSpecPanel || !rawSpecInput || !specForm) {
        return;
    }

    toggle.addEventListener("click", () => {
        rawSpecPanel.hidden = !rawSpecPanel.hidden;
        toggle.textContent = rawSpecPanel.hidden ? "Show raw spec" : "Hide raw spec";
    });

    rawSpecInput.addEventListener("input", () => {
        rawSpecInput.dataset.dirty = "true";
    });

    specForm.addEventListener("submit", () => {
        if (rawSpecInput.dataset.dirty !== "true") {
            rawSpecInput.value = buildSpecFromForm(specForm);
        }
    });
});

function value(form, name) {
    const field = form.querySelector(`[name="${name}"]`);
    return field ? field.value.trim() : "";
}

function buildSpecFromForm(form) {
    const lines = [];
    lines.push("lesson blocks");
    lines.push(`${value(form, "lesson_block_days")} ${value(form, "lesson_block_1_start")}-${value(form, "lesson_block_1_end")}`);
    lines.push(`${value(form, "lesson_block_days")} ${value(form, "lesson_block_2_start")}-${value(form, "lesson_block_2_end")}`);
    lines.push(`${value(form, "lesson_block_days")} ${value(form, "lesson_block_3_start")}-${value(form, "lesson_block_3_end")}`);
    lines.push("");

    lines.push(`room ${value(form, "room_name")}`);
    lines.push(`capacity ${value(form, "room_capacity")}`);
    lines.push("");

    lines.push(`instructor ${value(form, "instructor_name")}`);
    lines.push(`can teach ${value(form, "instructor_can_teach")}`);
    lines.push(`available ${value(form, "instructor_available_days")} ${value(form, "instructor_available_start")}-${value(form, "instructor_available_end")}`);
    const preferred = value(form, "instructor_prefers_with");
    const banned = value(form, "instructor_cannot_teach_with");
    if (preferred) {
        lines.push(`prefers teaching with ${preferred}`);
    }
    if (banned) {
        lines.push(`cannot teach with ${banned}`);
    }
    lines.push("");

    lines.push(`instructor ${value(form, "second_instructor_name")}`);
    lines.push(`can teach ${value(form, "second_instructor_can_teach")}`);
    lines.push(`available ${value(form, "second_instructor_available_days")} ${value(form, "second_instructor_available_start")}-${value(form, "second_instructor_available_end")}`);
    lines.push("");

    lines.push(`group ${value(form, "group_name")}`);
    lines.push(`students ${value(form, "group_students")}`);
    lines.push(`style ${value(form, "group_style")}`);
    lines.push(`level ${value(form, "group_level")}`);
    lines.push(`needs ${value(form, "group_lessons_per_week")} lesson per week`);
    lines.push(`duration ${value(form, "group_duration_minutes")} minutes`);
    lines.push(`teachers ${value(form, "group_teachers_required")}`);
    lines.push("");

    return lines.join("\n");
}
```

- [ ] **Step 5: Add simple styling**

Create `scheduler/static/scheduler/styles.css`:

```css
body {
    margin: 0;
    color: #1f2933;
    background: #f7f5f0;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.page {
    max-width: 1100px;
    margin: 0 auto;
    padding: 32px 20px;
}

.page-header {
    margin-bottom: 24px;
}

.page-header h1 {
    margin: 0 0 6px;
    font-size: 32px;
}

.page-header p {
    margin: 0;
    color: #52606d;
}

.workspace {
    display: grid;
    grid-template-columns: 220px 1fr;
    gap: 20px;
}

.steps {
    padding: 16px;
    background: #ffffff;
    border: 1px solid #d9e2ec;
    border-radius: 8px;
}

.steps a {
    display: block;
    padding: 8px 0;
    color: #334e68;
    text-decoration: none;
}

.panel {
    padding: 20px;
    background: #ffffff;
    border: 1px solid #d9e2ec;
    border-radius: 8px;
    margin-bottom: 16px;
}

.panel-heading h2 {
    margin: 0 0 4px;
    font-size: 20px;
}

.panel-heading p {
    margin: 0 0 14px;
    color: #627d98;
}

label {
    display: block;
    margin-bottom: 12px;
    font-weight: 700;
}

input,
textarea {
    width: 100%;
    margin-top: 4px;
    padding: 10px;
    border: 1px solid #bcccdc;
    border-radius: 6px;
    min-height: 360px;
    box-sizing: border-box;
}

input {
    min-height: auto;
    font: inherit;
}

textarea {
    font: 14px/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.field-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
}

.actions {
    display: flex;
    gap: 10px;
    align-items: center;
}

button,
.actions a {
    padding: 10px 14px;
    border: 1px solid #102a43;
    border-radius: 6px;
    background: #102a43;
    color: white;
    text-decoration: none;
    cursor: pointer;
}

.errors {
    padding: 16px;
    margin-bottom: 16px;
    background: #fff5f5;
    border: 1px solid #feb2b2;
    border-radius: 8px;
}

table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    margin-bottom: 20px;
}

th,
td {
    padding: 10px;
    border-bottom: 1px solid #d9e2ec;
    text-align: left;
}
```

- [ ] **Step 6: Replace editor template with concrete form-first controls**

Modify `scheduler/templates/scheduler/editor.html`:

```html
{% extends "scheduler/base.html" %}

{% block content %}
<main class="page">
    <header class="page-header">
        <h1>Dance Lesson Scheduler</h1>
        <p>Describe the weekly dance schedule, run the solver, and save the spec file.</p>
    </header>

    {% if errors %}
        <section class="errors">
            <h2>Fix these before running</h2>
            <ul>
                {% for error in errors %}
                    <li>{% if error.line %}Line {{ error.line }}: {% endif %}{{ error.message|default:error }}</li>
                {% endfor %}
            </ul>
        </section>
    {% endif %}

    <form method="post" enctype="multipart/form-data" action="{% url 'scheduler:import_spec' %}" class="panel">
        {% csrf_token %}
        <div class="panel-heading">
            <h2>Open saved spec</h2>
            <p>Upload a saved text spec to continue working.</p>
        </div>
        <input type="file" name="spec_file" accept=".txt,text/plain">
        <div class="actions">
            <button type="submit">Open spec</button>
        </div>
    </form>

    <form method="post" action="{% url 'scheduler:run' %}" data-spec-form>
        {% csrf_token %}
        <div class="workspace">
            <nav class="steps" aria-label="Setup sections">
                <a href="#lesson-blocks">Lesson blocks</a>
                <a href="#rooms">Rooms</a>
                <a href="#instructors">Instructors</a>
                <a href="#groups">Groups</a>
                <a href="#raw-spec">Raw spec</a>
            </nav>

            <div>
                <section class="panel" id="lesson-blocks">
                    <div class="panel-heading">
                        <h2>Lesson blocks</h2>
                        <p>Define the standard blocks the solver may use.</p>
                    </div>
                    <label>Days
                        <input name="lesson_block_days" value="Monday-Thursday">
                    </label>
                    <div class="field-grid">
                        <label>Block 1 start
                            <input name="lesson_block_1_start" value="18:00">
                        </label>
                        <label>Block 1 end
                            <input name="lesson_block_1_end" value="19:25">
                        </label>
                        <label>Block 2 start
                            <input name="lesson_block_2_start" value="19:30">
                        </label>
                        <label>Block 2 end
                            <input name="lesson_block_2_end" value="20:55">
                        </label>
                        <label>Block 3 start
                            <input name="lesson_block_3_start" value="21:00">
                        </label>
                        <label>Block 3 end
                            <input name="lesson_block_3_end" value="22:25">
                        </label>
                    </div>
                </section>

                <section class="panel" id="rooms">
                    <div class="panel-heading">
                        <h2>Rooms</h2>
                        <p>Start with one room; more room rows can use the same spec model.</p>
                    </div>
                    <div class="field-grid">
                        <label>Room name
                            <input name="room_name" value="Main Hall">
                        </label>
                        <label>Capacity
                            <input name="room_capacity" value="30">
                        </label>
                    </div>
                </section>

                <section class="panel" id="instructors">
                    <div class="panel-heading">
                        <h2>Instructors</h2>
                        <p>Define teaching eligibility, availability, and pair preferences.</p>
                    </div>
                    <div class="field-grid">
                        <label>Instructor
                            <input name="instructor_name" value="Anna">
                        </label>
                        <label>Can teach
                            <input name="instructor_can_teach" value="Lindy Hop beginner">
                        </label>
                        <label>Available days
                            <input name="instructor_available_days" value="Monday-Thursday">
                        </label>
                        <label>Available start
                            <input name="instructor_available_start" value="17:00">
                        </label>
                        <label>Available end
                            <input name="instructor_available_end" value="22:30">
                        </label>
                        <label>Prefers with
                            <input name="instructor_prefers_with" value="Ivona">
                        </label>
                        <label>Cannot teach with
                            <input name="instructor_cannot_teach_with" value="">
                        </label>
                        <label>Second instructor
                            <input name="second_instructor_name" value="Ivona">
                        </label>
                        <label>Second can teach
                            <input name="second_instructor_can_teach" value="Lindy Hop beginner">
                        </label>
                        <label>Second available days
                            <input name="second_instructor_available_days" value="Monday-Thursday">
                        </label>
                        <label>Second available start
                            <input name="second_instructor_available_start" value="17:00">
                        </label>
                        <label>Second available end
                            <input name="second_instructor_available_end" value="22:30">
                        </label>
                    </div>
                </section>

                <section class="panel" id="groups">
                    <div class="panel-heading">
                        <h2>Groups</h2>
                        <p>Define class groups, lesson duration, and teacher count.</p>
                    </div>
                    <div class="field-grid">
                        <label>Group
                            <input name="group_name" value="Lindy Hop 1">
                        </label>
                        <label>Students
                            <input name="group_students" value="24">
                        </label>
                        <label>Style
                            <input name="group_style" value="Lindy Hop">
                        </label>
                        <label>Level
                            <input name="group_level" value="beginner">
                        </label>
                        <label>Lessons per week
                            <input name="group_lessons_per_week" value="1">
                        </label>
                        <label>Duration minutes
                            <input name="group_duration_minutes" value="85">
                        </label>
                        <label>Teachers required
                            <input name="group_teachers_required" value="2">
                        </label>
                    </div>
                </section>

                <section class="panel" id="raw-spec">
                    <div class="panel-heading">
                        <h2>Raw spec</h2>
                        <p>The saved project file is this readable English text.</p>
                    </div>
                    <button type="button" data-raw-spec-toggle>Show raw spec</button>
                    <div data-raw-spec-panel hidden>
                        <textarea name="raw_spec" data-raw-spec-input>{{ form.raw_spec.value }}</textarea>
                    </div>
                </section>

                <div class="actions">
                    <button type="submit">Run scheduler</button>
                    <button type="submit" formaction="{% url 'scheduler:download_spec' %}">Download spec</button>
                </div>
            </div>
        </div>
    </form>
</main>
{% endblock %}
```

- [ ] **Step 7: Run form-first view test**

Run: `python -m pytest tests/test_views.py::test_editor_has_form_first_sections -v`

Expected: `1 passed`.

- [ ] **Step 8: Run all view tests**

Run: `python -m pytest tests/test_views.py -v`

Expected: all view tests pass.

- [ ] **Step 9: Commit**

```bash
git add scheduler/static scheduler/templates/scheduler/base.html scheduler/templates/scheduler/editor.html tests/test_views.py
git commit -m "Add form-first editor layout"
```

## Task 9: Repeatable Form Rows

**Files:**
- Modify: `scheduler/static/scheduler/app.js`
- Modify: `scheduler/templates/scheduler/editor.html`
- Modify: `tests/test_views.py`

- [ ] **Step 1: Add a view test for repeatable controls**

Append to `tests/test_views.py`:

```python
def test_editor_has_repeatable_row_controls(client):
    response = client.get(reverse("scheduler:editor"))

    assert b'data-room-rows' in response.content
    assert b'data-instructor-rows' in response.content
    assert b'data-group-rows' in response.content
    assert b'data-add-row="room"' in response.content
    assert b'data-add-row="instructor"' in response.content
    assert b'data-add-row="group"' in response.content
```

- [ ] **Step 2: Run the new repeatable-row test to verify it fails**

Run: `python -m pytest tests/test_views.py::test_editor_has_repeatable_row_controls -v`

Expected: failure because repeatable row controls do not exist.

- [ ] **Step 3: Add repeatable row support to JavaScript**

Modify `scheduler/static/scheduler/app.js` by replacing the `DOMContentLoaded` body and `buildSpecFromForm` helper with this code:

```javascript
document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector("[data-raw-spec-toggle]");
    const rawSpecPanel = document.querySelector("[data-raw-spec-panel]");
    const rawSpecInput = document.querySelector("[data-raw-spec-input]");
    const specForm = document.querySelector("[data-spec-form]");

    if (!toggle || !rawSpecPanel || !rawSpecInput || !specForm) {
        return;
    }

    toggle.addEventListener("click", () => {
        rawSpecPanel.hidden = !rawSpecPanel.hidden;
        toggle.textContent = rawSpecPanel.hidden ? "Show raw spec" : "Hide raw spec";
    });

    rawSpecInput.addEventListener("input", () => {
        rawSpecInput.dataset.dirty = "true";
    });

    document.querySelectorAll("[data-add-row]").forEach((button) => {
        button.addEventListener("click", () => addRow(button.dataset.addRow));
    });

    specForm.addEventListener("submit", () => {
        if (rawSpecInput.dataset.dirty !== "true") {
            rawSpecInput.value = buildSpecFromForm(specForm);
        }
    });
});

function addRow(kind) {
    const template = document.querySelector(`[data-${kind}-template]`);
    const target = document.querySelector(`[data-${kind}-rows]`);
    if (!template || !target) {
        return;
    }
    target.insertAdjacentHTML("beforeend", template.innerHTML);
}

function values(form, name) {
    return Array.from(form.querySelectorAll(`[name="${name}"]`)).map((field) => field.value.trim());
}

function first(form, name) {
    return values(form, name)[0] || "";
}

function buildSpecFromForm(form) {
    const lines = ["lesson blocks"];
    const days = first(form, "lesson_block_days");
    ["1", "2", "3"].forEach((index) => {
        const start = first(form, `lesson_block_${index}_start`);
        const end = first(form, `lesson_block_${index}_end`);
        if (start && end) {
            lines.push(`${days} ${start}-${end}`);
        }
    });
    lines.push("");

    const roomNames = values(form, "room_name");
    const roomCapacities = values(form, "room_capacity");
    roomNames.forEach((name, index) => {
        if (!name) {
            return;
        }
        lines.push(`room ${name}`);
        lines.push(`capacity ${roomCapacities[index]}`);
        lines.push("");
    });

    const instructorNames = values(form, "instructor_name");
    const canTeach = values(form, "instructor_can_teach");
    const availableDays = values(form, "instructor_available_days");
    const availableStarts = values(form, "instructor_available_start");
    const availableEnds = values(form, "instructor_available_end");
    const prefersWith = values(form, "instructor_prefers_with");
    const cannotTeachWith = values(form, "instructor_cannot_teach_with");
    instructorNames.forEach((name, index) => {
        if (!name) {
            return;
        }
        lines.push(`instructor ${name}`);
        lines.push(`can teach ${canTeach[index]}`);
        lines.push(`available ${availableDays[index]} ${availableStarts[index]}-${availableEnds[index]}`);
        if (prefersWith[index]) {
            lines.push(`prefers teaching with ${prefersWith[index]}`);
        }
        if (cannotTeachWith[index]) {
            lines.push(`cannot teach with ${cannotTeachWith[index]}`);
        }
        lines.push("");
    });

    const groupNames = values(form, "group_name");
    const groupStudents = values(form, "group_students");
    const groupStyles = values(form, "group_style");
    const groupLevels = values(form, "group_level");
    const groupLessons = values(form, "group_lessons_per_week");
    const groupDurations = values(form, "group_duration_minutes");
    const groupTeachers = values(form, "group_teachers_required");
    groupNames.forEach((name, index) => {
        if (!name) {
            return;
        }
        lines.push(`group ${name}`);
        lines.push(`students ${groupStudents[index]}`);
        lines.push(`style ${groupStyles[index]}`);
        lines.push(`level ${groupLevels[index]}`);
        lines.push(`needs ${groupLessons[index]} lesson per week`);
        lines.push(`duration ${groupDurations[index]} minutes`);
        lines.push(`teachers ${groupTeachers[index]}`);
        lines.push("");
    });

    return lines.join("\n");
}
```

- [ ] **Step 4: Add repeatable row markup**

Modify the `Rooms`, `Instructors`, and `Groups` sections in `scheduler/templates/scheduler/editor.html` so they use row containers and templates:

```html
<section class="panel" id="rooms">
    <div class="panel-heading">
        <h2>Rooms</h2>
        <p>Define room names and capacities.</p>
    </div>
    <div data-room-rows>
        <div class="field-grid">
            <label>Room name
                <input name="room_name" value="Main Hall">
            </label>
            <label>Capacity
                <input name="room_capacity" value="30">
            </label>
        </div>
    </div>
    <button type="button" data-add-row="room">Add room</button>
    <template data-room-template>
        <div class="field-grid">
            <label>Room name
                <input name="room_name" value="">
            </label>
            <label>Capacity
                <input name="room_capacity" value="">
            </label>
        </div>
    </template>
</section>

<section class="panel" id="instructors">
    <div class="panel-heading">
        <h2>Instructors</h2>
        <p>Define teaching eligibility, availability, and pair preferences.</p>
    </div>
    <div data-instructor-rows>
        <div class="field-grid">
            <label>Instructor
                <input name="instructor_name" value="Anna">
            </label>
            <label>Can teach
                <input name="instructor_can_teach" value="Lindy Hop beginner">
            </label>
            <label>Available days
                <input name="instructor_available_days" value="Monday-Thursday">
            </label>
            <label>Available start
                <input name="instructor_available_start" value="17:00">
            </label>
            <label>Available end
                <input name="instructor_available_end" value="22:30">
            </label>
            <label>Prefers with
                <input name="instructor_prefers_with" value="Ivona">
            </label>
            <label>Cannot teach with
                <input name="instructor_cannot_teach_with" value="">
            </label>
        </div>
        <div class="field-grid">
            <label>Instructor
                <input name="instructor_name" value="Ivona">
            </label>
            <label>Can teach
                <input name="instructor_can_teach" value="Lindy Hop beginner">
            </label>
            <label>Available days
                <input name="instructor_available_days" value="Monday-Thursday">
            </label>
            <label>Available start
                <input name="instructor_available_start" value="17:00">
            </label>
            <label>Available end
                <input name="instructor_available_end" value="22:30">
            </label>
            <label>Prefers with
                <input name="instructor_prefers_with" value="Anna">
            </label>
            <label>Cannot teach with
                <input name="instructor_cannot_teach_with" value="">
            </label>
        </div>
    </div>
    <button type="button" data-add-row="instructor">Add instructor</button>
    <template data-instructor-template>
        <div class="field-grid">
            <label>Instructor
                <input name="instructor_name" value="">
            </label>
            <label>Can teach
                <input name="instructor_can_teach" value="">
            </label>
            <label>Available days
                <input name="instructor_available_days" value="Monday-Thursday">
            </label>
            <label>Available start
                <input name="instructor_available_start" value="">
            </label>
            <label>Available end
                <input name="instructor_available_end" value="">
            </label>
            <label>Prefers with
                <input name="instructor_prefers_with" value="">
            </label>
            <label>Cannot teach with
                <input name="instructor_cannot_teach_with" value="">
            </label>
        </div>
    </template>
</section>

<section class="panel" id="groups">
    <div class="panel-heading">
        <h2>Groups</h2>
        <p>Define class groups, lesson duration, and teacher count.</p>
    </div>
    <div data-group-rows>
        <div class="field-grid">
            <label>Group
                <input name="group_name" value="Lindy Hop 1">
            </label>
            <label>Students
                <input name="group_students" value="24">
            </label>
            <label>Style
                <input name="group_style" value="Lindy Hop">
            </label>
            <label>Level
                <input name="group_level" value="beginner">
            </label>
            <label>Lessons per week
                <input name="group_lessons_per_week" value="1">
            </label>
            <label>Duration minutes
                <input name="group_duration_minutes" value="85">
            </label>
            <label>Teachers required
                <input name="group_teachers_required" value="2">
            </label>
        </div>
    </div>
    <button type="button" data-add-row="group">Add group</button>
    <template data-group-template>
        <div class="field-grid">
            <label>Group
                <input name="group_name" value="">
            </label>
            <label>Students
                <input name="group_students" value="">
            </label>
            <label>Style
                <input name="group_style" value="">
            </label>
            <label>Level
                <input name="group_level" value="">
            </label>
            <label>Lessons per week
                <input name="group_lessons_per_week" value="1">
            </label>
            <label>Duration minutes
                <input name="group_duration_minutes" value="85">
            </label>
            <label>Teachers required
                <input name="group_teachers_required" value="1">
            </label>
        </div>
    </template>
</section>
```

- [ ] **Step 5: Run repeatable-row test**

Run: `python -m pytest tests/test_views.py::test_editor_has_repeatable_row_controls -v`

Expected: `1 passed`.

- [ ] **Step 6: Run all view tests**

Run: `python -m pytest tests/test_views.py -v`

Expected: all view tests pass.

- [ ] **Step 7: Commit**

```bash
git add scheduler/static/scheduler/app.js scheduler/templates/scheduler/editor.html tests/test_views.py
git commit -m "Add repeatable schedule form rows"
```

## Task 10: Manual Browser Verification

**Files:**
- Modify only if verification finds a defect in files touched by earlier tasks.

- [ ] **Step 1: Start the Django dev server**

Run: `python manage.py runserver 127.0.0.1:8000`

Expected: server starts and prints `Starting development server at http://127.0.0.1:8000/`.

- [ ] **Step 2: Open the app**

Open: `http://127.0.0.1:8000/`

Expected:

- page loads with title `Dance Lesson Scheduler`
- left setup navigation shows `Lesson blocks`, `Rooms`, `Instructors`, `Groups`, and `Raw spec`
- raw spec textarea contains the example `Lindy Hop 1`

- [ ] **Step 3: Run the example schedule**

Click `Run scheduler`.

Expected:

- result page title says `Generated schedule`
- table includes `Lindy Hop 1`
- instructors include `Anna` and `Ivona`
- no login page appears
- no saved schedule list appears

- [ ] **Step 4: Download the spec**

Click `Download spec`.

Expected:

- browser downloads a text file named like `2026-06-25-lesson-schedule.txt`
- file content contains `group Lindy Hop 1`

- [ ] **Step 5: Run full test suite after browser fixes**

Run: `python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 6: Commit browser verification fixes if any files changed**

If no files changed, skip the commit.

If files changed:

```bash
git add scheduler tests
git commit -m "Polish scheduler browser workflow"
```

## Self-Review

Spec coverage:

- Account-free MVP: covered by Task 7 and Task 10 browser checks.
- Form-first GUI: covered by Tasks 8 and 9.
- Editable raw spec: covered by Task 7 and Task 8.
- Raw spec import and paste: covered by Task 7 through file upload and posted raw spec editing.
- Raw spec download: covered by Task 7.
- Human-readable English spec: covered by Tasks 2, 3, and 4.
- Recurring weekly schedule with explicit lesson blocks: covered by Tasks 2, 3, 5, and 6.
- 5-minute internal time grid: covered by Task 2.
- Fixed lesson duration: covered by Tasks 2, 3, 5, and 6.
- One-teacher and two-teacher lessons: covered by Tasks 2, 5, and 6.
- Hard pair bans and soft pair preferences: covered by Tasks 5 and 6.
- Validation and hints: covered by Tasks 5 and 7.
- Browser schedule view only: covered by Task 7 and Task 10.
- No database persistence of scheduling data: covered by architecture and Task 10 checks.

Placeholder scan:

- No unresolved placeholder markers.
- No unfinished task markers inside prose.
- No unnamed files.
- No steps that say only "write tests" without test content.

Type consistency:

- `ScheduleSpec`, `Room`, `Instructor`, `Group`, `LessonBlock`, `TimeRange`, `SpecError`, and `ValidationResult` are introduced before use.
- `parse_spec`, `serialize_spec`, `validate_spec`, and `solve_schedule` are introduced before view integration.
- View route names are consistent: `scheduler:editor`, `scheduler:run`, `scheduler:download_spec`, and `scheduler:import_spec`.
