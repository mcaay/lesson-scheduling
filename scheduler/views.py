from datetime import date

from django.http import HttpResponse
from django.shortcuts import render

from .examples import EXAMPLE_SPEC
from .forms import RawSpecForm
from .solver import solve_schedule
from .spec_parser import parse_spec
from .spec_validation import validate_spec


def editor(request):
    form = RawSpecForm(initial={"raw_spec": EXAMPLE_SPEC})
    return render(request, "scheduler/editor.html", {"form": form, "errors": []})


def run_schedule(request):
    form = RawSpecForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "scheduler/editor.html",
            {"form": form, "errors": form["raw_spec"].errors},
        )

    parsed = parse_spec(form.cleaned_data["raw_spec"])
    if parsed.errors:
        return render(
            request,
            "scheduler/editor.html",
            {"form": form, "errors": parsed.errors},
        )

    validation_errors = validate_spec(parsed.spec)
    if validation_errors:
        return render(
            request,
            "scheduler/editor.html",
            {"form": form, "errors": validation_errors},
        )

    result = solve_schedule(parsed.spec)
    return render(request, "scheduler/result.html", {"form": form, "result": result})


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
        return render(
            request,
            "scheduler/editor.html",
            {"form": form, "errors": ["Upload a UTF-8 text file."]},
        )
    form = RawSpecForm(initial={"raw_spec": raw_spec})
    return render(request, "scheduler/editor.html", {"form": form, "errors": []})
