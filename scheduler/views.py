from datetime import date

from django.http import HttpResponse
from django.shortcuts import render

from .editor_data import build_editor_data
from .examples import EXAMPLE_SPEC
from .forms import RawSpecForm
from .result_grid import build_result_grid
from .solver import solve_schedule
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
    context = {
        "form": form,
        "result": result,
        "result_grid": build_result_grid(parsed.spec, result) if result.solved else None,
    }
    return render(request, "scheduler/result.html", context)


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
