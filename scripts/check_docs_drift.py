#!/usr/bin/env python3
"""
Documentation drift detector for CDDBS.

Extracts facts from the live codebase (API endpoints, DB models, env vars,
frontend components, dependencies) and verifies they are mentioned in
README.md and DEVELOPER.md.

Exits with code 1 if any documentation has drifted from reality.
This enforces the EU Cyber Resilience Act (CRA) requirement that
technical documentation stays accurate and current.

Usage:
    python scripts/check_docs_drift.py          # from repo root
    python scripts/check_docs_drift.py --fix    # print what needs updating (no auto-fix)
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve repo root (parent of scripts/)
# ---------------------------------------------------------------------------
REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"
DEVELOPER = REPO / "DEVELOPER.md"
API_MAIN = REPO / "src" / "cddbs" / "api" / "main.py"
MODELS_PY = REPO / "src" / "cddbs" / "models.py"
CONFIG_PY = REPO / "src" / "cddbs" / "config.py"
REQUIREMENTS = REPO / "requirements.txt"
COMPONENTS_DIR = REPO / "frontend" / "src" / "components"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class DriftReport:
    """Collects drift violations and prints a summary."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def print_summary(self) -> int:
        if self.warnings:
            print("\n--- WARNINGS ---")
            for w in self.warnings:
                print(f"  [WARN] {w}")

        if self.errors:
            print("\n--- DOCUMENTATION DRIFT DETECTED ---")
            for e in self.errors:
                print(f"  [FAIL] {e}")
            print(
                f"\n{len(self.errors)} drift error(s) found. "
                "Update README.md and/or DEVELOPER.md before merging."
            )
            return 1

        print("\nAll documentation checks passed.")
        return 0


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalise(s: str) -> str:
    """Lower-case and collapse whitespace for fuzzy matching."""
    return re.sub(r"\s+", " ", s.lower().strip())

# ---------------------------------------------------------------------------
# 1. API Endpoints
# ---------------------------------------------------------------------------

def extract_api_endpoints(source: str) -> list[tuple[str, str]]:
    """Return [(method, path), ...] from FastAPI decorator lines."""
    pattern = re.compile(r'@app\.(get|post|put|delete|patch)\(\s*"([^"]+)"')
    results = []
    for m in pattern.finditer(source):
        method = m.group(1).upper()
        path = m.group(2)
        results.append((method, path))
    return results


def _normalise_path(path: str) -> str:
    """Collapse path template params: /foo/{bar_id} -> /foo/{} for matching."""
    return re.sub(r"\{[^}]+\}", "{}", path)


def check_api_endpoints(report: DriftReport) -> None:
    """Every API endpoint must appear in DEVELOPER.md.
    Key endpoints must appear in README.md."""
    source = read_text(API_MAIN)
    dev_doc = read_text(DEVELOPER)
    readme = read_text(README)

    endpoints = extract_api_endpoints(source)
    if not endpoints:
        report.error("Could not extract any API endpoints from main.py — parser may be broken.")
        return

    # --- DEVELOPER.md: every endpoint must be documented ---
    # Normalise path params in both code and docs so {report_id} matches {id}
    dev_lower = _normalise(dev_doc)
    # Also build a set of normalised documented paths
    doc_paths_raw = re.findall(r'`(/[^`]+)`', dev_doc)
    doc_paths_normalised = {_normalise_path(p.lower()) for p in doc_paths_raw}
    # Also check plain text occurrences (tables, prose)
    missing_dev = []
    for method, path in endpoints:
        path_norm = _normalise_path(path.lower())
        # Match if the normalised path appears in documented paths OR raw text
        if path_norm not in doc_paths_normalised and path.lower() not in dev_lower:
            missing_dev.append(f"{method} {path}")

    if missing_dev:
        report.error(
            f"DEVELOPER.md is missing {len(missing_dev)} API endpoint(s):\n"
            + "\n".join(f"      - {e}" for e in missing_dev)
        )

    # --- README.md: key endpoint groups must be mentioned ---
    readme_lower = _normalise(readme)
    key_paths = ["/analysis-runs", "/health", "/topic-runs", "/events", "/feedback"]
    missing_readme = [p for p in key_paths if p not in readme_lower]
    if missing_readme:
        report.error(
            f"README.md is missing references to key endpoint group(s):\n"
            + "\n".join(f"      - {p}" for p in missing_readme)
        )

# ---------------------------------------------------------------------------
# 2. Database Models (tables)
# ---------------------------------------------------------------------------

def extract_table_names(source: str) -> list[str]:
    """Return table names from __tablename__ assignments."""
    return re.findall(r'__tablename__\s*=\s*"(\w+)"', source)


def extract_model_classes(source: str) -> list[str]:
    """Return ORM class names that inherit from Base."""
    return re.findall(r"class\s+(\w+)\(Base\)", source)


def check_db_models(report: DriftReport) -> None:
    source = read_text(MODELS_PY)
    dev_doc = read_text(DEVELOPER)
    dev_lower = _normalise(dev_doc)

    tables = extract_table_names(source)
    if not tables:
        report.error("Could not extract any table names from models.py.")
        return

    missing = [t for t in tables if t not in dev_lower]
    if missing:
        report.error(
            f"DEVELOPER.md is missing {len(missing)} database table(s):\n"
            + "\n".join(f"      - {t}" for t in missing)
        )

    classes = extract_model_classes(source)
    readme_lower = _normalise(read_text(README))
    # README should at least mention the models.py file
    if "models.py" not in readme_lower and "models" not in readme_lower:
        report.warn("README.md does not reference models.py or database models.")

# ---------------------------------------------------------------------------
# 3. Environment Variables
# ---------------------------------------------------------------------------

def extract_env_vars(source: str) -> list[str]:
    """Return env var names from os.getenv() calls."""
    return re.findall(r'os\.getenv\(\s*"(\w+)"', source)


def check_env_vars(report: DriftReport) -> None:
    source = read_text(CONFIG_PY)
    dev_doc = read_text(DEVELOPER)
    dev_lower = _normalise(dev_doc)

    env_vars = extract_env_vars(source)
    if not env_vars:
        report.error("Could not extract any env vars from config.py.")
        return

    missing = [v for v in env_vars if v.lower() not in dev_lower]
    if missing:
        report.error(
            f"DEVELOPER.md is missing {len(missing)} environment variable(s):\n"
            + "\n".join(f"      - {v}" for v in missing)
        )

# ---------------------------------------------------------------------------
# 4. Frontend Components
# ---------------------------------------------------------------------------

def list_components() -> list[str]:
    """Return component filenames (without extension)."""
    if not COMPONENTS_DIR.is_dir():
        return []
    return sorted(
        p.stem for p in COMPONENTS_DIR.glob("*.tsx")
    )


def check_frontend_components(report: DriftReport) -> None:
    dev_doc = read_text(DEVELOPER)
    dev_lower = _normalise(dev_doc)

    components = list_components()
    if not components:
        report.warn("No frontend components found — skipping check.")
        return

    missing = [c for c in components if c.lower() not in dev_lower]
    if missing:
        report.error(
            f"DEVELOPER.md is missing {len(missing)} frontend component(s):\n"
            + "\n".join(f"      - {c}" for c in missing)
        )

# ---------------------------------------------------------------------------
# 5. Python Dependencies
# ---------------------------------------------------------------------------

def extract_requirements() -> list[str]:
    """Return package names from requirements.txt (strip version specifiers)."""
    if not REQUIREMENTS.is_file():
        return []
    lines = REQUIREMENTS.read_text().strip().splitlines()
    pkgs = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip extras and version specifiers: package[extra]>=1.0 -> package
        name = re.split(r"[\[>=<!\s]", line)[0]
        if name:
            pkgs.append(name)
    return pkgs


def check_dependencies(report: DriftReport) -> None:
    dev_doc = read_text(DEVELOPER)
    dev_lower = _normalise(dev_doc)

    pkgs = extract_requirements()
    if not pkgs:
        report.warn("Could not read requirements.txt — skipping dependency check.")
        return

    # Only flag core packages (skip test/dev utilities)
    core_pkgs = [p for p in pkgs if p not in ("pytest", "pytest-cov", "ruff")]
    missing = []
    for p in core_pkgs:
        # Normalise: psycopg2-binary -> psycopg2_binary, also check base name (psycopg2)
        name_norm = p.lower().replace("-", "_")
        base_name = name_norm.split("_")[0] if "_" in name_norm else name_norm
        dev_norm = dev_lower.replace("-", "_")
        if name_norm not in dev_norm and base_name not in dev_norm:
            missing.append(p)
    if missing:
        report.error(
            f"DEVELOPER.md is missing {len(missing)} Python dependency reference(s):\n"
            + "\n".join(f"      - {p}" for p in missing)
        )

# ---------------------------------------------------------------------------
# 6. README Freshness — key sections that must exist
# ---------------------------------------------------------------------------

REQUIRED_README_SECTIONS = [
    "quick start",
    "architecture",
    "api",
    "project structure",
    "development",
]


def check_readme_sections(report: DriftReport) -> None:
    readme_lower = _normalise(read_text(README))
    missing = [s for s in REQUIRED_README_SECTIONS if s not in readme_lower]
    if missing:
        report.error(
            f"README.md is missing required section(s):\n"
            + "\n".join(f"      - \"{s}\"" for s in missing)
        )


# ---------------------------------------------------------------------------
# 7. DEVELOPER.md Freshness — key sections that must exist
# ---------------------------------------------------------------------------

REQUIRED_DEV_SECTIONS = [
    "api reference",
    "data model",
    "pipeline",
    "frontend",
    "configuration",
    "deployment",
    "testing",
    "ci/cd",
]


def check_developer_sections(report: DriftReport) -> None:
    dev_lower = _normalise(read_text(DEVELOPER))
    missing = [s for s in REQUIRED_DEV_SECTIONS if s not in dev_lower]
    if missing:
        report.error(
            f"DEVELOPER.md is missing required section(s):\n"
            + "\n".join(f"      - \"{s}\"" for s in missing)
        )

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    # Verify required files exist
    for path, name in [
        (README, "README.md"),
        (DEVELOPER, "DEVELOPER.md"),
        (API_MAIN, "src/cddbs/api/main.py"),
        (MODELS_PY, "src/cddbs/models.py"),
        (CONFIG_PY, "src/cddbs/config.py"),
    ]:
        if not path.is_file():
            print(f"FATAL: Required file not found: {name}")
            return 1

    report = DriftReport()

    print("=== CDDBS Documentation Drift Check ===\n")

    print("[1/7] Checking API endpoints ...")
    check_api_endpoints(report)

    print("[2/7] Checking database models ...")
    check_db_models(report)

    print("[3/7] Checking environment variables ...")
    check_env_vars(report)

    print("[4/7] Checking frontend components ...")
    check_frontend_components(report)

    print("[5/7] Checking Python dependencies ...")
    check_dependencies(report)

    print("[6/7] Checking README.md sections ...")
    check_readme_sections(report)

    print("[7/7] Checking DEVELOPER.md sections ...")
    check_developer_sections(report)

    return report.print_summary()


if __name__ == "__main__":
    sys.exit(main())
