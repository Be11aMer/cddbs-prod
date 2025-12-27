# CDDBS (Cybersecurity Disinformation Detection Briefing System)

A professional intelligence briefing system that analyzes media narratives for disinformation patterns. Built with **FastAPI**, **PostgreSQL**, **React**, and **MUI**.

## Quick Start

See [QUICK_START.md](./QUICK_START.md) for detailed setup instructions.

**Important**: You must create a `.env` file with your API keys before running the application. See the Quick Start guide for details.

## Architecture

- **Backend**: FastAPI + PostgreSQL + SQLAlchemy
- **Frontend**: React + Vite + Material-UI + Redux Toolkit
- **Pipeline**: Multi-stage analysis (Fetch → Analyze → Digest → Translate → Summarize)

## API Documentation

The FastAPI backend provides automatic OpenAPI/Swagger documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

#### Analysis Runs

- `POST /analysis-runs` - Create a new analysis run
  - Request body: `{ "outlet": "RT", "url": "rt.com", "country": "Russia", "num_articles": 5 }`
  - Returns: `{ "id": 1, "status": "queued", "message": "Analysis started" }`

- `GET /analysis-runs` - List all analysis runs
  - Returns: Array of run status objects with `id`, `outlet`, `country`, `created_at`, `status`, `message`

- `GET /analysis-runs/{id}` - Get detailed report for a specific run
  - Returns: Complete report with `meta`, `final_report`, and `articles` array

#### Health & Status

- `GET /health` - System health check
- `GET /` - Service status

### Response Models

All endpoints return structured JSON responses:

- **RunStatusResponse**: `{ id, outlet, country, created_at, status, message }`
- **ReportResponse**: `{ meta: { outlet, url, country, analysis_date, articles_analyzed }, final_report: string, articles: ArticleSummary[] }`
- **ArticleSummary**: `{ title, link, date, analysis, digest, translated_digest }`

## Project Structure

```
cddbs/
├── src/cddbs/          # Main Python package
│   ├── api/           # FastAPI application
│   ├── pipeline/      # Analysis pipeline stages
│   ├── models.py      # SQLAlchemy models
│   └── database.py    # Database configuration
├── frontend/          # React frontend application
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── slices/      # Redux slices
│   │   └── api.ts       # API client
│   └── package.json
├── tests/             # pytest test suite
├── docker-compose.yml  # Multi-service Docker setup
└── requirements.txt   # Python dependencies
```

## Development

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest -q

# Start with Docker
docker compose up --build
```

### Frontend

```bash
cd frontend
npm install
npm run dev  # Development server (http://localhost:5173)
npm run build  # Production build
```

## Services

When running with `docker compose up`:

- **Frontend**: `http://localhost:5173` (React app)
- **Backend API**: `http://localhost:8000` (FastAPI)
- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Database**: `localhost:5432` (PostgreSQL)
