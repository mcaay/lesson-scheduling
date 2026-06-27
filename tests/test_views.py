from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from scheduler.examples import EXAMPLE_SPEC


def test_editor_shows_example_spec(client):
    response = client.get(reverse("scheduler:editor"))

    assert response.status_code == 200
    assert b"Raw spec" in response.content
    assert b"Lindy Hop 1" in response.content


def test_editor_has_form_first_sections(client):
    response = client.get(reverse("scheduler:editor"))

    assert response.status_code == 200
    assert b"Lesson blocks" in response.content
    assert b"Rooms" in response.content
    assert b"Instructors" in response.content
    assert b"Groups" in response.content
    assert b"Raw spec" in response.content
    assert b'name="lesson_block_days"' in response.content
    assert b'name="room_name"' in response.content
    assert b'name="instructor_name"' in response.content
    assert b'name="group_name"' in response.content


def test_editor_has_repeatable_row_controls(client):
    response = client.get(reverse("scheduler:editor"))

    assert response.status_code == 200
    assert b"data-room-rows" in response.content
    assert b"data-instructor-rows" in response.content
    assert b"data-group-rows" in response.content
    assert b'data-add-row="room"' in response.content
    assert b'data-add-row="instructor"' in response.content
    assert b'data-add-row="group"' in response.content


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
    response = client.post(
        reverse("scheduler:download_spec"), {"raw_spec": EXAMPLE_SPEC}
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "text/plain"
    assert response["Content-Disposition"].startswith("attachment;")
    assert b"group Lindy Hop 1" in response.content


def test_import_spec_file_loads_editor(client):
    upload = SimpleUploadedFile(
        "schedule.txt", EXAMPLE_SPEC.encode("utf-8"), content_type="text/plain"
    )

    response = client.post(reverse("scheduler:import_spec"), {"spec_file": upload})

    assert response.status_code == 200
    assert b"group Lindy Hop 1" in response.content


def test_import_spec_rejects_non_utf8_upload(client):
    upload = SimpleUploadedFile(
        "schedule.txt", b"\xff", content_type="text/plain"
    )

    response = client.post(reverse("scheduler:import_spec"), {"spec_file": upload})

    assert response.status_code == 200
    assert b"UTF-8 text file" in response.content
