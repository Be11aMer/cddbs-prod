#!/usr/bin/env python3
"""Scan files for accidentally committed secrets, API keys, and credentials.

Used in CI to reject PRs that contain hardcoded secrets.
Exit code 0 = clean, exit code 1 = secrets found.
"""

import re
import sys
from pathlib import Path

# Directories and files to skip
SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__",
    ".pytest_cache", ".cache", "dist", "build", ".eggs",
}
SKIP_FILES = {
    "detect_secrets.py",  # this file contains patterns, not secrets
    "package-lock.json",
    "known_narratives.json",
}
# Only scan these extensions
SCAN_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".yml", ".yaml", ".json",
    ".toml", ".cfg", ".ini", ".env", ".sh", ".bash", ".txt", ".md",
    ".html", ".css", ".sql", ".dockerfile",
}

# Patterns that indicate a real secret (not a placeholder)
SECRET_PATTERNS = [
    # Generic API keys (long alphanumeric strings assigned to key variables)
    (r"""(?i)(api[_-]?key|apikey)\s*[:=]\s*['"]([A-Za-z0-9_\-]{20,})['"]""",
     "API key"),
    # Generic secret/token assignments
    (r"""(?i)(secret|token|bearer)\s*[:=]\s*['"]([A-Za-z0-9_\-/.+]{20,})['"]""",
     "Secret/Token"),
    # AWS access keys
    (r"""AKIA[0-9A-Z]{16}""",
     "AWS Access Key"),
    # AWS secret keys
    (r"""(?i)aws_secret_access_key\s*[:=]\s*['"]?([A-Za-z0-9/+=]{40})['"]?""",
     "AWS Secret Key"),
    # Google API keys
    (r"""AIza[0-9A-Za-z_\-]{35}""",
     "Google API Key"),
    # GitHub tokens
    (r"""gh[pousr]_[A-Za-z0-9_]{36,}""",
     "GitHub Token"),
    # Generic private keys
    (r"""-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----""",
     "Private Key"),
    # PostgreSQL connection strings with non-default passwords
    (r"""postgresql(?:\+\w+)?://\w+:([^@\s]{8,})@(?!localhost|db:|127\.0\.0\.1)""",
     "Database Password in Connection String"),
    # Slack tokens
    (r"""xox[bporas]-[0-9a-zA-Z-]{10,}""",
     "Slack Token"),
    # Telegram bot tokens
    (r"""[0-9]{8,10}:[A-Za-z0-9_-]{35}""",
     "Telegram Bot Token"),
    # Twitter bearer tokens (long base64)
    (r"""(?i)bearer\s+[A-Za-z0-9%._\-]{50,}""",
     "Bearer Token"),
    # Hex-encoded secrets (64+ chars, likely SHA256 or similar)
    (r"""(?i)(secret|password|key|token)\s*[:=]\s*['"]([0-9a-f]{64,})['"]""",
     "Hex Secret"),
    # .env file patterns with real-looking values (not placeholders)
    (r"""(?i)^(?:SERPAPI_KEY|GOOGLE_API_KEY|TWITTER_BEARER_TOKEN|TELEGRAM_BOT_TOKEN)\s*=\s*(?!$|your_|changeme|placeholder|none|todo|xxx)(.{10,})$""",
     "Environment Variable with Value"),
]

# Compile patterns
COMPILED_PATTERNS = [
    (re.compile(pattern, re.MULTILINE), desc)
    for pattern, desc in SECRET_PATTERNS
]

# Known false positives to ignore
FALSE_POSITIVE_VALUES = {
    "your_serpapi_key", "your_google_api_key", "your_twitter_bearer_token",
    "your_telegram_bot_token", "optional-override", "optional-shared-secret",
    "test", "admin", "example", "changeme", "placeholder", "none", "todo",
    "your_serpapi_key_here", "your_google_api_key_here",
}


def should_scan(path: Path) -> bool:
    """Check if a file should be scanned."""
    for part in path.parts:
        if part in SKIP_DIRS:
            return False
    if path.name in SKIP_FILES:
        return False
    if path.name.startswith(".") and path.suffix not in SCAN_EXTENSIONS:
        return False
    return path.suffix.lower() in SCAN_EXTENSIONS or path.name in {
        ".env", ".env.example", "Dockerfile", "Makefile",
    }


def scan_file(filepath: Path) -> list[tuple[int, str, str]]:
    """Scan a single file for secrets. Returns list of (line_num, type, match)."""
    findings = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except (OSError, PermissionError):
        return findings

    lines = content.splitlines()
    for line_num, line in enumerate(lines, 1):
        # Skip comments that are clearly documentation
        stripped = line.strip()
        if stripped.startswith("#") and any(
            w in stripped.lower()
            for w in ["example", "template", "placeholder", "todo", "change"]
        ):
            continue

        for pattern, desc in COMPILED_PATTERNS:
            matches = pattern.findall(line)
            if matches:
                # Check for false positives
                match_str = str(matches[0]) if matches else ""
                if isinstance(matches[0], tuple):
                    # Groups captured — check the value part
                    values = [
                        v.lower().strip("'\" ")
                        for v in matches[0]
                        if len(v) > 5
                    ]
                else:
                    values = [match_str.lower().strip("'\" ")]

                if any(v in FALSE_POSITIVE_VALUES for v in values):
                    continue

                # Skip test database connection strings
                if "test:test@localhost" in line or "admin:admin@db:" in line:
                    continue
                if "admin:admin@localhost" in line:
                    continue

                findings.append((line_num, desc, stripped[:120]))

    return findings


def main() -> int:
    root = Path(".")
    all_findings: dict[str, list[tuple[int, str, str]]] = {}
    files_scanned = 0

    for filepath in sorted(root.rglob("*")):
        if not filepath.is_file():
            continue
        if not should_scan(filepath):
            continue

        files_scanned += 1
        findings = scan_file(filepath)
        if findings:
            all_findings[str(filepath)] = findings

    print(f"Scanned {files_scanned} files for secrets.")

    if all_findings:
        print(f"\n{'=' * 60}")
        print(f"SECRETS DETECTED — {sum(len(f) for f in all_findings.values())} finding(s) in {len(all_findings)} file(s)")
        print(f"{'=' * 60}\n")

        for filepath, findings in all_findings.items():
            print(f"  {filepath}:")
            for line_num, desc, preview in findings:
                print(f"    Line {line_num}: [{desc}] {preview}")
            print()

        print("ACTION REQUIRED: Remove all hardcoded secrets and use environment variables instead.")
        print("See SECURITY.md for best practices.")
        return 1

    print("No secrets detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
