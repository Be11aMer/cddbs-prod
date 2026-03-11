# Changelog

All notable changes to the CDDBS (Counter-Disinformation Database System) project
are documented in this file.

## [2026.03] - 2026-03-11

### First production release

This release consolidates all features developed across research sprints 1-5
into a deployable, documented platform.

### Added

- **GitHub Actions CI pipeline** — Lint (ruff), pytest with PostgreSQL service,
  and frontend build/type-check run on every push and PR to `main`.
- **JSON export endpoint** (`GET /analysis-runs/{id}/export`) — Downloads a
  structured JSON file containing the full briefing, quality scorecard,
  narrative matches, and article analyses.
- **Export JSON button** in the Report View dialog — one-click download of the
  complete analysis as a portable JSON archive.
- **Operational metrics endpoint** (`GET /metrics`) — Returns success rate,
  average quality score, average duration, top countries, and top narratives.
- **Quality trends endpoint** (`GET /stats/quality-trends`) — Time-series
  quality data per outlet with aggregate averages, for tracking briefing quality
  over time.
- **Comprehensive developer documentation** (`DEVELOPER.md`) — Architecture
  overview, module reference, API catalog, data model, pipeline flow, and
  contributor guide.

### Existing features (documented for completeness)

- 7-section structured intelligence briefing generation via Gemini (v1.3 prompt)
- 70-point, 7-dimension quality scoring rubric
- Known disinformation narrative matching (keyword-based, 50+ narratives)
- Twitter and Telegram social media analysis pipeline
- Topic mode: discover outlets pushing narratives on specific topics
- Event intelligence pipeline with RSS and GDELT collectors running every 3 min
- Event clustering, deduplication, burst detection, and narrative risk scoring
- Monitoring dashboard with 10+ visualization components
- Interactive report viewer with radar charts, narrative tags, annotated articles
- Tester feedback collection system
- Docker Compose deployment (PostgreSQL + FastAPI + Vite frontend)
- 132 test functions across 12 test files
