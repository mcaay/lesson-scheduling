# Project audit report

Date: 2026-08-15  
Audited commit: `305a3b8` (`main`)  
Specification: `IDEA.md`

## Executive summary

The happy path works, and the existing 88 tests pass. The project nevertheless has one critical availability/security flaw, six high-severity correctness or reliability flaws, and several medium/low issues.

The project should not be considered production-safe until C-01 and H-01 through H-06 are fixed. In particular:

- a tiny valid-looking request can monopolize the only solver indefinitely;
- duplicate names let one apparent instructor fill both teacher roles and let two declared groups receive only one lesson in total;
- process restarts lose queued/running work while the UI can poll forever;
- editing the GUI after a raw-spec error can replace the user's spec with the example;
- the non-JavaScript path runs a potentially 120+ second solve inside a Gunicorn worker configured with a 60-second timeout;
- a timeout is falsely reported as proof that the constraints are infeasible.

## Scope and verification

Reviewed:

- parser, serializer, models, validation, solver, result grid, job runner, views;
- templates, JavaScript, CSS, settings, packaging, and deployment notes;
- all tests and both bundled input examples;
- rendered desktop/mobile UI and the real invalid-spec browser flow.

Commands/checks:

- `.venv/bin/pytest -q` — **88 passed**;
- `.venv/bin/python manage.py check` — **no issues**;
- production-configured `manage.py check --deploy` — only the two HSTS subdomain/preload warnings intentionally documented by the runbook;
- `.venv/bin/python -m pip check` — **no broken requirements**;
- a real Chromium session — one console error, the missing favicon described in L-02;
- end-to-end solve of `example_input.txt` — **73 seconds** on this machine.

The current tests prove many intended rules for small, clean inputs. They do not cover adversarial sizes, identifier collisions, process restarts, timeout status, or preservation of invalid raw input.

## Findings

### C-01 — Unbounded solver work enables trivial denial of service

**Severity: Critical**

Evidence:

- `scheduler/forms.py:4-5` has no raw-spec length limit.
- `scheduler/views.py:30-35` enqueues AJAX input before parsing or validation.
- `scheduler/spec_parser.py:336-344` accepts arbitrarily large Python integers.
- `scheduler/spec_validation.py:11-103` has no upper bounds on rooms, entities, lesson blocks, lessons per week, or candidate count.
- `scheduler/solver.py:82-113` materializes every group × location × room × block × instructor-choice candidate.
- `scheduler/solver.py:200-205` compares every candidate pair: O(C²) Python work and potentially O(C²) constraints.
- `scheduler/solver.py:68-69` applies the 120-second limit only to `CpSolver.Solve`; parsing, candidate generation, conflict generation, and model construction are unlimited.
- `scheduler/solve_jobs.py:21,35` has one worker thread and an unbounded submission queue.

Measured with the repository's own `example_input.txt`:

```text
34 groups, 17 instructors, 12 expanded blocks
9,534 candidates
45,443,811 candidate-pair checks
73 seconds end to end
```

A much smaller text can be worse: `rooms 1000000000` passes validation and makes `_build_candidates` iterate one billion rooms. Because there is only one solver thread in the documented one-worker deployment, this can starve every later solve. Unlimited queued jobs also consume memory and disk. This can happen accidentally or be triggered remotely on the account-free public site.

Recommended fix:

1. Parse and validate before enqueueing.
2. Enforce explicit small bounds on raw bytes, uploaded bytes, rooms per location, entity counts, blocks, lessons per group, and estimated candidates.
3. Reject work above a documented complexity budget with a configuration error.
4. Replace all-pairs conflict generation with resource/time buckets and `AddAtMostOne`/interval constraints.
5. Use a bounded queue and admission/rate control.
6. Apply a wall-clock deadline to the entire job process, not only CP-SAT.

### H-01 — Duplicate names corrupt the scheduling model

**Severity: High**

Names are used as internal identities, but uniqueness is never validated:

- `scheduler/spec_validation.py:23` creates an instructor-name set only to check references; it does not detect duplicates.
- There are no duplicate checks for groups or locations.
- `scheduler/solver.py:185-197` groups lesson requirements by `group.name`.
- `scheduler/solver.py:313-314` identifies group conflicts by name.
- `scheduler/solver.py:318-322` identifies rooms by location name plus room number.
- `scheduler/solver.py:336-339` identifies instructors by name.
- `scheduler/result_grid.py:7-16` also keys result cells by location name and room number.

Verified results:

```text
Two declared instructors named Alex (leader and follower):
validation errors = []
solved = True
assigned instructors = ('Alex', 'Alex')

Two declared groups both named Course, each needing one lesson:
validation errors = []
solved = True
scheduled lessons = 1 for 2 declared groups
```

The first result violates “two distinct instructors.” The second violates “every group receives exactly its required number.” Duplicate location names similarly collapse rooms/resources and result cells.

Recommended fix: reject duplicate instructor, group, and location names before solving. Then use stable object/index IDs internally rather than display names. Add a final solution-invariant checker before presenting any result.

### H-02 — Missing domain validation permits invalid projects and false success

**Severity: High**

Only the existence of a location and `rooms_count >= 1` are structurally checked. Missing checks include:

- at least one lesson block, instructor, and group;
- group lessons per week >= 1;
- group duration > 0 and divisible by 5;
- non-negative instructor minimum/maximum values;
- supported instructor roles;
- non-empty/unique role lists;
- self-references and contradictory pair preferences;
- integer upper bounds.

Verified results:

```text
Location-only project:
validation errors = []
solved = True, lessons = 0

Group with 0 lessons per week:
validation errors = []
solved = True, lessons = 0

Instructor roles ('leader', 'wizard') and workloads -2/-1:
validation errors = []

Group lessons per week = 10**30:
validation errors = []
solve raises TypeError inside OR-Tools
```

The asynchronous path turns the last case into the generic “Scheduling failed unexpectedly”; the synchronous path can return HTTP 500. Other invalid values are mislabeled as “combined constraints are too tight” rather than rejected before solving, contrary to `IDEA.md:48,94`.

Recommended fix: centralize domain checks in `spec_validation.py`, use sensible integer maxima, and return precise validation errors before candidate creation.

### H-03 — Background jobs are process-local, non-resumable, and can remain pending forever

**Severity: High**

`scheduler/solve_jobs.py:21-35` uses an in-process `ThreadPoolExecutor`. JSON files persist job state, but there is no durable queue, worker lease, startup recovery, or stale-pending transition.

Consequences:

- a Gunicorn restart/deploy/process crash loses every queued or running future;
- the corresponding JSON stays `pending`;
- `scheduler/static/scheduler/app.js:327-347` polls forever with no deadline;
- cleanup runs only when another job is submitted (`start_solve_job` line 25), so an idle lost job can remain indefinitely;
- with multiple Gunicorn workers, each has an independent queue and executor;
- a single long solve blocks every later job assigned to that process queue.

This does not meet the product promise that solves run as reliable background jobs.

Recommended fix: run solves in a separate bounded worker process/service backed by SQLite or a recoverable spool. Persist `queued`, `running`, heartbeat/start time, and terminal states; recover or fail abandoned jobs at startup. Give polling a server-side and client-side deadline.

### H-04 — A parse error can cause the GUI to overwrite the user's raw specification

**Severity: High**

`scheduler/editor_data.py:8-12` replaces any unparsable non-empty spec with `EXAMPLE_SPEC` when building GUI state. The rendered page still contains the user's raw text, but:

- the Parameters tab opens by default;
- `scheduler/static/scheduler/app.js:205` initializes `rawSpecDirty = false` after the page reload;
- the first GUI input/change calls `syncRawSpec` (`app.js:230-251`);
- that rebuild replaces the raw textarea with the example-derived GUI data.

Real-browser reproduction:

1. Enter `group Broken` in Raw specification.
2. Run; the server correctly shows three line errors.
3. The Parameters tab contains the full example project, not `group Broken`.
4. Change the first location.
5. Return to Raw specification: `group Broken` has been replaced by the example project plus that location change.

This is silent user-data loss in the durable project-file workflow.

Recommended fix: never substitute example data for a non-empty invalid spec. On parse errors, open the raw tab, mark it authoritative/dirty, and disable GUI-to-raw synchronization until the user explicitly resets or successfully reparses it.

### H-05 — The fallback request path runs the solver inside the web worker

**Severity: High**

`scheduler/views.py:30-36` starts a background job only when the client sends `X-Requested-With: XMLHttpRequest`. Otherwise `views.py:38-51` parses, validates, and solves synchronously.

`scheduler/static/scheduler/app.js:306-308` intentionally falls back to a normal form submission if `fetch` or `FormData` is unavailable. The same occurs when JavaScript fails to load or is disabled. The documented production service uses `--timeout 60` (`docs/multi-app-vps-runbook.md:76-79`), while the repository's realistic input took 73 seconds and CP-SAT alone may search for 120 seconds. Gunicorn can therefore kill the worker and return an error.

This also makes behavior depend on a spoofable presentation header rather than the server-side operation.

Recommended fix: every valid POST to the run endpoint should create a background job. For progressive enhancement, return a normal HTML status page for non-AJAX requests and JSON for JSON-preferring clients.

### H-06 — Timeout and model errors are falsely reported as infeasibility

**Severity: High**

`scheduler/solver.py:71-72` maps every status other than `OPTIMAL` and `FEASIBLE` to:

> No complete schedule found. The combined constraints are too tight.

That includes:

- `INFEASIBLE` — the message is appropriate;
- `UNKNOWN` — commonly means the time limit expired without a solution/proof;
- `MODEL_INVALID` — means an implementation/input-range error.

Verified by returning OR-Tools `UNKNOWN`: the app emitted the constraints-too-tight message. This tells users to change valid data when the real cause may be timeout or a broken model.

Recommended fix: branch explicitly on all statuses. Say “no schedule exists” only for `INFEASIBLE`; report a time-limit/no-proof outcome for `UNKNOWN`; log and surface an internal error for `MODEL_INVALID`. Include elapsed time and status in job metadata.

### M-01 — The advertised `maximum 0` disable switch conflicts with the default minimum

**Severity: Medium**

`IDEA.md:46` says a preferred maximum of `0` disables an instructor. The default minimum is `1`. But `scheduler/spec_validation.py:25-35` rejects minimum > maximum before treating zero as disabled. Therefore changing only the maximum from its default `3` to `0` produces a validation error; users must also discover that minimum must be changed to `0`.

The GUI help is internally contradictory: it says the maximum cannot be below the minimum and also that zero disables the instructor.

Recommended fix: make `maximum == 0` a special disabled state for which the minimum is ignored or normalized to zero. Test disabling an otherwise-default instructor by changing only the maximum.

### M-02 — Semantic validation diagnostics are incomplete and not line-based

**Severity: Medium**

Every error produced by `scheduler/spec_validation.py` uses `SpecError(None, ...)`, so raw-spec users receive no line number for duplicate/unknown names, bad workload ranges, missing roles, pair bans, or unmatched blocks. This falls short of the line-based validation design in `docs/superpowers/specs/2026-06-25-dance-scheduler-mvp-design.md:82`.

The validator also stops checking a group after several first failures (`continue` at lines 62, 74, 79, and 90), hiding independent problems. Its final message combines duration, time-window, pair, and availability failures into one vague sentence. One multi-role instructor for a two-role group is incorrectly described as “every eligible role pair is banned,” even when no pair exists.

Recommended fix: retain source-line metadata during parsing, report all independent deterministic errors, and distinguish “too few distinct instructors,” “all pairs banned,” “duration mismatch,” “window mismatch,” and “no co-available pair.”

### M-03 — The result grid displays lesson slots that do not exist

**Severity: Medium**

`scheduler/result_grid.py:4-47` takes the union of all days and the union of all time blocks, then renders their Cartesian product. If Monday defines only 18:00 and Tuesday defines only 20:00, the table also shows an empty Monday 20:00 cell and an empty Tuesday 18:00 cell. Those cells look available but were never legal solver choices.

Recommended fix: carry an `is_defined_block` flag per day/time cell and render unavailable cells distinctly, or build per-day rows without inventing combinations.

### M-04 — The raw grammar cannot represent advertised “any” names containing commas

**Severity: Medium**

`scheduler/spec_parser.py:347-348` treats every comma as a list separator. Instructor names are reused in pair lists, and group/course names are reused in `can teach` lists. A name such as `Smith, Jr` or course `Dance, Advanced` cannot round-trip or be referenced, although the GUI says names may be any non-empty value.

Recommended fix: either validate and document that commas/newlines are forbidden in referenced names, or add a quoting/escaping grammar and use it consistently in Python and JavaScript serializers.

### M-05 — Mutation endpoints do not enforce HTTP methods

**Severity: Medium**

No view uses `@require_POST`. In particular, a GET to `/run/` with the AJAX header creates a job with an empty spec and bypasses normal POST/CSRF semantics. `/import-spec/` and `/download-spec/` also accept GET and silently return example/empty content.

This is not the main denial-of-service vector—the public POST endpoint is already unbounded—but it increases accidental and automated misuse and makes the API contract unclear.

Recommended fix: add `@require_GET`/`@require_POST` as appropriate and return 405 for wrong methods.

### M-06 — Optimization priorities use incompatible, undocumented units

**Severity: Medium**

The single objective combines:

- pair preference: ±1 per one-way preference (`scheduler/solver.py:360-374`);
- workload deviation: −10 per class (`solver.py:208-240`);
- instructor gaps: −1 per five-minute slot (`solver.py:244-300`).

As a result, saving a 15-minute gap (3 points) outweighs a mutual preferred pair (2 points), while a 55-minute gap outweighs one class of workload deviation. Nothing in `IDEA.md` defines this trade-off, so small timetable changes can produce results contrary to the most visible user preferences.

Recommended fix: define an explicit priority policy. Prefer lexicographic optimization for clear priorities, or document and test calibrated weights with representative schedules.

### M-07 — Job-file cleanup can leak raw specifications and stale data

**Severity: Medium**

- `scheduler/solve_jobs.py:52` cleans only `*.json`.
- `_write_job` creates files named `.<job>.json.<uuid>.tmp` (`lines 117-123`). A crash between write and replace leaves a temp file that cleanup never matches.
- Cleanup happens only when a new job starts, not periodically.
- The temp file is written before `chmod(0o600)`, so it briefly uses process umask permissions; a crash before chmod can leave broader permissions.
- Status/result responses containing job data have no explicit `Cache-Control: no-store`.

This weakens the “no permanent scheduling records” expectation and can accumulate personally identifying staff/course data.

Recommended fix: create temp files with mode 0600 atomically, clean both final and temp patterns on startup/periodically, delete terminal jobs after a documented TTL, and send no-store headers on job status/result pages.

### M-08 — UTF-8 import is incomplete and upload validation is too weak

**Severity: Medium**

`scheduler/views.py:111-119` reads the entire upload and decodes only with `utf-8`:

- common UTF-8-with-BOM files decode successfully but leave `\ufeff` before `lesson blocks`, producing a false syntax error;
- there is no application-level byte limit before the complete file is read;
- extension/content type are not checked despite the `.txt` product contract.

The size issue contributes directly to C-01.

Recommended fix: enforce a small byte cap while streaming, decode with `utf-8-sig`, and give a precise file-type/size error.

### L-01 — Browser constraints and accessibility do not match the specification

**Severity: Low**

- Time inputs omit `step="300"`, so browsers allow off-grid minutes even though the product requires five-minute increments.
- Duration inputs omit `step="5"`.
- Custom tabs do not implement Arrow/Home/End keyboard behavior expected for `role="tablist"`.
- Help text is nested inside labels, causing the full tooltip paragraph to become part of each field's accessible name.
- `prefers-reduced-motion` merely slows the spinner (`styles.css:489-493`) instead of removing animation.

Server validation catches some of these input mistakes, but the form should prevent them and the accessible interaction should match its ARIA roles.

### L-02 — Every page load requests a missing favicon

**Severity: Low**

The real-browser audit recorded a 404 and console error for `/favicon.ico`. Add a real icon/link or an intentional data-URL icon to avoid noisy logs and console failures.

### L-03 — Production installs are not reproducible

**Severity: Low**

`pyproject.toml` contains broad dependency ranges but there is no lock/constraints file. A deployment can therefore install materially different Django/OR-Tools/Numpy/Protobuf versions from the version tested locally. The current environment is internally consistent, but a future fresh deploy is not reproducible.

Recommended fix: maintain a reviewed production lock/constraints file and update it deliberately.

### L-04 — Downloaded UTF-8 text does not declare its charset

**Severity: Low**

`scheduler/views.py:102-108` returns `Content-Type: text/plain` while specifications commonly contain non-ASCII Polish names. The bytes are UTF-8, but the response should explicitly declare `text/plain; charset=utf-8` to prevent client mis-detection.

## Test-suite gaps

The suite is clean but too example-driven. Add the following regression layers:

1. **Solution invariant checker** used by tests and optionally production: exact lesson count per group object, unique instructors within each lesson, valid roles/eligibility/availability, no resource overlap, and travel gaps.
2. **Identifier tests:** duplicate groups, instructors, and locations; self/contradictory references; names containing delimiters.
3. **Domain-boundary tests:** empty project, zero/negative/huge integers, unsupported instructor roles, invalid durations, entity/input limits.
4. **Status tests:** `INFEASIBLE`, `UNKNOWN`, `MODEL_INVALID`, internal exception, and total wall-clock timeout.
5. **Job lifecycle tests:** restart with queued/running files, abandoned jobs, bounded queue, cleanup of temp files, and polling deadline.
6. **Browser regression:** invalid raw spec must survive an error followed by a GUI edit.
7. **Performance regression:** keep `example_input.txt` as a realistic fixture with budgets for candidate count, model-build time, total time, and memory.
8. **HTTP contract tests:** method restrictions, raw/upload size limits, UTF-8 BOM, cache headers, and the non-JavaScript background flow.
9. **Result-grid tests:** different blocks on different days and explicit unavailable cells.

## Recommended repair order

1. C-01: admission limits, bounded queue, whole-job deadline, and non-quadratic conflict construction.
2. H-01/H-02: strict identities and complete domain validation; add the invariant checker.
3. H-03/H-05: durable worker lifecycle and always-background HTTP flow.
4. H-04: prevent raw-spec data loss.
5. H-06/M-01/M-02: accurate solver states and validation messages.
6. Address result fidelity, grammar, job-file lifecycle, imports, and frontend/accessibility issues.

## What is already correct

For unique, reasonably sized, valid inputs, the implementation correctly enforces the main hard constraints tested in the suite: exact lesson counts, lesson-block duration, group windows, instructor role/eligibility/availability, room/group/instructor overlap, distinct instructor objects, pair bans, and the 60-minute cross-location gap. The parser reports syntax errors cleanly, the spec serializer round-trips valid data, production settings fail closed when the secret or allowed hosts are missing, static assets are fingerprinted in production, and output is template-escaped.
