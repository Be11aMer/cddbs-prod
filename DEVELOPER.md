# CDDBS Developer Documentation

> **Version:** 2026.03 (first production release)
> **Last updated:** 2026-03-11

This is the central developer reference for the **Cyber Disinformation Detection Briefing System (CDDBS)**. It covers architecture, every module, every API endpoint, data models, pipeline flows, configuration, deployment, testing, and contribution guidelines. **This document must be updated whenever the application changes.**

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Directory Structure](#3-directory-structure)
4. [Backend Modules](#4-backend-modules)
5. [API Reference](#5-api-reference)
6. [Data Models](#6-data-models)
7. [Pipeline Flows](#7-pipeline-flows)
8. [Frontend](#8-frontend)
9. [Configuration](#9-configuration)
10. [Deployment](#10-deployment)
11. [Testing](#11-testing)
12. [CI/CD](#12-cicd)
13. [Branching Strategy](#13-branching-strategy)
14. [Contributor Guide](#14-contributor-guide)

---

## 1. Project Overview

CDDBS is an AI-powered counter-disinformation analysis platform. It ingests news articles and social media content, runs them through an LLM (Google Gemini) analysis pipeline, and produces structured intelligence briefings scored against a quality rubric. It detects alignment with known disinformation narratives and provides a monitoring dashboard for analysts.

### Core capabilities

| Capability | Description |
|---|---|
| Outlet analysis | Fetch articles from a news outlet via SerpAPI, analyze with Gemini, produce a 7-section intelligence briefing |
| Quality scoring | Score every briefing against a 70-point, 7-dimension rubric (structural completeness, attribution, confidence, evidence, rigor, actionability, readability) |
| Narrative matching | Match briefing and article text against a database of 50+ known disinformation narratives |
| Social media analysis | Analyze Twitter/X accounts and Telegram channels using the same 7-section briefing format |
| Topic mode | Discover which outlets are pushing narratives on a specific topic by comparing their coverage to a neutral wire-service baseline |
| Event intelligence | Continuously ingest articles from RSS feeds and GDELT, cluster into events, detect keyword frequency bursts, score narrative risk |
| Monitoring dashboard | Real-time dashboard with global map, intel feed, activity timeline, narrative charts, event clusters, outlet network graph |
| JSON export | Download complete analysis results as a structured JSON archive |
| Metrics | Operational metrics including success rate, average quality, throughput |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React/Vite)                  │
│  MUI + Recharts + React Simple Maps + TanStack Query        │
│  Port 5173 (dev) / 80 (production via Nginx)                │
├─────────────────────────────────────────────────────────────┤
│                      FastAPI Backend                        │
│  Port 8000 — uvicorn with --reload in dev                   │
│                                                             │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────┐        │
│  │ Analysis  │  │ Topic Mode   │  │ Social Media   │        │
│  │ Pipeline  │  │ Pipeline     │  │ Pipeline       │        │
│  └─────┬────┘  └──────┬───────┘  └───────┬────────┘        │
│        │               │                  │                 │
│  ┌─────▼───────────────▼──────────────────▼─────┐           │
│  │              Gemini LLM (google-genai)        │           │
│  └───────────────────────────────────────────────┘           │
│                                                             │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐       │
│  │ Quality      │  │ Narrative   │  │ Collectors   │       │
│  │ Scorer       │  │ Matcher     │  │ (RSS/GDELT)  │       │
│  └──────────────┘  └─────────────┘  └──────────────┘       │
├─────────────────────────────────────────────────────────────┤
│                    PostgreSQL 15                             │
│  12 tables — see Data Models section                        │
└─────────────────────────────────────────────────────────────┘
```

**Key backend dependencies:** FastAPI, uvicorn, SQLAlchemy, psycopg2-binary, alembic, python-dotenv, requests, httpx, google-genai, feedparser, scikit-learn.

### Request flow (outlet analysis)

1. `POST /analysis-runs` creates a `Report` row with status "pending"
2. A background task calls `run_pipeline()` in `orchestrator.py`
3. `fetch_articles()` retrieves articles via SerpAPI
4. `get_consolidated_prompt()` builds the user prompt; `get_system_prompt()` loads `system_prompt_v1.3.txt`
5. `call_gemini()` sends the prompt to Gemini 2.5 Flash with `response_mime_type="application/json"`
6. Response is parsed into individual analyses + structured briefing
7. `score_briefing()` runs the 70-point quality rubric
8. `match_narratives_from_report()` checks against known narratives
9. Results are persisted: `Report`, `Article`, `Briefing`, `NarrativeMatch` rows
10. Frontend polls `GET /analysis-runs/{id}` until status = "completed"

---

## 3. Directory Structure

```
cddbs-prod/
├── .github/workflows/ci.yml    # CI pipeline
├── docker-compose.yml           # PostgreSQL + web + frontend
├── Dockerfile                   # Python 3.11 slim backend image
├── Makefile                     # build, up, test shortcuts
├── requirements.txt             # Python dependencies
├── CHANGELOG.md                 # Release notes
├── DEVELOPER.md                 # This file
│
├── src/cddbs/
│   ├── __init__.py
│   ├── config.py                # Settings from environment variables
│   ├── database.py              # SQLAlchemy engine, SessionLocal, Base
│   ├── models.py                # 11 ORM models
│   ├── quality.py               # 7-dimension quality scorer
│   ├── narratives.py            # Narrative matching engine
│   ├── adapters.py              # Twitter/Telegram data normalization
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py              # FastAPI app — all 31 endpoints
│   │
│   ├── pipeline/
│   │   ├── orchestrator.py      # Main outlet analysis pipeline
│   │   ├── fetch.py             # SerpAPI article fetching
│   │   ├── prompt_templates.py  # Gemini prompt construction
│   │   ├── analyze.py           # Article analysis helpers
│   │   ├── summarize.py         # Text summarization
│   │   ├── translate.py         # Translation utilities
│   │   ├── digest.py            # Digest generation
│   │   ├── social_media_pipeline.py  # Twitter/Telegram pipeline
│   │   ├── topic_pipeline.py    # Topic mode pipeline
│   │   ├── topic_prompt_templates.py # Topic mode prompts
│   │   ├── deduplication.py     # Article deduplication
│   │   ├── event_clustering.py  # TF-IDF based event clustering
│   │   ├── burst_detection.py   # Keyword frequency spike detection
│   │   └── narrative_risk.py    # Per-cluster narrative risk scoring
│   │
│   ├── collectors/
│   │   ├── base.py              # BaseCollector abstract class
│   │   ├── rss.py               # RSS feed collector
│   │   ├── gdelt.py             # GDELT API collector
│   │   └── manager.py           # CollectorManager — background loop
│   │
│   ├── utils/
│   │   ├── genai_client.py      # Gemini API wrapper
│   │   └── system_prompt.py     # System prompt loader
│   │
│   └── data/
│       ├── system_prompt_v1.3.txt   # LLM system instructions
│       ├── known_narratives.json    # 50+ known disinformation narratives
│       └── briefing_v1.json         # Briefing JSON schema
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx             # React entry point
│       ├── App.tsx              # Router and layout
│       ├── api.ts               # API client (axios + typed functions)
│       ├── store.ts             # Redux store
│       ├── theme.tsx            # MUI theme
│       ├── hooks.ts             # Custom hooks
│       ├── components/          # 30 components (see Frontend section)
│       ├── contexts/            # NotificationContext etc.
│       ├── hooks/               # Additional hooks
│       ├── slices/              # Redux slices
│       └── utils/               # Frontend utilities
│
└── tests/
    ├── conftest.py              # Shared fixtures (in-memory SQLite)
    ├── test_adapters.py         # Twitter/Telegram adapter tests
    ├── test_api.py              # FastAPI endpoint tests
    ├── test_api_helpers.py      # API helper function tests
    ├── test_database.py         # Database model tests
    ├── test_fetch.py            # Article fetch tests
    ├── test_models.py           # ORM model tests
    ├── test_narratives.py       # Narrative matching tests
    ├── test_orchestrator.py     # Pipeline orchestrator tests
    ├── test_pipeline.py         # End-to-end pipeline tests
    ├── test_quality.py          # Quality scorer tests
    └── test_schema.py           # Schema validation tests
```

---

## 4. Backend Modules

### 4.1 `config.py` — Settings

All configuration is read from environment variables via `python-dotenv`.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://admin:admin@db:5432/cddbs` | PostgreSQL connection string |
| `SERPAPI_KEY` | (none) | SerpAPI key for article search |
| `GOOGLE_API_KEY` | (none) | Google AI API key for Gemini |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model identifier |
| `ARTICLE_LIMIT` | `3` | Default articles per analysis |
| `ALLOWED_ORIGINS` | `*` | CORS allowed origins (comma-separated) |
| `DB_POOL_SIZE` | `5` | SQLAlchemy connection pool size |
| `DB_MAX_OVERFLOW` | `10` | SQLAlchemy max overflow connections |
| `GDELT_PROXY_URL` | (none) | Cloudflare Worker URL to proxy GDELT requests (bypasses datacenter IP blocks) |
| `TWITTER_BEARER_TOKEN` | (none) | Twitter API v2 bearer token |
| `TWITTER_API_KEY` | (none) | Twitter API consumer key |
| `TWITTER_API_SECRET` | (none) | Twitter API consumer secret |
| `TELEGRAM_BOT_TOKEN` | (none) | Telegram Bot API token |

### 4.2 `database.py` — Database Engine

Creates the SQLAlchemy engine and `SessionLocal` factory. Uses `pool_pre_ping=True` for connection health checks. `init_db()` calls `Base.metadata.create_all()` on startup to auto-create tables.

### 4.3 `models.py` — ORM Models

11 SQLAlchemy models — see [Data Models](#6-data-models) for full schema.

### 4.4 `quality.py` — Quality Scorer

Implements the 7-dimension, 70-point quality rubric. Each dimension scores 0-10:

1. **Structural Completeness** — Are all 7 briefing sections present?
2. **Attribution Quality** — Are claims backed by typed evidence references?
3. **Confidence Signaling** — Are confidence levels (high/moderate/low) used consistently?
4. **Evidence Presentation** — Is evidence diverse, quantitative, and well-structured?
5. **Analytical Rigor** — Are scope, limitations, and bias acknowledged?
6. **Actionability** — Is the briefing useful to an analyst (clear findings, prioritization)?
7. **Readability** — Is the format consistent and the summary well-sized?

**Rating thresholds:** >=60 Excellent, >=50 Good, >=40 Acceptable, >=30 Poor, <30 Failing.

**Key functions:**
- `score_briefing(payload) -> dict` — Main entry point. Accepts full Gemini response or standalone briefing.
- `format_scorecard(scorecard, briefing_id) -> str` — Human-readable text output.

The scorer handles both legacy format (inline evidence) and v1.3 format (flat evidence fields). Helper functions like `_get_findings_evidence()`, `_get_confidence_factors()`, and `_get_limitations_structured()` normalize across formats.

### 4.5 `narratives.py` — Narrative Matcher

Matches text against `data/known_narratives.json` using keyword counting.

**Key functions:**
- `match_narratives(text, threshold=2) -> list` — Returns matched narratives with confidence levels (high: 5+ keywords, moderate: 3-4, low: 2).
- `match_narratives_from_report(report_text, articles) -> list` — Combines matches from report text and individual articles, deduplicating by narrative ID and keeping the strongest match.
- `get_all_narratives() -> list` — Returns the full narrative database for the `/narratives` endpoint.

**Narrative database structure:**
```json
{
  "categories": [
    {
      "id": "anti_nato",
      "name": "Anti-NATO / Western Alliance",
      "narratives": [
        {
          "id": "anti_nato_001",
          "name": "NATO expansion threatens Russia",
          "keywords": ["NATO expansion", "encirclement", ...],
          "description": "...",
          "frequency": "high",
          "active": true
        }
      ]
    }
  ]
}
```

### 4.6 `adapters.py` — Platform Adapters

Normalizes platform-specific data into a common `BriefingInput` format.

**Data classes:**
- `PostData` — Normalized post/message (text, timestamp, engagement, amplification flag)
- `ProfileData` — Account/channel profile (handle, platform, followers, verified, etc.)
- `BriefingInput` — Container: profile + posts + collection period

**Adapter classes:**
- `TwitterAdapter` — Converts Twitter API v2 response to `BriefingInput`
- `TelegramAdapter` — Converts Telegram Bot API response to `BriefingInput`

### 4.7 `utils/genai_client.py` — Gemini Client

`call_gemini(prompt, api_key=None) -> str` wraps the Google GenAI SDK:
- Uses `gemini-2.5-flash` model
- Temperature: 0.1 (near-deterministic)
- Response format: `application/json`
- System instruction loaded from `system_prompt_v1.3.txt`

### 4.8 `pipeline/orchestrator.py` — Main Pipeline

`run_pipeline()` is the core analysis function:

1. Fetch articles via `fetch_articles()` (SerpAPI)
2. Build prompt via `get_consolidated_prompt()`
3. Call Gemini and parse JSON from response (handles markdown code blocks, raw JSON, and fallback)
4. Create/update `Report`, create `Article` rows
5. Run `score_briefing()` → create `Briefing` row
6. Run `match_narratives_from_report()` → create `NarrativeMatch` rows
7. Commit all changes

**Error handling:** Quality scoring and narrative matching are non-fatal — if they fail, the analysis still completes.

### 4.9 `pipeline/social_media_pipeline.py` — Social Media Pipeline

`run_social_media_pipeline()` follows the same pattern as the outlet pipeline but:
- Uses `get_social_media_prompt()` instead of `get_consolidated_prompt()`
- Input is platform-normalized `BriefingInput` from adapters
- Handles Twitter-specific (retweet ratio, follower/following) and Telegram-specific (forwarding, subscriber) metrics

`fetch_twitter_data(handle)` and `fetch_telegram_data(handle)` are async functions that call platform APIs.

### 4.10 `pipeline/topic_pipeline.py` — Topic Mode Pipeline

`run_topic_pipeline()` discovers which outlets are pushing narratives on a topic and detects coordinated narrative pushing:

1. **Baseline phase:** Fetch articles from reference outlets (Reuters, BBC, AP, AFP) → ask Gemini for a neutral baseline summary
2. **Discovery phase:** Broad SerpAPI search → identify top non-reference outlets by frequency (excludes 30+ known mainstream/reference domains)
3. **Comparative phase:** For each discovered outlet, fetch articles → ask Gemini to compare coverage against baseline → score divergence (0-100) and amplification signal (low/medium/high)
4. **Persistence:** Results stored in `TopicRun` and `TopicOutletResult` rows

### 4.11 `collectors/` — Event Intelligence Collectors

Background article ingestion running every 180 seconds via `CollectorManager`.

**`base.py`:**
- `RawArticleData` dataclass with `url_hash` property (SHA-256) for deduplication
- `BaseCollector` ABC with `collect() -> list[RawArticleData]`

**`rss.py` — RSSCollector:**
- Fetches from curated RSS feeds of known outlets using `feedparser`
- Handles various feed formats (Atom, RSS 2.0)

**`gdelt.py` — GDELTCollector:**
- Queries the GDELT API for recent articles
- Filters by theme/geography relevant to disinformation monitoring

**`manager.py` — CollectorManager:**
- Manages all collectors, tracks per-collector health status
- `start_background(interval_seconds)` runs a perpetual async loop
- After ingestion: runs deduplication → event clustering (TF-IDF + cosine similarity) → burst detection (z-score on keyword frequency) → narrative risk scoring
- Started in FastAPI `lifespan` context manager, stopped on shutdown

### 4.12 Processing pipeline modules

- **`deduplication.py`** — URL-hash and content-similarity based dedup
- **`event_clustering.py`** — TF-IDF vectorization + cosine similarity clustering
- **`burst_detection.py`** — Keyword frequency z-score spike detection (rolling 24h baseline vs. last 1h)
- **`narrative_risk.py`** — Per-cluster risk scoring based on narrative keyword overlap

---

## 5. API Reference

Base URL: `/api` (proxied by Vite in development)

### 5.1 Analysis Runs

| Method | Path | Description |
|---|---|---|
| `POST` | `/analysis-runs` | Create a new outlet analysis (runs in background) |
| `GET` | `/analysis-runs` | List all analysis runs (lightweight) |
| `GET` | `/analysis-runs/{report_id}` | Full analysis details with articles and briefing |
| `GET` | `/analysis-runs/{report_id}/quality` | Quality scorecard for a run |
| `GET` | `/analysis-runs/{report_id}/narratives` | Matched narratives for a run |
| `GET` | `/analysis-runs/{report_id}/export` | Download full analysis as JSON |

**POST `/analysis-runs` request body:**
```json
{
  "outlet": "RT News",
  "url": "https://rt.com",
  "country": "Russia",
  "num_articles": 5,
  "date_filter": "m",
  "serpapi_key": "optional-override",
  "google_api_key": "optional-override"
}
```

**GET `/analysis-runs/{id}` response includes:**
- `meta` — Outlet name, URL, country, analysis date, articles analyzed
- `final_report` — Markdown text briefing (backward-compatible)
- `structured_briefing` — 7-section JSON briefing object
- `articles` — List of articles with per-article analysis (propaganda score, sentiment, framing, key claims, etc.)
- `status` — "queued" | "running" | "completed" | "failed"

### 5.2 Topic Mode

| Method | Path | Description |
|---|---|---|
| `POST` | `/topic-runs` | Create a topic analysis run |
| `GET` | `/topic-runs` | List all topic runs |
| `GET` | `/topic-runs/{id}` | Full topic run with per-outlet divergence results |

**POST `/topic-runs` request body:**
```json
{
  "topic": "NATO expansion eastward",
  "num_outlets": 5,
  "date_filter": "m"
}
```

### 5.3 Social Media

| Method | Path | Description |
|---|---|---|
| `POST` | `/social-media/analyze` | Analyze a Twitter/Telegram account |

**Request body:**
```json
{
  "platform": "twitter",
  "handle": "@rt_com"
}
```

### 5.4 Event Intelligence

| Method | Path | Description |
|---|---|---|
| `GET` | `/events` | List event clusters (filterable by type, status, risk, country) |
| `GET` | `/events/{id}` | Event cluster details with articles |
| `GET` | `/events/map` | Events grouped by country for map visualization |
| `GET` | `/events/bursts` | Narrative burst detections (keyword frequency spikes) |

### 5.5 Statistics & Monitoring

| Method | Path | Description |
|---|---|---|
| `GET` | `/stats/global` | Aggregate platform statistics |
| `GET` | `/stats/by-country` | Per-country risk and analysis counts |
| `GET` | `/stats/narrative-trends` | Top narratives by frequency |
| `GET` | `/stats/narrative-frequency` | Narrative frequency with confidence breakdown |
| `GET` | `/stats/activity-timeline` | Hourly article ingestion counts |
| `GET` | `/stats/outlet-network` | Outlet relationship network graph data |
| `GET` | `/stats/quality-trends` | Quality scores over time per outlet |
| `GET` | `/monitoring/feed` | Recent articles from collector pipeline |

### 5.6 Operational

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Root — returns `{"service": "cddbs", "status": "ok"}` |
| `GET` | `/health` | Health check (includes DB connectivity) |
| `GET` | `/metrics` | Operational metrics (success rate, avg quality, throughput) |
| `GET` | `/api-status` | External API key configuration status |
| `GET` | `/collector/status` | Collector health status |
| `GET` | `/narratives` | Full known narratives database |

### 5.7 Feedback

| Method | Path | Description |
|---|---|---|
| `POST` | `/feedback` | Submit tester feedback |
| `GET` | `/feedback` | List all feedback entries |

### 5.8 Webhooks

| Method | Path | Description |
|---|---|---|
| `POST` | `/webhooks` | Register a new webhook endpoint |
| `GET` | `/webhooks` | List all registered webhooks |
| `DELETE` | `/webhooks/{id}` | Unregister a webhook |
| `POST` | `/webhooks/test/{id}` | Send a test payload to a webhook |

**POST `/webhooks` request body:**
```json
{
  "url": "https://example.com/hook",
  "events": ["pipeline_failure", "narrative_burst"],
  "secret": "optional-shared-secret"
}
```

---

## 6. Data Models

### 6.1 Entity Relationship Diagram

```
Outlet 1──* Article *──1 Report
                            │
                    ┌───────┼──────────┐
                    │       │          │
                 Briefing   │    NarrativeMatch
                  (1:1)     │       (*:1)
                            │
                       TopicRun 1──* TopicOutletResult

RawArticle *──1 EventCluster
                     │
              NarrativeBurst

WebhookConfig (standalone)
```

### 6.2 Table Definitions

#### `outlets`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| name | String UNIQUE | Outlet name |
| url | String | Outlet URL |

#### `articles`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| outlet_id | FK → outlets | |
| report_id | FK → reports | |
| title | String | |
| link | String | |
| snippet | Text | |
| date | String | |
| meta | JSON | Contains `{"analysis": {...}}` with per-article scores |
| full_text | Text | |
| created_at | DateTime | |

#### `reports`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| outlet | String | Outlet name |
| country | String | |
| final_report | Text | Markdown briefing text |
| raw_response | Text | Raw Gemini response |
| data | JSON | Metadata: status, url, quality_score, narrative_matches_count |
| created_at | DateTime | |

#### `briefings`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| report_id | FK → reports (UNIQUE) | One briefing per report |
| briefing_json | JSON | Full Gemini response payload |
| quality_score | Integer | 0-70 |
| quality_rating | String | Excellent/Good/Acceptable/Poor/Failing |
| quality_details | JSON | Full scorecard with per-dimension breakdown |
| prompt_version | String | Default "v1.3" |
| created_at | DateTime | |

#### `narrative_matches`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| report_id | FK → reports | |
| narrative_id | String | e.g. "anti_nato_001" |
| narrative_name | String | |
| category | String | |
| confidence | String | high/moderate/low |
| matched_keywords | JSON | List of matched keywords |
| match_count | Integer | |
| created_at | DateTime | |

#### `topic_runs`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| topic | String | Search topic |
| num_outlets | Integer | Default 5 |
| date_filter | String | h/d/w/m/y |
| status | String | pending/running/completed/failed |
| baseline_summary | Text | Gemini neutral baseline |
| baseline_raw | Text | Raw Gemini JSON |
| coordination_signal | Float | 0.0-1.0 — fraction of outlets in coordinated cluster |
| coordination_detail | JSON | {shared_techniques, coordinated_outlets, counts} |
| created_at | DateTime | |
| completed_at | DateTime | |
| error | Text | |

#### `topic_outlet_results`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| topic_run_id | FK → topic_runs | |
| outlet_name | String | |
| outlet_domain | String | |
| articles_analyzed | Integer | |
| divergence_score | Integer | 0-100 |
| amplification_signal | String | low/medium/high |
| propaganda_techniques | JSON | List of technique names |
| framing_summary | Text | |
| divergence_explanation | Text | |
| key_claims | JSON | Specific claims made by outlet not in baseline |
| omissions | JSON | Key baseline facts omitted by outlet |
| gemini_raw | Text | |
| article_links | JSON | [{title, url, date}] |
| created_at | DateTime | |

#### `feedback`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| tester_name | String | |
| tester_role | String | analyst/developer/researcher/other |
| overall_rating | Integer | 1-5 |
| accuracy_rating | Integer | 1-5 |
| usability_rating | Integer | 1-5 |
| bugs_encountered | Text | |
| misleading_outputs | Text | |
| missing_features | Text | |
| ux_pain_points | Text | |
| professional_concerns | Text | |
| would_recommend | String | yes/no/maybe |
| additional_comments | Text | |
| created_at | DateTime | |

#### `raw_articles`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| url_hash | String(64) UNIQUE | SHA-256 of normalized URL |
| title | String | |
| url | String | |
| content | Text | |
| source_name | String | |
| source_domain | String | Indexed |
| source_type | String | rss/gdelt/news_api |
| published_at | DateTime | |
| language | String(10) | |
| country | String(100) | |
| raw_meta | JSON | |
| cluster_id | FK → event_clusters | |
| is_duplicate | Boolean | Default False |
| duplicate_of | FK → raw_articles | |
| created_at | DateTime | |

#### `event_clusters`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| title | String | Generated cluster title |
| event_type | String | conflict/protest/diplomacy/disaster/cyber/info_warfare |
| countries | JSON | ["Ukraine", "Russia"] |
| entities | JSON | {people: [], orgs: [], locations: []} |
| keywords | JSON | |
| first_seen | DateTime | |
| last_seen | DateTime | |
| article_count | Integer | |
| source_count | Integer | |
| burst_score | Float | |
| narrative_risk_score | Float | |
| status | String | active/declining/resolved |
| created_at | DateTime | |

#### `narrative_bursts`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| keyword | String | Indexed |
| baseline_frequency | Float | Articles/hour (rolling 24h avg) |
| current_frequency | Float | Articles/hour (last 1h) |
| z_score | Float | |
| cluster_id | FK → event_clusters | |
| detected_at | DateTime | |
| resolved_at | DateTime | Null = still active |

#### `webhook_configs`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| url | String | Webhook delivery URL |
| events | JSON | List of event types to subscribe to |
| secret | String | Optional shared secret for HMAC signing |
| active | Boolean | Default true |
| created_at | DateTime | |
| last_triggered_at | DateTime | Null if never fired |
| failure_count | Integer | Consecutive delivery failures |

---

## 7. Pipeline Flows

### 7.1 Outlet Analysis Flow

```
User → POST /analysis-runs
  │
  ├─ Create Report (status: pending)
  ├─ Background task:
  │   ├─ fetch_articles(outlet, country, SerpAPI)
  │   ├─ get_consolidated_prompt(outlet, country, articles)
  │   ├─ call_gemini(prompt)  →  JSON response
  │   ├─ Parse: individual_analyses + structured_briefing + final_briefing
  │   ├─ Persist: Report.data, Report.final_report, Article rows
  │   ├─ score_briefing(payload) → Briefing row
  │   └─ match_narratives_from_report() → NarrativeMatch rows
  │
  └─ Frontend polls GET /analysis-runs/{id}
```

### 7.2 Event Intelligence Flow

```
CollectorManager (every 180s)
  │
  ├─ RSSCollector.collect()   → [RawArticleData]
  ├─ GDELTCollector.collect() → [RawArticleData]
  │
  ├─ Persist to raw_articles (url_hash dedup)
  ├─ Deduplication (content similarity)
  ├─ Event clustering (TF-IDF + cosine similarity)
  │   └─ Create/update EventCluster rows
  ├─ Burst detection (z-score on keyword frequency)
  │   └─ Create NarrativeBurst rows
  └─ Narrative risk scoring (per-cluster)
      └─ Update EventCluster.narrative_risk_score
```

### 7.3 Topic Mode Flow

```
User → POST /topic-runs
  │
  ├─ Create TopicRun (status: pending)
  ├─ Background task:
  │   ├─ Fetch baseline articles (Reuters, BBC, AP, AFP)
  │   ├─ Gemini: generate neutral baseline summary
  │   ├─ Broad SerpAPI search → discover non-reference outlets
  │   ├─ For each outlet (up to num_outlets):
  │   │   ├─ Fetch outlet articles
  │   │   ├─ Gemini: compare vs baseline
  │   │   └─ Persist TopicOutletResult (divergence_score, etc.)
  │   └─ Mark TopicRun completed
  │
  └─ Frontend polls GET /topic-runs/{id}
```

### 7.4 Briefing JSON Structure

The Gemini response produces this 7-section structure:

```json
{
  "individual_analyses": [...],
  "tldr_summary": "2-3 sentence summary",
  "structured_briefing": {
    "executive_summary": "3-5 sentence intelligence-grade summary",
    "key_findings": [
      {
        "finding": "Specific finding statement",
        "confidence": "high|moderate|low",
        "evidence_type": "PATTERN|EXTERNAL|NETWORK|POST|METADATA",
        "evidence": "Reference with metrics"
      }
    ],
    "subject_profile": {
      "name": "outlet",
      "platform": "web|twitter|telegram",
      "country": "...",
      "articles_analyzed": 5,
      "type": "State media|Independent|Proxy|Unknown"
    },
    "narrative_analysis": {
      "primary_narratives": [...],
      "behavioral_indicators": [...],
      "network_context": [...],
      "source_attribution": {
        "role": "Official State Media|Proxy|Deniable|Authentic|Unknown",
        "content_origin": "...",
        "amplification_chain": "..."
      }
    },
    "confidence_assessment": {
      "overall": "high|moderate|low",
      "factors": [
        {"factor": "Data Completeness", "level": "...", "notes": "..."},
        {"factor": "Source Reliability", "level": "...", "notes": "..."},
        {"factor": "Analytical Consistency", "level": "...", "notes": "..."},
        {"factor": "Corroboration", "level": "...", "notes": "..."}
      ]
    },
    "limitations": ["..."],
    "methodology": {
      "data_collection": "...",
      "articles_analyzed": 5,
      "analysis_model": "gemini-2.5-flash",
      "prompt_version": "v1.3"
    }
  },
  "final_briefing": "Backward-compatible text briefing"
}
```

---

## 8. Frontend

### 8.1 Stack

- **React 18** with TypeScript
- **Vite** for dev server and build
- **MUI 6** (Material UI) for components
- **Recharts** for charts (bar, line, area, radar)
- **React Simple Maps** for the world map
- **TanStack Query** for server state
- **Redux Toolkit** for client state
- **Axios** for HTTP

### 8.2 Key Components

| Component | File | Purpose |
|---|---|---|
| `App` | `App.tsx` | Root layout, routing, tab navigation |
| `MonitoringDashboard` | `MonitoringDashboard.tsx` | Main dashboard with 12 sub-sections |
| `ReportViewDialog` | `ReportViewDialog.tsx` | Full-screen briefing viewer |
| `NewAnalysisDialog` | `NewAnalysisDialog.tsx` | Create new analysis form |
| `RunsTable` | `RunsTable.tsx` | Analysis history table |
| `RunDetail` | `RunDetail.tsx` | Inline run detail view |
| `TopicRunsTable` | `TopicRunsTable.tsx` | Topic runs history |
| `TopicRunDetail` | `TopicRunDetail.tsx` | Topic run result viewer |
| `GlobalMap` | `GlobalMap.tsx` | World map with country risk colors |
| `IntelFeed` | `IntelFeed.tsx` | Real-time article feed |
| `ActivityTimeline` | `ActivityTimeline.tsx` | Hourly ingestion chart |
| `NarrativeBarChart` | `NarrativeBarChart.tsx` | Top narratives bar chart |
| `NarrativeTrendPanel` | `NarrativeTrendPanel.tsx` | Narrative trends over time |
| `OutletNetworkGraph` | `OutletNetworkGraph.tsx` | Outlet relationship graph |
| `EventClusterPanel` | `EventClusterPanel.tsx` | Active event clusters with detail dialog |
| `BurstTimeline` | `BurstTimeline.tsx` | Narrative burst keyword frequency spikes (z-score) |
| `CountryRiskIndex` | `CountryRiskIndex.tsx` | Country risk ranking |
| `QualityRadarChart` | `QualityRadarChart.tsx` | 7-dimension quality radar |
| `QualityBadge` | `QualityBadge.tsx` | Quality rating badge |
| `NarrativeTags` | `NarrativeTags.tsx` | Colored narrative match tags |
| `AnnotatedArticleCards` | `AnnotatedArticleCards.tsx` | Per-article analysis cards |
| `CollectorStatusBar` | `CollectorStatusBar.tsx` | Collector health indicators |
| `MetricCard` | `MetricCard.tsx` | Single metric stat card |
| `FeedbackDialog` | `FeedbackDialog.tsx` | Tester feedback form |
| `SettingsDialog` | `SettingsDialog.tsx` | API key configuration |
| `ApiStatusInfo` | `ApiStatusInfo.tsx` | API configuration status |
| `StatusIndicator` | `StatusIndicator.tsx` | Status dot indicator |
| `StatusDistributionChart` | `StatusDistributionChart.tsx` | Run status pie chart |
| `Skeletons` | `Skeletons.tsx` | Loading skeleton components |
| `ColdStartNotice` | `ColdStartNotice.tsx` | Cold start warning banner |
| `KeyboardShortcutsDialog` | `KeyboardShortcutsDialog.tsx` | Keyboard shortcuts help |
| `TestGuideDialog` | `TestGuideDialog.tsx` | Testing guide for testers |

### 8.3 API Client (`api.ts`)

All API calls are in `frontend/src/api.ts` with full TypeScript interfaces:
- Typed request/response interfaces for every endpoint
- `exportAnalysisRun(reportId)` triggers a browser download of the JSON export
- `fetchMetrics()` returns platform operational metrics
- `fetchQualityTrends(outlet?)` returns quality score time-series data

### 8.4 State Management

- **TanStack Query** handles all server state (automatic caching, refetching, polling)
- **Redux Toolkit** used for UI state (selected tab, dialog open states)
- Polling is used for in-progress analysis runs (via `refetchInterval`)

---

## 9. Configuration

### 9.1 Required Environment Variables

For basic functionality:
```env
DATABASE_URL=postgresql+psycopg2://admin:admin@db:5432/cddbs
SERPAPI_KEY=your_serpapi_key
GOOGLE_API_KEY=your_google_api_key
```

For social media analysis:
```env
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

Optional:
```env
ALLOWED_ORIGINS=http://localhost:5173,https://your-domain.com
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
GEMINI_MODEL=gemini-2.5-flash
ARTICLE_LIMIT=3
```

### 9.2 Render Deployment

The project includes `render.yaml` for Render deployments. Set environment variables in the Render dashboard.

---

## 10. Deployment

### 10.1 Docker Compose (Development)

```bash
# Start all services
docker-compose up --build

# Or use the Makefile
make up
```

Services:
- `db` — PostgreSQL 15 on port 5432
- `web` — FastAPI on port 8000 (with `--reload`)
- `frontend` — Vite on port 5173

### 10.2 Docker (Production)

The `Dockerfile` builds a Python 3.11 slim image:
- Installs `requirements.txt`
- Sets `PYTHONPATH=/app`
- Runs `uvicorn src.cddbs.api.main:app --host 0.0.0.0 --port 8000`
- Includes `--timeout-keep-alive 75` and `--timeout-graceful-shutdown 30` for long-running analysis requests

The frontend has its own `Dockerfile` (in `frontend/`) that builds the Vite app and serves via Nginx.

### 10.3 Database Initialization

Tables are auto-created on startup via `init_db()` in the FastAPI lifespan. No manual migration needed for fresh deployments. For schema changes, Alembic is available in `requirements.txt` but migrations are not yet configured — add them if schema changes become frequent.

---

## 11. Testing

### 11.1 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/cddbs --cov-report=term-missing

# Run a specific file
pytest tests/test_quality.py -v

# Using Makefile
make test
```

### 11.2 Test Architecture

Tests use an **in-memory SQLite database** (configured in `tests/conftest.py`) to avoid needing PostgreSQL for test runs. Key fixtures:

- `db_session` — Fresh SQLAlchemy session per test
- `client` — FastAPI `TestClient` with overridden DB dependency

### 11.3 Test Coverage

| Test File | What It Covers |
|---|---|
| `test_api.py` | FastAPI endpoint integration tests |
| `test_api_helpers.py` | Internal API helper functions |
| `test_quality.py` | Quality scoring — all 7 dimensions, edge cases, format normalization |
| `test_narratives.py` | Narrative matching — thresholds, dedup, confidence levels |
| `test_models.py` | ORM model creation and relationships |
| `test_database.py` | Database connectivity and table creation |
| `test_pipeline.py` | End-to-end pipeline with mocked Gemini |
| `test_orchestrator.py` | Pipeline orchestrator logic |
| `test_adapters.py` | Twitter/Telegram adapter normalization |
| `test_schema.py` | Pydantic schema validation |
| `test_fetch.py` | Article fetching |

**Total: 132 test functions across 12 files.**

---

## 12. CI/CD

### GitHub Actions (`.github/workflows/ci.yml`)

Triggered on push/PR to `main`/`master`/`development`. Four jobs:

1. **lint** — Installs `ruff`, runs `ruff check src/ tests/`
2. **test** — Spins up PostgreSQL 15 service, runs `pytest tests/ -v`
3. **docs-drift** — Runs `scripts/check_docs_drift.py` to verify README.md and DEVELOPER.md are in sync with the codebase. Checks API endpoints, database models, environment variables, frontend components, and Python dependencies. **Fails the build if documentation has drifted** — required for EU CRA compliance.
4. **frontend-build** — Installs npm dependencies, runs `npm run build` (type-check + bundle)

### Branch Policy (`.github/workflows/branch-policy.yml`)

Triggered on PRs to `main`/`master`/`development`. Enforces the branching strategy:
- **PRs to `main`:** Only the `development` branch is allowed as source. All other branches are rejected.
- **PRs to `development`:** Warns if the branch is not based on `development`.

See [Branching Strategy](#13-branching-strategy) for full details.

### Secret Scan (`.github/workflows/secret-scan.yml`)

Triggered on push/PR to `main`/`master`/`development`. Runs `scripts/detect_secrets.py` to scan the codebase for hardcoded API keys, tokens, passwords, and credentials. On PRs, also scans the diff for secrets in changed lines. **Fails the build and rejects the PR if any secrets are found.**

---

## 13. Branching Strategy

### 13.1 Overview

This project uses a **two-tier branching model**:

- **`main`** — Production-only. Contains tested, release-ready code. Deployments are made from this branch. **No direct commits or feature branches are allowed from `main`.**
- **`development`** — Active development branch. All feature branches, bugfix branches, and other work branches **must be created from `development`** and merged back into `development`.

```
main  ◄──────────────── (release merges only) ──── development
                                                       │
                                          ┌────────────┼────────────┐
                                          │            │            │
                                     feature/X    bugfix/Y    feature/Z
```

### 13.2 Rules

1. **All new branches must be created from `development`**, never from `main`.
2. **All feature/bugfix PRs must target `development`**, never `main`.
3. **Only `development` can merge into `main`**, via a release PR after testing.
4. **Direct commits to `main` are not allowed** (enforce via GitHub branch protection).
5. **Direct commits to `development` are discouraged** — use feature branches.

### 13.3 Workflow

**Starting new work:**
```bash
git checkout development
git pull origin development
git checkout -b feature/my-feature    # or bugfix/my-bug, chore/my-task
# ... make changes ...
git push -u origin feature/my-feature
# Create PR targeting 'development'
```

**Releasing to production:**
```bash
git checkout development
git pull origin development
# Ensure all tests pass and code is stable
# Create PR: development → main
# After review and merge, main is deployed
```

### 13.4 Enforcement

Branch policy is enforced at three levels:

| Level | Mechanism | What It Does |
|---|---|---|
| **CI** | `.github/workflows/branch-policy.yml` | Fails PRs to `main` from any branch except `development`. Warns on PRs to `development` that are not based on `development`. |
| **Local** | `scripts/install-hooks.sh` (pre-push hook) | Blocks pushing feature branches that were created from `main` instead of `development`. |
| **GitHub** | Branch protection rules (manual setup) | Require PR reviews, require status checks to pass, restrict who can push to `main`. |

**Setting up local enforcement:**
```bash
bash scripts/install-hooks.sh
```

**Recommended GitHub branch protection settings for `main`:**
- Require pull request reviews before merging
- Require status checks to pass (CI, branch-policy)
- Restrict pushes to `main` (no direct pushes)
- Do not allow bypassing the above settings

---

## 14. Contributor Guide

### 14.1 Development Setup

```bash
# Clone and enter the project
git clone <repo-url> && cd cddbs-prod

# Switch to the development branch (all work starts here)
git checkout development

# Install git hooks for branch policy enforcement
bash scripts/install-hooks.sh

# Create a .env file from the template
cp .env.example .env  # edit with your API keys

# Start with Docker
docker-compose up --build

# Or run locally
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://admin:admin@localhost:5432/cddbs
uvicorn src.cddbs.api.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

### 14.2 Adding a New API Endpoint

1. Add Pydantic request/response models in `src/cddbs/api/main.py`
2. Add the endpoint function with `@app.get()` or `@app.post()`
3. Add corresponding TypeScript interface and fetch function in `frontend/src/api.ts`
4. Write tests in `tests/test_api.py`
5. Update this documentation

### 14.3 Adding a New Collector

1. Create `src/cddbs/collectors/my_source.py` extending `BaseCollector`
2. Implement `name`, `source_type`, and `collect()` method
3. Add the collector instance to `CollectorManager.__init__()` in `manager.py`
4. Test by running the application and checking `/collector/status`

### 14.4 Adding a New Narrative

Edit `src/cddbs/data/known_narratives.json`:
```json
{
  "id": "category_nnn",
  "name": "Narrative Name",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "description": "What this narrative promotes",
  "frequency": "high|medium|low",
  "active": true
}
```

The keyword threshold for a match is 2 by default — ensure at least 2 distinctive keywords.

### 14.5 Modifying the Briefing Prompt

The system prompt is in `src/cddbs/data/system_prompt_v1.3.txt`. The user prompt template is in `src/cddbs/pipeline/prompt_templates.py`. If you change the briefing JSON structure:

1. Update `prompt_templates.py`
2. Update `quality.py` scorer to handle new format (add normalization in `_extract_briefing()`)
3. Update frontend `StructuredBriefing` interface in `api.ts`
4. Update `ReportViewDialog.tsx` rendering
5. Bump the prompt version in `Briefing.prompt_version`

### 14.6 Documentation Updates

**This file (`DEVELOPER.md`) is the single source of truth for developer documentation.** Update it whenever you:
- Add/remove an API endpoint
- Add/modify a database model
- Change the pipeline flow
- Add a new module or component
- Change configuration variables
- Modify the deployment process

---

## 15. Sprint 8: Topic Mode Innovations, Supply Chain Security & AI Disclosure

### 15.1 Topic Mode Innovations (v1.8.0)

**Key claims and omissions storage**

The comparative Gemini prompt returns `key_claims_by_outlet` (specific claims made by the outlet that diverge from the neutral baseline) and `omissions` (key facts from the baseline that the outlet omits or downplays). These are now stored in `TopicOutletResult.key_claims` and `TopicOutletResult.omissions` respectively and displayed in the outlet card's expanded detail view.

**Coordination signal detection**

After all per-outlet analyses complete, `run_topic_pipeline()` computes a coordination signal:

1. Identify "high-divergence" outlets: `divergence_score ≥ 60` with non-empty `propaganda_techniques`
2. Build a frequency map of techniques across high-divergence outlets
3. Techniques shared by ≥2 high-divergence outlets are flagged as shared
4. `coordination_signal = len(coordinated_outlets) / len(all_outlets)` (0.0-1.0)
5. `coordination_detail` stores: shared techniques, coordinated outlet list, counts

Signal interpretation:
- `≥ 0.50`: HIGH — strong coordinated narrative pushing signal
- `0.25-0.50`: MODERATE — some coordination possible
- `< 0.25`: LOW — likely independent coverage

This is exposed in `GET /topic-runs/{id}` as `coordination_signal` and `coordination_detail`, and rendered as a `CoordinationBanner` in `TopicRunDetail.tsx`.

### 15.2 AI Provenance & Disclosure (EU AI Act Art. 50)

**`AIMetadata` API schema**

All `GET /analysis-runs/{id}` responses now include an `ai_metadata` object:

```json
{
  "model_id": "gemini-2.5-flash",
  "prompt_version": "v1.3",
  "generated_at": "2026-04-15T10:30:00Z",
  "quality_score": 54,
  "quality_rating": "Good",
  "requires_human_review": true,
  "disclosure": "This content was generated by an AI language model (Google Gemini)..."
}
```

This satisfies EU AI Act Art. 50's machine-readable marking requirement.

**`AIProvenanceCard` component**

`frontend/src/components/AIProvenanceCard.tsx` — tiered disclosure UI:
- **Primary row** (always visible): AI-Generated badge, model chip, quality confidence tier, "REVIEW REQUIRED" indicator
- **Expanded detail** (click to open): model ID, prompt version, generation timestamp, quality score, full legal disclosure text, EU AI Act reference

Design principle: disclosure is permanent (not dismissible), compact, and integrated into the data presentation — avoids the transparency fatigue of modals or alert banners.

Rendered in `ReportViewDialog.tsx` above every briefing. Replaces the prior "Experimental Research MVP" alert.

### 15.3 Supply Chain Security

**SBOM generation (`sbom.yml`)**

Workflow: `.github/workflows/sbom.yml`
- Triggers: push/PR to `main` or `development`
- Tool: `cyclonedx-py environment` — scans the installed Python environment (more accurate than requirements.txt parsing)
- Output: `sbom.json` uploaded as CI artifact, retained 90 days
- Satisfies: EU CRA Art. 13(15) SBOM requirement; CycloneDX format accepted by BSI TR-03183-2

Run locally:
```bash
pip install cyclonedx-bom
cyclonedx-py environment --output-format json --output-file sbom.json
```

**Dependency vulnerability scanning (pip-audit)**

Added to `.github/workflows/ci.yml` as `vulnerability-scan` job:
- Tool: `pip-audit` (Trail of Bits/Google) — queries PyPI Advisory + OSV.dev database
- Behaviour: fails CI if any known vulnerability is found; uploads JSON report as artifact
- Run locally: `pip install pip-audit && pip-audit -r requirements.txt`

**GitHub Actions SHA pinning**

All GitHub Actions references in all workflows are pinned to commit SHA rather than mutable version tags (e.g., `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683` not `@v4`). This mitigates supply chain attacks via compromised Action releases (GhostAction pattern, 2025).

### 15.4 New Components and Files (Sprint 8)

| File | Purpose |
|------|---------|
| `frontend/src/components/AIProvenanceCard.tsx` | EU AI Act Art. 50 disclosure component |
| `tests/test_sprint8_topic_innovations.py` | Sprint 8 test suite (coordination, key claims, AI metadata) |
| `.github/workflows/sbom.yml` | CycloneDX SBOM generation CI workflow |

### 15.5 New API Response Fields (Sprint 8)

| Endpoint | New Field | Type | Notes |
|----------|-----------|------|-------|
| `GET /analysis-runs/{id}` | `ai_metadata` | `AIMetadata` | EU AI Act provenance object |
| `GET /topic-runs/{id}` | `coordination_signal` | `float\|null` | 0.0-1.0 coordination score |
| `GET /topic-runs/{id}` | `coordination_detail` | `object\|null` | Shared techniques + coordinated outlets |
| `GET /topic-runs/{id}` → `outlet_results[]` | `key_claims` | `string[]\|null` | Claims made by outlet |
| `GET /topic-runs/{id}` → `outlet_results[]` | `omissions` | `string[]\|null` | Baseline facts omitted |

---

*End of developer documentation. Keep this file current with every change.*
