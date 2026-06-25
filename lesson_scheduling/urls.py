from django.urls import include, path


urlpatterns = [
    path("", include("scheduler.urls")),
]
