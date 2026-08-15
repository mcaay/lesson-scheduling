import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from scheduler.examples import EXAMPLE_SPEC
from scheduler.spec_limits import MAX_RAW_SPEC_BYTES


def test_editor_shows_example_spec(client):
    response = client.get(reverse("scheduler:editor"))

    assert response.status_code == 200
    assert b"Raw spec" in response.content
    assert b"LH1" in response.content
    assert b"LH2" in response.content
    assert b"LH3" in response.content
    assert b"Charleston 1" in response.content
    assert b"Balboa 1" in response.content
    assert b"Solo Jazz" in response.content
    assert b'value="Swing Studio"' in response.content
    assert b'value="Jazz Loft"' in response.content
    assert b'name="location_rooms_count" aria-label="Number of rooms" min="1" value="2"' in response.content
    assert b'value="Ania"' in response.content
    assert b'value="Mateusz"' in response.content
    assert b'value="Marysia"' in response.content
    assert 'value="Rafał"'.encode("utf-8") in response.content
    assert b"<strong>Ania</strong>" not in response.content
    assert b"<strong>New instructor</strong>" not in response.content
    assert b'name="room_capacity"' not in response.content
    assert b'name="instructor_preferred_min_classes" aria-label="Preferred min classes" min="0" value="1"' in response.content
    assert b'name="instructor_preferred_max_classes" aria-label="Preferred max classes" min="0" value="3"' in response.content


def test_editor_has_form_first_sections(client):
    response = client.get(reverse("scheduler:editor"))

    assert response.status_code == 200
    assert b"Lesson blocks" in response.content
    assert b"Locations" in response.content
    assert b"Instructors" in response.content
    assert b"Groups" in response.content
    assert b"Raw specification" in response.content
    assert b"data-editor-tab=\"parameters\"" in response.content
    assert b"data-editor-tab=\"raw-spec\"" in response.content
    assert b"id=\"raw-spec-panel\"" in response.content
    assert b"data-tab-panel=\"raw-spec\" hidden" in response.content
    assert b"data-raw-spec-toggle" not in response.content
    assert b"class=\"upload-form\"" not in response.content
    assert b"Teacher roles needed" in response.content
    assert b'name="lesson_block_days"' in response.content
    assert b'name="location_name"' in response.content
    assert b'name="location_rooms_count"' in response.content
    assert b'name="room_name"' not in response.content
    assert b'name="instructor_name"' in response.content
    assert b'name="group_name"' in response.content
    assert b'name="group_students"' not in response.content
    assert b'name="instructor_roles"' in response.content
    assert b'name="instructor_preferred_min_classes"' in response.content
    assert b'name="instructor_preferred_max_classes"' in response.content
    assert b'name="instructor_avoids_with"' in response.content
    assert b'name="instructor_cannot_teach_with"' in response.content
    assert b'name="group_teacher_roles"' in response.content
    assert b'name="group_style"' not in response.content
    assert b'name="group_level"' not in response.content
    assert b'type="time" name="lesson_block_start" aria-label="Starts" step="300"' in response.content
    assert b'name="group_duration_minutes" aria-label="Duration minutes" min="5" step="5"' in response.content
    assert b'aria-labelledby="parameters-tab"' in response.content
    assert b'aria-labelledby="raw-spec-tab"' in response.content
    assert b"scheduler/favicon.svg" in response.content


def test_editor_has_repeatable_row_controls(client):
    response = client.get(reverse("scheduler:editor"))

    assert response.status_code == 200
    assert b"data-location-rows" in response.content
    assert b"data-instructor-rows" in response.content
    assert b"data-group-rows" in response.content
    assert b"data-lesson-block-rows" in response.content
    assert b'data-add-row="location"' in response.content
    assert b'data-add-row="instructor"' in response.content
    assert b'data-add-row="group"' in response.content
    assert b'data-add-row="lesson-block"' in response.content
    assert b"data-remove-row" in response.content
    assert b'aria-label="Remove"' in response.content
    assert b"remove-icon" in response.content
    assert b">Remove</button>" not in response.content


def test_editor_explains_every_input_with_tooltips(client):
    response = client.get(reverse("scheduler:editor"))

    assert response.status_code == 200
    fields = (
        "lesson_block_days",
        "lesson_block_start",
        "lesson_block_end",
        "location_name",
        "location_rooms_count",
        "instructor_name",
        "instructor_roles",
        "instructor_preferred_min_classes",
        "instructor_preferred_max_classes",
        "instructor_can_teach",
        "instructor_available",
        "instructor_prefers_with",
        "instructor_avoids_with",
        "instructor_cannot_teach_with",
        "group_name",
        "group_lessons_per_week",
        "group_duration_minutes",
        "group_teacher_roles",
        "group_time_windows",
        "spec_file",
        "raw_spec",
    )
    for field in fields:
        assert f'data-help-for="{field}"'.encode() in response.content

    tooltip_count = response.content.count(b'class="field-tooltip"')
    assert tooltip_count > len(fields)
    assert (
        response.content.count(
            b'<span class="field-tooltip-example-label">E.g.</span>'
        )
        == tooltip_count
    )
    assert response.content.count(b"<hr>") == tooltip_count
    assert b"<code>Tuesday</code>" in response.content
    assert b"<code>Monday-Thursday</code>" in response.content
    assert b"Default: leader, follower" not in response.content
    assert b"The roles this instructor can teach" in response.content
    assert b"Enter 0 here to disable the instructor" in response.content
    assert b"Lesson blocks are the possible weekly slots" in response.content
    assert b"The room size handling is not covered by this website" in response.content
    assert b"some levels might have multiple parallel groups" in response.content
    assert b"Here in the teacher setup only write Lindy Hop beginner" in response.content
    assert b"Time constraints for this group" in response.content
    assert b"this group must occur somewhere within any of those time windows" in response.content
    assert b"Optional times when this group can have a lesson" not in response.content
    assert b'tabindex="0"' in response.content


def test_run_schedule_shows_result(client, monkeypatch, settings, tmp_path):
    class ImmediateExecutor:
        def submit(self, function, *args):
            function(*args)

    settings.SOLVER_JOB_DIRECTORY = tmp_path
    monkeypatch.setattr("scheduler.solve_jobs._executor", ImmediateExecutor())
    response = client.post(
        reverse("scheduler:run"),
        {"raw_spec": EXAMPLE_SPEC},
        follow=True,
    )

    assert response.status_code == 200
    assert b"Generated schedule" in response.content
    assert b"schedule-grid" in response.content
    assert b"<table" in response.content
    assert b"schedule-table" in response.content
    assert b"schedule-day-heading" in response.content
    assert b"schedule-room-heading" in response.content
    assert b"schedule-time" in response.content
    assert b"lesson-card" in response.content
    assert b"LH1" in response.content
    assert b"Solo Jazz" in response.content
    assert b"Swing Studio" in response.content
    assert b"Taught by" not in response.content
    assert b"<small>" not in response.content
    assert b"Save work" in response.content
    assert b"Download spec" not in response.content
    assert b"Back to editor" in response.content
    assert b"Start over" not in response.content


def test_run_schedule_shows_validation_errors(client, settings, tmp_path):
    settings.SOLVER_JOB_DIRECTORY = tmp_path
    response = client.post(
        reverse("scheduler:run"),
        {
            "raw_spec": (
                "location Main Hall\nrooms 1\n\n"
                "group Lindy Hop 1\nneeds 1 lesson per week"
            )
        },
        follow=True,
    )

    assert response.status_code == 200
    assert b"Group Lindy Hop 1 is missing duration" in response.content


def test_download_spec_returns_text_file(client):
    response = client.post(
        reverse("scheduler:download_spec"), {"raw_spec": EXAMPLE_SPEC}
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    assert response["Content-Disposition"].startswith("attachment;")
    assert b"group LH1" in response.content
    assert b"group Solo Jazz" in response.content


def test_editor_save_work_button_downloads_spec(client):
    response = client.get(reverse("scheduler:editor"))

    assert response.status_code == 200
    assert b"Save work" in response.content
    assert b"Download spec" not in response.content


def test_editor_shows_solver_loading_state(client):
    response = client.get(reverse("scheduler:editor"))

    assert response.status_code == 200
    assert b"data-solver-form" in response.content
    assert b"data-run-scheduler" in response.content
    assert b"data-solver-loading" in response.content
    assert b"Large schedules can take several minutes." in response.content


def test_ajax_solver_returns_job_and_renders_completed_result(
    client,
    monkeypatch,
    settings,
    tmp_path,
):
    class ImmediateExecutor:
        def submit(self, function, *args):
            function(*args)

    settings.SOLVER_JOB_DIRECTORY = tmp_path
    monkeypatch.setattr("scheduler.solve_jobs._executor", ImmediateExecutor())

    response = client.post(
        reverse("scheduler:run"),
        {"raw_spec": EXAMPLE_SPEC},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 202
    status_response = client.get(response.json()["status_url"])
    assert status_response.json()["status"] == "complete"
    assert status_response["Cache-Control"] == "no-store"

    result_response = client.get(status_response.json()["result_url"])
    assert result_response.status_code == 200
    assert result_response["Cache-Control"] == "no-store"
    assert b"Generated schedule" in result_response.content
    assert b"LH1" in result_response.content


def test_ajax_solver_returns_validation_errors_through_result_page(
    client,
    monkeypatch,
    settings,
    tmp_path,
):
    class ImmediateExecutor:
        def submit(self, function, *args):
            function(*args)

    settings.SOLVER_JOB_DIRECTORY = tmp_path
    monkeypatch.setattr("scheduler.solve_jobs._executor", ImmediateExecutor())

    response = client.post(
        reverse("scheduler:run"),
        {"raw_spec": "group Broken"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    status_response = client.get(response.json()["status_url"])

    assert status_response.json()["status"] == "invalid"
    result_response = client.get(status_response.json()["result_url"])
    assert b"Group Broken is missing lessons per week" in result_response.content


def test_import_spec_file_loads_editor(client):
    upload = SimpleUploadedFile(
        "schedule.txt", EXAMPLE_SPEC.encode("utf-8"), content_type="text/plain"
    )

    response = client.post(reverse("scheduler:import_spec"), {"spec_file": upload})

    assert response.status_code == 200
    assert b"group LH1" in response.content
    assert b"group Solo Jazz" in response.content


def test_import_spec_rejects_non_utf8_upload(client):
    upload = SimpleUploadedFile(
        "schedule.txt", b"\xff", content_type="text/plain"
    )

    response = client.post(reverse("scheduler:import_spec"), {"spec_file": upload})

    assert response.status_code == 400
    assert b"UTF-8 text file" in response.content


def test_editor_post_preserves_raw_spec_from_result(client):
    raw_spec = EXAMPLE_SPEC.replace("group LH1", "group Balboa 1")

    response = client.post(reverse("scheduler:editor"), {"raw_spec": raw_spec})

    assert response.status_code == 200
    assert b"Balboa 1" in response.content


def test_editor_post_rehydrates_gui_from_raw_spec(client):
    raw_spec = EXAMPLE_SPEC.replace(
        "location Jazz Loft",
        "location Blue Studio",
    )

    response = client.post(reverse("scheduler:editor"), {"raw_spec": raw_spec})

    assert response.status_code == 200
    assert b'value="Blue Studio"' in response.content
    assert b'name="room_capacity"' not in response.content
    assert b'value="Monday-Thursday"' in response.content


def test_invalid_raw_spec_stays_authoritative_in_the_raw_tab(
    client,
    settings,
    tmp_path,
):
    settings.SOLVER_JOB_DIRECTORY = tmp_path

    response = client.post(
        reverse("scheduler:run"),
        {"raw_spec": "group Broken"},
        follow=True,
    )

    assert b"group Broken" in response.content
    assert b'data-raw-spec-authoritative' in response.content
    assert b'id="raw-spec-tab"' in response.content
    assert b'id="raw-spec-panel"' in response.content
    assert b'value="Swing Studio"' not in response.content


def test_plain_form_submission_returns_a_refreshing_job_page(
    client,
    monkeypatch,
    settings,
    tmp_path,
):
    class HoldingExecutor:
        def submit(self, _function, *_args):
            pass

    settings.SOLVER_JOB_DIRECTORY = tmp_path
    monkeypatch.setattr("scheduler.solve_jobs._executor", HoldingExecutor())

    response = client.post(
        reverse("scheduler:run"),
        {"raw_spec": EXAMPLE_SPEC},
        follow=True,
    )

    assert b"Finding the best schedule" in response.content
    assert b'http-equiv="refresh"' in response.content
    assert response["Cache-Control"] == "no-store"


def test_raw_spec_has_an_application_byte_limit(client):
    response = client.post(
        reverse("scheduler:run"),
        {"raw_spec": "x" * (MAX_RAW_SPEC_BYTES + 1)},
    )

    assert response.status_code == 400
    assert b"cannot exceed" in response.content


def test_import_accepts_utf8_bom(client):
    upload = SimpleUploadedFile(
        "schedule.txt",
        b"\xef\xbb\xbf" + EXAMPLE_SPEC.encode("utf-8"),
        content_type="text/plain",
    )

    response = client.post(reverse("scheduler:import_spec"), {"spec_file": upload})

    assert response.status_code == 200
    assert b"\xef\xbb\xbf" not in response.content
    assert b"group LH1" in response.content


def test_import_rejects_wrong_extension(client):
    upload = SimpleUploadedFile(
        "schedule.pdf",
        EXAMPLE_SPEC.encode("utf-8"),
        content_type="application/pdf",
    )

    response = client.post(reverse("scheduler:import_spec"), {"spec_file": upload})

    assert response.status_code == 400
    assert b".txt" in response.content


@pytest.mark.parametrize(
    "url_name",
    ("run", "download_spec", "import_spec"),
)
def test_post_only_endpoints_reject_get(client, url_name):
    assert client.get(reverse(f"scheduler:{url_name}")).status_code == 405


@pytest.mark.parametrize(
    "url_name",
    ("solve_job_status", "solve_job_result"),
)
def test_job_read_endpoints_reject_post(client, url_name):
    assert (
        client.post(reverse(f"scheduler:{url_name}", args=[uuid.uuid4()])).status_code
        == 405
    )
