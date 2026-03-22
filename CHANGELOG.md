# Changelog

All notable changes to the CDDBS (Cyber Disinformation Detection Briefing System) project
are documented in this file.

## [2026.04.1] - 2026-03-22

### Sprint 8: Topic Mode Innovations, Supply Chain Security & AI Disclosure

This release delivers three areas of innovation on top of the existing Sprint 7 platform.

### Added

- **Topic Mode: Coordinated Narrative Detection** — After all per-outlet analyses complete,
  the pipeline computes a `coordination_signal` (0.0-1.0) by identifying high-divergence
  outlets (score ≥ 60) that share ≥2 propaganda techniques. A `CoordinationBanner` in
  `TopicRunDetail.tsx` surfaces this signal with shared technique labels and outlet names.
  Differentiates CDDBS from single-outlet tools — now detects *networks* of coordinated
  narrative pushing, not just individual divergence.

- **Topic Mode: Key Claims and Omissions** — `GET /topic-runs/{id}` now returns
  `key_claims` (specific claims made by each outlet diverging from the neutral baseline)
  and `omissions` (key baseline facts omitted by the outlet). These were already extracted
  by Gemini but previously discarded. Both are stored in `topic_outlet_results` and
  displayed in the expandable outlet card in `TopicRunDetail.tsx`.

- **AI Provenance Card (`AIProvenanceCard.tsx`)** — EU AI Act Art. 50 compliance. Every
  analysis report now displays a persistent, tiered provenance indicator: compact badge
  (always visible) → expandable detail (model ID, prompt version, generation timestamp,
  quality score, full legal disclosure text). Replaces the generic "Experimental Research
  MVP" alert. Machine-readable `ai_metadata` object added to `GET /analysis-runs/{id}`.

- **SBOM generation CI (`sbom.yml`)** — CycloneDX SBOM (`sbom.json`) generated on every
  push to `main`/`development` using `cyclonedx-py environment` (environment scan, most
  accurate for pip projects). Artifact retained 90 days. Satisfies EU CRA Art. 13(15).

- **Dependency vulnerability scanning** — `pip-audit` added to `ci.yml` as
  `vulnerability-scan` job. Queries PyPI Advisory + OSV.dev. Fails CI on known
  vulnerabilities. JSON report uploaded as artifact. Run locally:
  `pip-audit -r requirements.txt`.

- **GitHub Actions SHA pinning** — All workflow Action references pinned to commit SHA
  rather than mutable version tags. Mitigates supply chain attacks via compromised Action
  releases (GhostAction pattern, 2025). Applies to all 4 workflow files.

- **Sprint 8 tests** (`tests/test_sprint8_topic_innovations.py`) — 10 tests covering:
  key_claims/omissions DB storage, pipeline wiring from Gemini response, coordination
  signal logic, API schema completeness, `ai_metadata` structure validation.

### Changed

- `topic_runs` table: added `coordination_signal` (Float) and `coordination_detail` (JSON)
- `topic_outlet_results` table: added `key_claims` (JSON) and `omissions` (JSON)
- `GET /topic-runs/{id}` response: includes `coordination_signal`, `coordination_detail`,
  and per-outlet `key_claims` + `omissions`
- `GET /analysis-runs/{id}` response: includes `ai_metadata` object
- `TopicRunDetail.tsx`: renders `CoordinationBanner`, key claims list, omissions list
- `ReportViewDialog.tsx`: renders `AIProvenanceCard` instead of generic warning alert
- `requirements.txt`: added `cyclonedx-bom>=4.0` and `pip-audit>=2.7` (CI/dev tools)

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
