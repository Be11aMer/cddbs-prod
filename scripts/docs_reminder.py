#!/usr/bin/env python3
"""Claude Code post-edit docs reminder.

Non-blocking hook: prints a reminder to update DEVELOPER.md when editing
files that correspond to documented sections. Reads tool input as JSON from stdin.
"""
import json
import sys

# Map file path patterns to DEVELOPER.md sections
REMINDERS = [
    (
        ["src/cddbs/api/main.py"],
        "DEVELOPER.md §5 (API Reference) — add/update the endpoint entry.",
    ),
    (
        ["src/cddbs/models.py"],
        "DEVELOPER.md §6 (Data Models) — update the table or column description.",
    ),
    (
        ["frontend/src/components/"],
        "DEVELOPER.md §8 (Frontend) — update the component list if this is a new file.",
    ),
    (
        ["src/cddbs/config.py"],
        "DEVELOPER.md §9 (Configuration) — add/update the env var row.",
    ),
    (
        ["src/cddbs/pipeline/", "src/cddbs/collectors/"],
        "DEVELOPER.md §4 (Backend Modules) — add/update the module description.",
    ),
    (
        ["src/cddbs/database.py"],
        "DEVELOPER.md §6 (Data Models) — document any new startup migration.",
    ),
    (
        ["src/cddbs/scheduler.py"],
        "DEVELOPER.md §16/§17 (Scheduler) — update the job table if a job was added/removed.",
    ),
]


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        sys.exit(0)

    try:
        data = json.loads(raw)
        file_path = data.get("file_path", "") if isinstance(data, dict) else ""
    except (json.JSONDecodeError, TypeError):
        sys.exit(0)

    if not file_path:
        sys.exit(0)

    for paths, reminder in REMINDERS:
        if any(p in file_path for p in paths):
            print(
                f"\n\033[33m[DOCS REMINDER]\033[0m {reminder}\n"
                f"Also update: CHANGELOG.md\n",
                file=sys.stderr,
            )
            break

    sys.exit(0)


if __name__ == "__main__":
    main()
