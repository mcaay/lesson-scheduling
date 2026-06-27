from django.urls import path

from . import views


app_name = "scheduler"

urlpatterns = [
    path("", views.editor, name="editor"),
    path("run/", views.run_schedule, name="run"),
    path("download-spec/", views.download_spec, name="download_spec"),
    path("import-spec/", views.import_spec, name="import_spec"),
]
