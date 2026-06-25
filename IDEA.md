# Dance Lesson Scheduler

Build a Python/Django web application for automatically scheduling dance classes for dance schools.

This is not a general scheduling system for regular schools, universities, or training companies. The product is specifically and exclusively for dance schools.

## Core Idea

The application lets a dance school owner describe a recurring weekly dance-class schedule problem, then generates the best valid weekly schedule using Google OR-Tools CP-SAT.

The MVP is account-free and file-based:

- the user does not need to create an account
- the user enters scheduling data through a clean GUI
- the app generates a human-readable English raw text specification from the GUI
- the user can toggle to a "Raw spec" view and edit that text directly
- the solver runs from the parsed specification
- the generated schedule is viewable in the browser
- to save work, the user downloads or copies the raw spec as a `.txt` file
- later, the user can import or paste that spec back into the app and continue working

The raw spec is the durable project file. The database must not be used to save user scheduling data in the MVP.

## Stack

- Python
- Django
- sqlite as the default Django database
- Google OR-Tools CP-SAT
- Django templates at the start, no React
- Tailwind, simple CSS, and plain JavaScript where needed
- suitable for later deployment on a VPS

## MVP Scope

The MVP schedules a recurring weekly timetable only.

Included:

- explicit lesson blocks, for example `Monday-Thursday 18:00-19:25`
- rooms and room capacities
- instructors
- instructor availability
- dance styles and skill levels
- groups and group sizes
- lesson requirements
- one-teacher and two-teacher lessons
- instructor eligibility by style/level
- hard instructor-pair bans
- soft instructor-pair preferences
- useful validation and conflict hints
- browser view of the generated schedule
- raw spec download
- raw spec import or paste

Excluded:

- user accounts
- login
- school accounts
- multi-school tenancy
- saving specs or schedules to the application database
- calendar dates
- holidays
- cancellations
- substitutions
- one-off events
- exporting generated schedules to another file format
- React
- enterprise features

## User Workflow

1. Open the app.
2. Enter scheduling data in structured forms.
3. Optionally toggle "Raw spec" and edit the generated text directly.
4. Validate the input.
5. Run the scheduler.
6. View the generated weekly schedule.
7. Adjust forms or raw spec.
8. Run again.
9. Download or copy the raw spec to save the work.
10. Later, import or paste the saved spec to continue.

## Raw Spec

The raw spec should be human-readable English text, not XML and not a database dump.

The format should be strict enough to parse reliably, but simple enough for a dance school owner to read and lightly edit.

Example direction:

```text
lesson blocks
Monday-Thursday 18:00-19:25
Monday-Thursday 19:30-20:55
Monday-Thursday 21:00-22:25

room Main Hall
capacity 30

instructor Anna
can teach Lindy Hop beginner, Solo Jazz beginner
available Monday-Thursday 17:00-22:30
prefers teaching with Ivona
cannot teach with Ana

group Lindy Hop 1
students 24
style Lindy Hop
level beginner
needs 1 lesson per week
duration 85 minutes
teachers 2
```

The app should support both directions:

- forms generate the raw spec
- raw spec edits are parsed back into form state

If the raw spec has syntax or validation errors, the app should show line-based errors and should not run the solver until the input is fixed.

## Scheduling Model

The user defines explicit lesson blocks. The solver assigns required lessons to those blocks.

All times use `HH:MM` in the spec and are normalized internally to a 5-minute grid.

Each lesson requirement has a fixed duration chosen by the user. Typical schools may use blocks such as:

- 18:00-19:25
- 19:30-20:55
- 21:00-22:25

The solver should not invent arbitrary lesson starts outside the defined lesson blocks.

## Domain Examples

- the `Lindy Hop 1` group needs 1 lesson per week
- instructor Anna can teach `Lindy Hop beginner`
- Anna is available Monday-Thursday from 17:00 to 22:30
- Room A has capacity for 30 people
- the group has 24 people
- one room cannot host two classes at the same time
- one instructor cannot teach two classes at the same time
- one group cannot have two classes at the same time
- a pair dance can require two teachers
- a solo dance can require one teacher
- some instructor pairs are banned
- some instructor pairs are preferred

## Hard Constraints

- every required lesson must be scheduled
- no room conflicts
- no instructor conflicts
- no group conflicts
- classes must use an explicit lesson block
- the block must fit instructor availability
- the room must have enough capacity
- assigned instructors must be eligible to teach the lesson's style and level
- lessons requiring two teachers must receive two instructors
- hard instructor-pair bans must be respected

## Soft Preferences

Soft preferences improve the schedule but should not make the MVP overcomplicated.

Important preferences:

- respect positive instructor-pair preferences
- avoid negative instructor-pair preferences
- avoid very late slots when reasonable
- batch instructor lessons when reasonable
- reduce instructor gaps when reasonable
- prefer evening hours for adult groups when reasonable

If a preference is difficult, keep the solver simple and document the limitation instead of overbuilding the MVP.

## Validation And Hints

Before solving, the app should catch clear problems:

- invalid raw spec syntax
- unknown names
- invalid times
- lesson block duration mismatches
- groups too large for every room
- required lessons with no eligible instructor
- required lessons with no available lesson block
- two-teacher requirements with too few eligible instructors
- pair bans that make a lesson impossible

If validation passes but CP-SAT finds no solution, the app should explain that the individual inputs are valid but the combined constraints are too tight. It should suggest practical next moves, such as adding lesson blocks, relaxing availability, adding rooms, or loosening hard pair bans.

## Application Structure Direction

Keep the backend simple and Django-native:

- function-based views only
- Django templates
- plain forms and small JavaScript helpers
- no React
- no microservices
- local parser/serializer code for the raw spec
- local solver module wrapping OR-Tools
- tests around parser, validation, serializer, and solver behavior

The Django database exists because this is a Django project using sqlite, but MVP scheduling data should live in submitted form/spec data, not persisted business tables.

## Implementation Direction

Do not code everything at once.

First prepare:

1. the raw spec grammar and examples
2. parser and serializer
3. validation layer
4. simple GUI form flow
5. raw spec toggle and import/download
6. first CP-SAT solver that finds a valid schedule
7. schedule result view
8. useful failure hints
9. focused tests

Then iterate from the simplest usable form-first scheduling loop:

1. enter a small schedule through forms
2. inspect the generated raw spec
3. validate it
4. solve it
5. view the weekly schedule
6. tweak forms or raw spec
7. run again
8. download the spec

## Important Principles

- keep the code simple and readable
- keep the saved artifact human-readable
- keep the MVP account-free
- do not save user scheduling data in the database
- do not introduce React at the start
- do not design the system for enterprises
- solver input should come from the parsed raw spec
- if a constraint is difficult, simplify it instead of overcomplicating the MVP

Start with the design and implementation plan, not with product code.
