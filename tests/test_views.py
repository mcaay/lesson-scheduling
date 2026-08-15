from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from scheduler.examples import EXAMPLE_SPEC


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
    assert b'name="location_rooms_count" min="1" value="2"' in response.content
    assert b'value="Ania"' in response.content
    assert b'value="Mateusz"' in response.content
    assert b'value="Marysia"' in response.content
    assert 'value="Rafał"'.encode("utf-8") in response.content
    assert b"<strong>Ania</strong>" not in response.content
    assert b"<strong>New instructor</strong>" not in response.content
    assert b'name="room_capacity"' not in response.content
    assert b'name="instructor_preferred_min_classes" min="0" value="1"' in response.content
    assert b'name="instructor_preferred_max_classes" min="0" value="3"' in response.content


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


def test_run_schedule_shows_result(client):
    response = client.post(reverse("scheduler:run"), {"raw_spec": EXAMPLE_SPEC})

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


def test_run_schedule_shows_validation_errors(client):
    response = client.post(
        reverse("scheduler:run"),
        {
            "raw_spec": (
                "location Main Hall\nrooms 1\n\n"
                "group Lindy Hop 1\nneeds 1 lesson per week"
            )
        },
    )

    assert response.status_code == 200
    assert b"Group Lindy Hop 1 is missing duration" in response.content


def test_download_spec_returns_text_file(client):
    response = client.post(
        reverse("scheduler:download_spec"), {"raw_spec": EXAMPLE_SPEC}
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "text/plain"
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

    result_response = client.get(status_response.json()["result_url"])
    assert result_response.status_code == 200
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

    assert response.status_code == 200
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
