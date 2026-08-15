# Dance Lesson Scheduler

A Django application that generates a recurring weekly timetable for dance schools with Google OR-Tools CP-SAT.

## Product

- No accounts or permanent scheduling records.
- Users edit parameters in the GUI or edit the equivalent raw text specification.
- The parsed raw specification is the solver's only input and the durable project file.
- Users can import, download, and reopen UTF-8 `.txt` specifications.
- Results are displayed as a weekly room timetable.
- Solves run as background jobs; the browser polls their status with short requests.

The MVP excludes dates, holidays, cancellations, substitutions, one-off events, calendar export, and multi-school features.

## Stack

- Python, Django, and sqlite
- Django templates, plain JavaScript, and CSS; no React
- Google OR-Tools CP-SAT
- Function-based views and local parser, serializer, validator, and solver modules

## Scheduling Model

Users define:

- lesson blocks: the only times at which lessons may occur;
- locations and their number of interchangeable rooms;
- instructors, roles, course eligibility, availability, workload preferences, and pair preferences;
- groups, weekly lesson count, duration, required teacher roles, and optional time windows.

Times use `HH:MM` on a 5-minute grid. A day may be singular (`Tuesday`) or an inclusive range (`Monday-Thursday`). The solver never invents a start time outside the lesson blocks.

### Hard Constraints

- Every group receives exactly its required number of weekly lessons.
- A lesson block must equal the group's duration.
- A group time window, when present, must fully contain the lesson block.
- Every instructor must be eligible, have the required role, and be available for the full block.
- A room, group, or instructor cannot occupy overlapping lessons.
- Two-role lessons use two distinct instructors and respect pair bans.
- An instructor needs at least 60 minutes between lessons at different locations.

### Optimization

Among valid schedules, prefer requested instructor pairs, avoid discouraged pairs, minimize same-day instructor gaps, and keep workloads near their preferred weekly minimum and maximum. A preferred maximum of `0` disables an instructor without removing them from the specification, which is useful for a trimester-long absence.

The solver may search for up to 120 seconds. If no complete schedule exists, report that the combined constraints are too tight. Syntax and independently detectable configuration errors should be reported before solving.

## Raw Specification

```text
lesson blocks
Monday-Thursday 18:00-19:25
Monday-Thursday 19:30-20:55

location Main Studio
rooms 2

instructor Anna
roles follower
prefers minimum 1 class per week
prefers maximum 3 classes per week
can teach Lindy Hop beginner
available Tuesday 18:00-21:00
available Thursday 18:00-21:00
prefers teaching with Jan

instructor Jan
roles leader
can teach Lindy Hop beginner
available Monday-Thursday 17:00-22:30

group Lindy Hop beginner #1
needs 1 lesson per week
duration 85 minutes
teacher roles leader, follower
time window Tuesday 18:00-21:00
time window Thursday 18:00-21:00
```

Rules:

- Repeated `available` lines are alternatives (OR).
- Repeated `time window` lines are alternatives (OR).
- Without a `time window`, a group may use any otherwise valid lesson block.
- A window equal to one lesson block fixes the group to that block.
- Comma-separated GUI availability and time-window values become repeated raw-spec lines.
- A group suffix such as `#1` identifies an instance; instructor eligibility is matched against the name without that suffix.
- Supported roles are `leader`, `follower`, and `solo`; a group requires one or two roles.
- Instructor defaults are roles `leader, follower`, preferred minimum `1`, and preferred maximum `3`.
- Names referenced by pair preferences must identify declared instructors.

Invalid syntax is reported by line. The solver runs only after parsing and validation succeed.

## Engineering Boundaries

- Keep scheduling data in submitted form/spec data, not business tables.
- Keep templates simple and computation in Python modules.
- Prefer direct, readable code and focused parser, serializer, validation, solver, and GUI tests.
- Add only constraints required by real dance-school workflows.
