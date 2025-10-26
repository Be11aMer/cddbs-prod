# CDDBS (PostgreSQL + FastAPI)

It is configured for **PostgreSQL** and includes a FastAPI backend, basic pipeline modules, SQLAlchemy models, unit tests, Docker support, and a Makefile.

## Quick start (development)
1. In `.env` and set your values (POSTGRES_USER, POSTGRES_PASSWORD, etc.).
2. Build and start services:
   ```bash
   docker compose up --build
   ```
3. API will be available at `http://localhost:8000`.
4. Run tests (locally):
   ```bash
   pip install -r requirements.txt
   pytest -q
   ```

## What is included
- `src/cddbs/` : main package
- `src/cddbs/pipeline/*` : pipeline stages (fetch, analyze, digest, translate, summarize)
- `src/cddbs/api` : FastAPI app
- `src/cddbs/models.py` : SQLAlchemy models for outlets/articles/reports
- `docker-compose.yml`, `Dockerfile` : Docker setup with Postgres
- `tests/` : pytest
