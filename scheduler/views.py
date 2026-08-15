from datetime import date
from pathlib import Path

from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .editor_data import build_editor_data
from .examples import EXAMPLE_SPEC
from .forms import RawSpecForm
from .result_grid import build_result_grid
from .solve_jobs import SolveQueueFull, read_solve_job, start_solve_job
from .solver import ScheduledLesson, SolveResult
from .spec_limits import MAX_RAW_SPEC_BYTES
from .spec_models import SpecError
from .spec_parser import parse_spec


@require_http_methods(["GET", "POST"])
def editor(request):
    if request.method == "POST":
        submitted_form = RawSpecForm(request.POST)
        if submitted_form.is_valid():
            form = RawSpecForm(
                initial={"raw_spec": submitted_form.cleaned_data["raw_spec"]}
            )
        else:
            form = submitted_form
    else:
        form = RawSpecForm(initial={"raw_spec": EXAMPLE_SPEC})
    return render_editor(request, form, list(form.errors.get("raw_spec", ())))


@require_POST
def run_schedule(request):
    form = RawSpecForm(request.POST)
    if not form.is_valid():
        errors = list(form.errors.get("raw_spec", ()))
        if _wants_json(request):
            return JsonResponse({"errors": errors}, status=400)
        return render_editor(request, form, errors, status=400)

    try:
        job_id = start_solve_job(form.cleaned_data["raw_spec"])
    except SolveQueueFull:
        message = "The scheduler is busy. Please try again in a few minutes."
        if _wants_json(request):
            return JsonResponse({"error": message}, status=503)
        return render_editor(request, form, [message], status=503)

    result_url = reverse("scheduler:solve_job_result", args=[job_id])
    if not _wants_json(request):
        return redirect(result_url)
    return JsonResponse(
        {"status_url": reverse("scheduler:solve_job_status", args=[job_id])},
        status=202,
    )


@require_GET
def solve_job_status(request, job_id):
    job = read_solve_job(job_id)
    if job is None:
        raise Http404

    response_data = {"status": job["status"]}
    if job["status"] in {"complete", "invalid", "error"}:
        response_data["result_url"] = reverse(
            "scheduler:solve_job_result",
            args=[job_id],
        )
    return _never_cache(JsonResponse(response_data))


@require_GET
def solve_job_result(request, job_id):
    job = read_solve_job(job_id)
    if job is None:
        raise Http404

    if job["status"] in {"queued", "running"}:
        return _never_cache(
            render(
                request,
                "scheduler/solve_pending.html",
                {
                    "job_status": job["status"],
                    "refresh_url": reverse(
                        "scheduler:solve_job_result",
                        args=[job_id],
                    ),
                },
            )
        )

    form = RawSpecForm(initial={"raw_spec": job["raw_spec"]})
    if job["status"] == "invalid":
        errors = [SpecError(**error) for error in job["errors"]]
        return _never_cache(render_editor(request, form, errors))
    if job["status"] == "error":
        return _never_cache(render_editor(request, form, [job["message"]]))

    parsed = parse_spec(job["raw_spec"])
    if not parsed.is_valid:
        return _never_cache(render_editor(request, form, parsed.errors))

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
        status=job.get("solver_status", ""),
    )
    return _never_cache(render_result(request, form, parsed.spec, result))


@require_POST
def download_spec(request):
    raw_spec = request.POST.get("raw_spec", "")
    response = HttpResponse(raw_spec, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="{date.today()}-lesson-schedule.txt"'
    )
    return response


@require_POST
def import_spec(request):
    upload = request.FILES.get("spec_file")
    error = _upload_error(upload)
    if error:
        return render_editor(
            request,
            RawSpecForm(initial={"raw_spec": ""}),
            [error],
            status=400,
        )

    try:
        uploaded_bytes = upload.read(MAX_RAW_SPEC_BYTES + 1)
        if len(uploaded_bytes) > MAX_RAW_SPEC_BYTES:
            return render_editor(
                request,
                RawSpecForm(initial={"raw_spec": ""}),
                [f"The specification cannot exceed {MAX_RAW_SPEC_BYTES // 1000} KB."],
                status=400,
            )
        raw_spec = uploaded_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return render_editor(
            request,
            RawSpecForm(initial={"raw_spec": ""}),
            ["Upload a UTF-8 text file."],
            status=400,
        )
    form = RawSpecForm(initial={"raw_spec": raw_spec})
    return render_editor(request, form, [])


def render_editor(request, form, errors, *, status=200):
    raw_spec = form["raw_spec"].value()
    raw_spec = "" if raw_spec is None else raw_spec
    raw_spec_has_syntax_errors = bool(raw_spec.strip()) and not parse_spec(
        raw_spec
    ).is_valid
    return render(
        request,
        "scheduler/editor.html",
        {
            "form": form,
            "errors": errors,
            "editor": build_editor_data(raw_spec),
            "raw_spec_authoritative": bool(errors) or raw_spec_has_syntax_errors,
        },
        status=status,
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


def _upload_error(upload):
    if upload is None:
        return "Choose a .txt specification file."
    if upload.size > MAX_RAW_SPEC_BYTES:
        return f"The specification cannot exceed {MAX_RAW_SPEC_BYTES // 1000} KB."
    if Path(upload.name).suffix.lower() != ".txt":
        return "Upload a .txt specification file."
    if upload.content_type and not (
        upload.content_type.startswith("text/")
        or upload.content_type == "application/octet-stream"
    ):
        return "Upload a plain-text specification file."
    return None


def _wants_json(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _never_cache(response):
    response["Cache-Control"] = "no-store"
    return response
