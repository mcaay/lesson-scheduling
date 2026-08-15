from datetime import date

from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse

from .editor_data import build_editor_data
from .examples import EXAMPLE_SPEC
from .forms import RawSpecForm
from .result_grid import build_result_grid
from .solve_jobs import read_solve_job, start_solve_job
from .solver import ScheduledLesson, SolveResult, solve_schedule
from .spec_models import SpecError
from .spec_parser import parse_spec
from .spec_validation import validate_spec


def editor(request):
    if request.method == "POST":
        form = RawSpecForm(request.POST)
        if form.is_valid():
            form = RawSpecForm(initial={"raw_spec": form.cleaned_data["raw_spec"]})
        else:
            form = RawSpecForm(initial={"raw_spec": EXAMPLE_SPEC})
    else:
        form = RawSpecForm(initial={"raw_spec": EXAMPLE_SPEC})
    return render_editor(request, form, [])


def run_schedule(request):
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        job_id = start_solve_job(request.POST.get("raw_spec", ""))
        return JsonResponse(
            {"status_url": reverse("scheduler:solve_job_status", args=[job_id])},
            status=202,
        )

    form = RawSpecForm(request.POST)
    if not form.is_valid():
        return render_editor(request, form, form["raw_spec"].errors)

    parsed = parse_spec(form.cleaned_data["raw_spec"])
    if parsed.errors:
        return render_editor(request, form, parsed.errors)

    validation_errors = validate_spec(parsed.spec)
    if validation_errors:
        return render_editor(request, form, validation_errors)

    result = solve_schedule(parsed.spec)
    return render_result(request, form, parsed.spec, result)


def solve_job_status(request, job_id):
    job = read_solve_job(job_id)
    if job is None:
        raise Http404

    response = {"status": job["status"]}
    if job["status"] != "pending":
        response["result_url"] = reverse(
            "scheduler:solve_job_result",
            args=[job_id],
        )
    return JsonResponse(response)


def solve_job_result(request, job_id):
    job = read_solve_job(job_id)
    if job is None:
        raise Http404

    form = RawSpecForm(initial={"raw_spec": job["raw_spec"]})
    if job["status"] == "pending":
        return render_editor(request, form, ["The schedule is still being generated."])
    if job["status"] == "invalid":
        errors = [SpecError(**error) for error in job["errors"]]
        return render_editor(request, form, errors)
    if job["status"] == "error":
        return render_editor(request, form, [job["message"]])

    parsed = parse_spec(job["raw_spec"])
    if not parsed.is_valid:
        return render_editor(request, form, parsed.errors)

    result = SolveResult(
        solved=job["solved"],
        lessons=tuple(
            ScheduledLesson(
                **{
                    **lesson,
                    "instructor_names": tuple(lesson["instructor_names"]),
                }
            )
            for lesson in job["lessons"]
        ),
        message=job["message"],
    )
    return render_result(request, form, parsed.spec, result)


def download_spec(request):
    raw_spec = request.POST.get("raw_spec", "")
    response = HttpResponse(raw_spec, content_type="text/plain")
    response["Content-Disposition"] = (
        f'attachment; filename="{date.today()}-lesson-schedule.txt"'
    )
    return response


def import_spec(request):
    upload = request.FILES.get("spec_file")
    try:
        raw_spec = upload.read().decode("utf-8") if upload else EXAMPLE_SPEC
    except UnicodeDecodeError:
        form = RawSpecForm(initial={"raw_spec": EXAMPLE_SPEC})
        return render_editor(request, form, ["Upload a UTF-8 text file."])
    form = RawSpecForm(initial={"raw_spec": raw_spec})
    return render_editor(request, form, [])


def render_editor(request, form, errors):
    raw_spec = form["raw_spec"].value() or EXAMPLE_SPEC
    return render(
        request,
        "scheduler/editor.html",
        {
            "form": form,
            "errors": errors,
            "editor": build_editor_data(raw_spec),
        },
    )


def render_result(request, form, spec, result):
    return render(
        request,
        "scheduler/result.html",
        {
            "form": form,
            "result": result,
            "result_grid": build_result_grid(spec, result) if result.solved else None,
        },
    )
