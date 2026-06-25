from django.urls import reverse


def test_editor_page_loads(client):
    response = client.get(reverse("scheduler:editor"))

    assert response.status_code == 200
    assert b"Dance Lesson Scheduler" in response.content
