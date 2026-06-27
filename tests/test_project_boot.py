from django.urls import reverse
from django.conf import settings


def test_editor_page_loads(client):
    response = client.get(reverse("scheduler:editor"))

    assert response.status_code == 200
    assert b"Dance Lesson Scheduler" in response.content


def test_mvp_does_not_install_account_apps():
    assert "django.contrib.admin" not in settings.INSTALLED_APPS
    assert "django.contrib.auth" not in settings.INSTALLED_APPS
    assert "django.contrib.sessions" not in settings.INSTALLED_APPS
