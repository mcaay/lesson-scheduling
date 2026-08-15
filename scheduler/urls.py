from django.urls import path

from . import views


app_name = "scheduler"

urlpatterns = [
    path("", views.editor, name="editor"),
    path("run/", views.run_schedule, name="run"),
    path(
        "solve-jobs/<uuid:job_id>/",
        views.solve_job_status,
        name="solve_job_status",
    ),
    path(
        "solve-jobs/<uuid:job_id>/result/",
        views.solve_job_result,
        name="solve_job_result",
    ),
    path("download-spec/", views.download_spec, name="download_spec"),
    path("import-spec/", views.import_spec, name="import_spec"),
]
