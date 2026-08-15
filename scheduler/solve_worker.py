import json
import sys
from dataclasses import asdict

from .solver import solve_schedule
from .spec_parser import parse_spec
from .spec_validation import validate_spec


def main():
    raw_spec = sys.stdin.read()
    parsed = parse_spec(raw_spec)
    errors = parsed.errors or tuple(validate_spec(parsed.spec))
    if errors:
        raise ValueError("Worker received an invalid specification")

    result = solve_schedule(parsed.spec)
    json.dump(
        {
            "solved": result.solved,
            "message": result.message,
            "solver_status": result.status,
            "lessons": [asdict(lesson) for lesson in result.lessons],
        },
        sys.stdout,
        ensure_ascii=False,
    )


if __name__ == "__main__":
    main()
