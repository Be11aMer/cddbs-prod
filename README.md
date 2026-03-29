# CDDBS (Cyber Disinformation Detection Briefing System)

An AI-powered intelligence briefing system that analyzes media narratives for disinformation patterns. Built with **FastAPI**, **PostgreSQL**, **React/TypeScript**, and **Google Gemini**.

## Live Deployments

| Service | URL |
|---------|-----|
| Frontend (Cloudflare) | [cddbs-frontend.projectsfiae.workers.dev](https://cddbs-frontend.projectsfiae.workers.dev/) |
| Frontend (Render) | [cddbs-frontend.onrender.com](https://cddbs-frontend.onrender.com/) |
| Backend API | [cddbs-api.onrender.com](https://cddbs-api.onrender.com/) |

> Render free tier spins down after inactivity. Visit the backend URL first and wait 30–60s for it to wake.

## Architecture

- **Backend**: FastAPI + PostgreSQL (Neon) + SQLAlchemy + slowapi
- **Frontend**: React 18 + Vite + Material-UI 6 + Redux Toolkit + TypeScript
- **LLM**: Google Gemini 2.5 Flash via google-genai SDK
- **Data Sources**: SerpAPI (Google News), GDELT (via Cloudflare Workers proxy), RSS feeds
- **CI**: GitHub Actions (lint, test, SBOM, pip-audit, dependency scanner, secret scan)

## Quick Start & Development

See [QUICK_START.md](./QUICK_START.md) for detailed setup instructions.

```bash
# Backend
pip install -r requirements.txt
docker compose up --build

# Frontend
cd frontend && npm install && npm run dev
```

## Key Features

| Feature | Description |
|---------|-------------|
| **Outlet Analysis** | Fetch articles via SerpAPI, analyze with Gemini, produce 7-section intelligence briefing |
| **Topic Mode** | Cross-outlet analysis comparing coverage against neutral wire-service baseline |
| **Event Intelligence** | Continuous RSS + GDELT ingestion, TF-IDF clustering, burst detection, narrative risk scoring |
| **Quality Scoring** | 70-point, 7-dimension rubric (structural, attribution, confidence, evidence, rigor, actionability, readability) |
| **Narrative Detection** | Matching against 50+ known disinformation narratives |
| **AI Trust Framework** | Output validation, grounding score (TF-IDF claim verification), confidence calibration |
| **Social Media** | Twitter/X and Telegram account analysis |
| **Monitoring Dashboard** | Global map, intel feed, activity timeline, narrative charts, outlet network graph |
| **Compliance** | EU AI Act Art. 50 provenance, CRA SBOM, `/compliance/evidence` endpoint |

## API Endpoints

### Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analysis-runs` | Create outlet analysis (rate limited: 5/min) |
| `GET` | `/analysis-runs` | List all analysis runs |
| `GET` | `/analysis-runs/{id}` | Full report with briefing, articles, AI metadata |
| `GET` | `/analysis-runs/{id}/quality` | Quality scorecard (70-point rubric) |
| `GET` | `/analysis-runs/{id}/narratives` | Narrative matches |
| `GET` | `/analysis-runs/{id}/export` | JSON export download |

### Topic Mode

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/topic-runs` | Cross-outlet topic analysis (rate limited: 3/min) |
| `GET` | `/topic-runs` | List topic runs |
| `GET` | `/topic-runs/{id}` | Full results with divergence scores, coordination signal |

### Event Intelligence

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/events` | List event clusters (filterable by type, country, risk) |
| `GET` | `/events/{id}` | Event detail with articles |
| `GET` | `/events/map` | Events grouped by country |
| `GET` | `/events/bursts` | Active narrative burst detections |

### Statistics & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/stats/global` | Global metrics (analyses, countries, narratives) |
| `GET` | `/stats/by-country` | Per-country risk index |
| `GET` | `/stats/narrative-trends` | Top narratives by frequency |
| `GET` | `/stats/activity-timeline` | Article ingestion over time |
| `GET` | `/stats/outlet-network` | Outlet relationship graph |
| `GET` | `/monitoring/feed` | Live article feed |

### Other

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/social-media/analyze` | Twitter/Telegram analysis (rate limited: 5/min) |
| `POST` | `/feedback` | Submit tester feedback |
| `GET` | `/compliance/evidence` | Machine-readable compliance snapshot |
| `GET` | `/health` | Health check with DB connectivity |

Full Swagger UI: `http://localhost:8000/docs`

## Project Structure

```
cddbs-prod/
├── src/cddbs/
│   ├── api/
│   │   ├── main.py              # FastAPI app, all endpoints
│   │   └── security_headers.py  # Security headers middleware
│   ├── pipeline/
│   │   ├── orchestrator.py      # Main analysis pipeline
│   │   ├── topic_pipeline.py    # Topic mode (baseline + comparative)
│   │   ├── output_validator.py  # LLM output validation + grounding score
│   │   ├── event_clustering.py  # TF-IDF event clustering
│   │   ├── burst_detection.py   # Z-score burst detection
│   │   └── prompt_templates.py  # Gemini prompt templates
│   ├── collectors/              # RSS + GDELT multi-source ingestion
│   ├── utils/
│   │   ├── input_sanitizer.py   # Prompt injection prevention
│   │   ├── genai_client.py      # Gemini API client
│   │   └── system_prompt.py     # v1.3 system prompt
│   ├── models.py                # SQLAlchemy models (12 tables)
│   ├── config.py                # Configuration (env vars)
│   └── database.py              # DB engine + session
├── frontend/                    # React + TypeScript + MUI
├── tests/                       # 249 tests
├── .github/workflows/           # 7 CI workflows
├── requirements.txt
├── DEVELOPER.md                 # Full developer reference
├── CHANGELOG.md                 # Sprint-by-sprint changelog
└── docker-compose.yml
```

## Security

- **CORS**: Explicit origin list (no wildcards)
- **Rate Limiting**: slowapi on all mutation endpoints
- **Input Sanitization**: Prompt injection prevention on all user inputs
- **Output Validation**: Structural validation of LLM responses before storage
- **Security Headers**: CSP, X-Frame-Options, HSTS on all responses
- **Error Sanitization**: Internal details never leaked to clients
- **Supply Chain**: SHA-pinned Actions, SBOM, pip-audit, custom dependency scanner

OWASP LLM Top 10 coverage: LLM01, LLM02, LLM04, LLM06, LLM09.

See [SECURITY.md](./SECURITY.md) for vulnerability reporting.

## Testing

```bash
# Run all tests
PYTHONPATH=. pytest tests/ -v

# Run Sprint 9 security tests only
PYTHONPATH=. pytest tests/test_sprint9_security.py -v
```

249 tests across 19 test files. CI runs on every push and PR.

## Related

- **cddbs-research** — Research repo with notebooks, sprint docs, compliance logs, and retrospectives

## License

MIT
