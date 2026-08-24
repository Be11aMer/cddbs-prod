#!/usr/bin/env python3
"""Append one JSONL line to .claude/audit.jsonl on every tool use."""
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

data = json.loads(sys.stdin.read() or "{}")
entry = {
    "ts": datetime.now(UTC).isoformat(),
    "session": os.getenv("CLAUDE_SESSION_ID", ""),
    "tool": sys.argv[1] if len(sys.argv) > 1 else data.get("tool_name", ""),
    "input_summary": str(data)[:200],
}
log = Path(__file__).resolve().parent.parent / ".claude" / "audit.jsonl"
log.parent.mkdir(exist_ok=True)
with log.open("a") as f:
    f.write(json.dumps(entry) + "\n")
