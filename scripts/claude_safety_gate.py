#!/usr/bin/env python3
"""Claude Code pre-tool safety gate.

Reads the Bash tool input as JSON from stdin (Claude Code hook convention).
Exits 1 (blocking) with a clear explanation for known dangerous commands.
Exits 0 (allow) for everything else.

Blocked categories:
  - Force push / hard reset / discard-all (irreversible git operations)
  - --no-verify (skipping pre-commit hooks)
  - Destructive SQL (DROP/TRUNCATE TABLE)
  - rm -rf on broad paths
"""
import json
import re
import sys

# (pattern, user-facing reason)
BLOCKED_PATTERNS = [
    (
        r"git\s+push\s+(-f\b|--force\b)",
        "Force push can silently overwrite remote history. Use a regular push. "
        "If this is truly needed, run it manually in a terminal.",
    ),
    (
        r"git\s+reset\s+--hard",
        "Hard reset permanently destroys uncommitted work. "
        "Confirm the intent with the user before running this manually.",
    ),
    (
        r"git\s+clean\s+-[a-zA-Z]*f",
        "git clean -f permanently deletes all untracked files. Run manually if needed.",
    ),
    (
        r"git\s+checkout\s+--\s*\.",
        "git checkout -- . discards ALL unstaged changes. Run manually if needed.",
    ),
    (
        r"git\s+restore\s+\.",
        "git restore . discards ALL unstaged changes. Run manually if needed.",
    ),
    (
        r"--no-verify",
        "Skipping hooks (--no-verify) is not permitted. "
        "Fix the underlying hook failure instead.",
    ),
    (
        r"git\s+commit\s+--amend",
        "Amending commits that are already pushed causes history divergence. "
        "Create a new commit instead.",
    ),
    (
        r"\bDROP\s+TABLE\b",
        "DROP TABLE is irreversible. Confirm with the user and run manually.",
    ),
    (
        r"\bTRUNCATE\s+TABLE\b",
        "TRUNCATE TABLE permanently deletes all rows. Confirm and run manually.",
    ),
    (
        r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f\s+/",
        "rm -rf on an absolute path is blocked. Run manually if truly needed.",
    ),
    (
        r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f\s+\.",
        "rm -rf on the current directory is blocked.",
    ),
    (
        r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f\s+~",
        "rm -rf on the home directory is blocked.",
    ),
]


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        sys.exit(0)

    try:
        data = json.loads(raw)
        command = data.get("command", "") if isinstance(data, dict) else str(data)
    except (json.JSONDecodeError, TypeError):
        sys.exit(0)

    for pattern, reason in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            print(
                f"\n\033[31m[SAFETY GATE]\033[0m Command blocked.\n"
                f"Command : {command!r}\n"
                f"Reason  : {reason}\n",
                file=sys.stderr,
            )
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
