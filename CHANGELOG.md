# Changelog

All notable changes to the CDDBS (Cyber Disinformation Detection Briefing System) project
are documented in this file.

## [2026.03.1] - 2026-03-18

### Sprint 7: Intelligence Layer

This release adds the intelligence layer that transforms raw ingested articles
into actionable event clusters with risk scoring.

### Added

- **TF-IDF event clustering pipeline** (`pipeline/event_clustering.py`) —
  Agglomerative clustering on TF-IDF vectors groups related articles into
  EventCluster records with title, keywords, countries, and event type
  classification (conflict, protest, diplomacy, disaster, cyber, info_warfare).
- **Z-score burst detection** (`pipeline/burst_detection.py`) — Detects
  keyword frequency spikes using rolling 24h baseline and z-score threshold
  (default 3.0). Creates NarrativeBurst records for active spikes.
- **Narrative risk scoring** (`pipeline/narrative_risk.py`) — 4-signal
  composite score (0-1) per event cluster: source concentration, burst
  magnitude, timing synchronization, and known narrative match.
- **Automated processing pipeline** — Clustering, burst detection, and risk
  scoring run automatically after each collector cycle via CollectorManager.
- **Events API endpoints**:
  - `GET /events` — List event clusters with filters (type, country, status,
    min_risk, limit, offset)
  - `GET /events/{id}` — Event detail with full article list and keywords
  - `GET /events/map` — Events grouped by country for map visualization
  - `GET /events/bursts` — Active narrative bursts with z-scores
- **BurstTimeline.tsx** — New dashboard component showing active keyword
  frequency spikes ranked by z-score, with threshold indicator and frequency
  bars.
- **GlobalMap event overlay** — Map now shows event cluster data: countries
  with active events get highlighted borders, tooltips show event counts and
  risk scores.
- **MonitoringDashboard layout update** — Bottom row now includes 4 panels:
  Event Clusters, Burst Timeline, Active Narratives, and Country Risk Index.
- **49 new Sprint 7 tests** across 3 test files:
  - `test_event_clustering.py` — 12 tests (classification, cluster creation,
    edge cases)
  - `test_burst_detection.py` — 14 tests (z-score, hourly frequencies, spike
    detection)
  - `test_narrative_risk.py` — 23 tests (all 4 risk signals, composite score,
    edge cases)
  - `test_events_api.py` — Events API endpoint integration tests

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
