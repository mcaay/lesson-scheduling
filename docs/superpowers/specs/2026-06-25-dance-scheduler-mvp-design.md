# Dance Scheduler MVP Design

## Summary

Build a Django web app that lets a dance school owner generate a recurring weekly lesson schedule without creating an account. The user enters scheduling data through forms, can toggle into an editable raw text spec, runs the CP-SAT solver, views the generated schedule, and saves work by downloading the raw spec as a text file.

The MVP deliberately avoids accounts and database persistence of scheduling data. The durable artifact is the human-readable English spec.

## Product Decisions

- The app is specifically for dance schools, not general scheduling.
- Users do not create accounts in the MVP.
- The GUI is the primary working surface.
- The raw spec is visible and editable through a toggle.
- The raw spec is English-only.
- The raw spec is human-readable, not XML and not a database dump.
- Users can import or paste a saved spec to continue working.
- Users can download the current spec as a `.txt` file.
- Generated schedules are viewable in the browser only in the MVP.
- The schedule is recurring weekly only.
- Users explicitly define lesson blocks.
- Times use `HH:MM` and normalize internally to a 5-minute grid.
- Lesson requirements have fixed durations chosen by the user.
- Two-teacher lessons support hard pair bans and soft pair preferences.

## User Workflow

1. The user opens the app.
2. The user fills structured forms for lesson blocks, rooms, instructors, groups, requirements, availability, and preferences.
3. The app generates a raw spec from the form state.
4. The user can toggle "Raw spec" to inspect or edit the text directly.
5. Raw spec edits are parsed back into form state.
6. The user validates the input.
7. The user runs the scheduler.
8. The app displays the weekly schedule or useful errors.
9. The user tweaks forms or raw spec and runs again.
10. The user downloads the raw spec to save the work.
11. Later, the user imports or pastes the saved spec to continue.

## Scope

Included in the MVP:

- recurring weekly schedule generation
- explicit lesson blocks
- room capacities
- instructors
- instructor availability
- instructor teaching eligibility
- dance styles and skill levels
- groups and group sizes
- lesson requirements
- one-teacher and two-teacher lessons
- hard instructor-pair bans
- soft instructor-pair preferences
- spec validation and conflict hints
- raw spec import, paste, edit, and download
- browser schedule view

Excluded from the MVP:

- user accounts
- login
- school accounts
- multi-school tenancy
- saving specs or schedules to the database
- dates, holidays, cancellations, substitutions, and one-off events
- exporting generated schedules to a file format
- calendar integrations
- React
- enterprise features

## Raw Spec

The raw spec is the saved project format. It should be readable enough for a non-programmer to understand and lightly edit, while strict enough for reliable parsing.

The app must support two transformations:

- serialize form state into raw spec text
- parse raw spec text back into form state

Syntax and validation errors should be line-based. If the raw spec cannot be parsed or validated, the solver should not run.

Example direction:

```text
lesson blocks
Monday-Thursday 18:00-19:25
Monday-Thursday 19:30-20:55
Monday-Thursday 21:00-22:25

room Main Hall

instructor Anna
can teach Lindy Hop beginner, Solo Jazz beginner
available Monday-Thursday 17:00-22:30
prefers teaching with Ivona
cannot teach with Ana

group Lindy Hop 1
needs 1 lesson per week
duration 85 minutes
teacher roles leader, follower
```

## Scheduling Model

The solver assigns required lessons to user-defined lesson blocks. It should not invent arbitrary start times outside those blocks.

All times in the spec use `HH:MM`. Internally, parsing converts them to 5-minute slot indexes. This supports schools with precise blocks such as `18:00-19:25`, `19:30-20:55`, and `21:00-22:25`.

Each lesson requirement has a fixed user-chosen duration. Validation should detect obvious mismatches between requirement durations and available lesson blocks.

## Constraints

Hard constraints:

- every required lesson must be scheduled
- no room conflicts
- no instructor conflicts
- no group conflicts
- lessons must use explicit lesson blocks
- assigned instructors must be eligible for the group's named course
- assigned instructors must be available for the selected lesson block
- two-teacher lessons must receive two instructors
- hard instructor-pair bans must be respected

Soft preferences:

- reward preferred instructor pairs
- penalize disliked instructor pairs where they are not hard-banned
- avoid very late slots when reasonable
- batch instructor lessons when reasonable
- reduce instructor gaps when reasonable
- prefer evening hours for adult groups when reasonable

The first solver should stay understandable. If a soft preference creates disproportionate complexity, keep it out of the first implementation and document the limitation.

## Validation And Failure Hints

Validation should run before solving and catch deterministic problems:

- raw spec syntax errors
- unknown names
- invalid days or times
- invalid lesson block ranges
- required lessons with no eligible instructor
- required lessons with no available block
- two-teacher requirements with too few eligible instructors
- pair bans that make a requirement impossible

If validation passes but the solver finds no complete schedule, the app should say that the inputs are individually valid but the combined constraints are too tight. It should suggest likely fixes such as adding lesson blocks, relaxing instructor availability, adding rooms, or loosening pair bans.

## Architecture

Use a small Django app with Django templates and function-based views.

Core units:

- `spec` module: parser, serializer, and plain Python data objects
- `validation` module: deterministic checks and user-facing errors
- `solver` module: OR-Tools CP-SAT model and result extraction
- `views` module: form/spec editing, validation, run action, and result display
- templates: simple form pages, raw spec toggle, and weekly schedule view
- tests: parser, serializer, validation, and solver fixtures

The Django sqlite database remains available for normal Django operation, but the MVP should not persist user scheduling data in business tables.

## Data Flow

```text
Forms
  -> form state
  -> raw spec serializer
  -> raw spec text
  -> parser
  -> validation
  -> solver
  -> schedule result
  -> browser view
```

When the user edits raw spec directly:

```text
Raw spec text
  -> parser
  -> validation
  -> form state
```

## Testing

The MVP should have focused tests for:

- parsing valid spec examples
- rejecting invalid syntax with line-based errors
- serializing form state into stable raw spec text
- parsing serialized output back into equivalent state
- validation failures for impossible inputs
- a small solvable fixture
- a small unsolvable fixture
- two-teacher pair bans
- two-teacher pair preferences

## Implementation Sequence

1. Define the first raw spec grammar and example fixtures.
2. Build parser and serializer.
3. Add validation checks and line-based errors.
4. Build a minimal form/spec editing page.
5. Build raw spec download and import/paste.
6. Build the first CP-SAT solver for valid schedules.
7. Add the weekly schedule result view.
8. Expand form-based editing around the same spec model.
9. Add pair bans and pair preferences.
10. Improve failure hints.

## Open Product Boundary

Future versions may add accounts, saved specs, saved schedules, exports, calendar integrations, and school-level persistence. Those are intentionally outside the MVP.
