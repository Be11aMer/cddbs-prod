from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.cddbs.database import SessionLocal, init_db
from src.cddbs.models import Article, Outlet, Report
from src.cddbs.pipeline.orchestrator import run_pipeline


app = FastAPI(title="CDDBS API")


def get_db():
    """Provide a SQLAlchemy session for request lifetime."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    # Ensure tables exist on startup
    init_db()

@app.get("/")
def root():
    return {"service": "cddbs", "status": "ok"}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ArticleSummary(BaseModel):
    id: int
    title: str
    link: Optional[str] = None
    snippet: Optional[str] = None
    date: Optional[str] = None

    class Config:
        from_attributes = True


class ReportData(BaseModel):
    outlet: str
    url: str
    country: str
    analysis_date: datetime
    articles_analyzed: int


class ReportResponse(BaseModel):
    id: int
    outlet: str
    country: Optional[str] = None
    created_at: datetime
    meta: Optional[ReportData] = None
    final_report: Optional[str] = None
    status: str
    message: Optional[str] = None
    articles: List[ArticleSummary] = Field(default_factory=list)


class RunCreateRequest(BaseModel):
    outlet: str
    url: str
    country: str
    num_articles: int = Field(5, ge=1, le=20)
    serpapi_key: Optional[str] = None
    google_api_key: Optional[str] = None


class RunStatusResponse(BaseModel):
    id: int
    outlet: str
    country: Optional[str] = None
    created_at: datetime
    status: str
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_report_status(report: Report) -> Tuple[str, Optional[str]]:
    """Helper to determine the high-level status of a report."""
    status = "completed"
    msg = None
    data = report.data or {}
    errors = data.get("errors") if isinstance(data, dict) else None
    
    if errors:
        status = "failed"
        msg = "; ".join(map(str, errors))
    elif not report.final_report:
        status = "running"
        
    return status, msg


def _get_or_create_outlet(db: Session, name: str, url: str) -> Outlet:
    outlet = db.query(Outlet).filter(Outlet.name == name).first()
    if outlet:
        # Update URL if it changed
        if url and outlet.url != url:
            outlet.url = url
            db.add(outlet)
            db.commit()
            db.refresh(outlet)
        return outlet

    outlet = Outlet(name=name, url=url)
    db.add(outlet)
    db.commit()
    db.refresh(outlet)
    return outlet


def _run_analysis_job(
    report_id: int,
    outlet: str,
    url: str,
    country: str,
    num_articles: int = 5,
    serpapi_key: Optional[str] = None,
    google_api_key: Optional[str] = None
):
    """
    Background job that executes the analysis pipeline and persists results.
    """
    db = SessionLocal()
    try:
        # handle updating the report and articles
        run_pipeline(
            outlet, 
            country, 
            report_id=report_id, 
            num_articles=num_articles, 
            url=url,
            serpapi_key=serpapi_key,
            google_api_key=google_api_key
        )

    except Exception as exc:  # noqa: BLE001
        # If something fails, we still want the report row to exist; we just
        # store the error message in its data payload.
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.data = {
                "outlet": outlet,
                "url": url,
                "country": country,
                "analysis_date": datetime.utcnow().isoformat(),
                "articles_analyzed": 0,
                "errors": [str(exc)],
            }
            db.add(report)
            db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@app.post("/analysis-runs", response_model=RunStatusResponse)
def create_analysis_run(
    payload: RunCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Create a new analysis run.

    This immediately creates a placeholder Report row and then schedules
    the long-running analysis in a background task.
    """
    report = Report(
        outlet=payload.outlet,
        country=payload.country,
        final_report=None,
        data={
            "outlet": payload.outlet,
            "url": payload.url,
            "country": payload.country,
            "analysis_date": datetime.utcnow().isoformat(),
            "articles_analyzed": 0,
            "status": "pending",
        },
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    background_tasks.add_task(
        _run_analysis_job,
        report_id=report.id,
        outlet=payload.outlet,
        url=payload.url,
        country=payload.country,
        num_articles=payload.num_articles,
        serpapi_key=payload.serpapi_key,
        google_api_key=payload.google_api_key
    )

    return RunStatusResponse(
        id=report.id,
        outlet=report.outlet,
        country=report.country,
        created_at=report.created_at,
        status="queued",
        message="Analysis run scheduled",
    )


@app.get("/analysis-runs", response_model=List[RunStatusResponse])
def list_analysis_runs(db: Session = Depends(get_db)):
    """Return a lightweight list of analysis runs for the UI history view."""
    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    response: List[RunStatusResponse] = []

    for r in reports:
        status, msg = _get_report_status(r)
        response.append(
            RunStatusResponse(
                id=r.id,
                outlet=r.outlet,
                country=r.country,
                created_at=r.created_at,
                status=status,
                message=msg,
            )
        )

    return response


@app.get("/analysis-runs/{report_id}", response_model=ReportResponse)
def get_analysis_run(report_id: int, db: Session = Depends(get_db)):
    """
    Return a single analysis run, including its final report text and
    a list of associated articles (if any).

    This endpoint is what the frontend will use for the detailed briefing view.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    data = report.data or {}
    meta = None
    if isinstance(data, dict):
        try:
            meta = ReportData(
                outlet=data.get("outlet", report.outlet),
                url=data.get("url", ""),
                country=data.get("country", report.country or ""),
                analysis_date=datetime.fromisoformat(
                    data.get("analysis_date", datetime.utcnow().isoformat())
                ),
                articles_analyzed=data.get("articles_analyzed", 0),
            )
        except Exception:  # noqa: BLE001
            meta = None

    # Return articles linked to this specific report
    article_summaries: List[ArticleSummary] = [
        ArticleSummary.from_orm(a) for a in report.articles
    ]

    status, msg = _get_report_status(report)

    return ReportResponse(
        id=report.id,
        outlet=report.outlet,
        country=report.country,
        created_at=report.created_at,
        meta=meta,
        final_report=report.final_report,
        status=status,
        message=msg,
        articles=article_summaries,
    )


@app.get("/health")
def healthcheck(db: Session = Depends(get_db)):
    """
    Lightweight health endpoint for deployment checks.
    Verifies DB connectivity in addition to the base service status.
    """
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"database_error: {exc}") from exc

    return {"status": "ok"}


@app.get("/api-status")
def api_status():
    """
    Check configuration status of external APIs (SerpAPI and Gemini).
    This endpoint ONLY checks if API keys are configured - it does NOT make actual API calls
    to avoid consuming tokens unnecessarily.
    """
    from src.cddbs.config import settings

    status = {
        "serpapi": {
            "configured": bool(settings.SERPAPI_KEY),
            "status": "configured" if settings.SERPAPI_KEY else "not_configured",
            "message": "SerpAPI key is configured" if settings.SERPAPI_KEY else "SerpAPI key not configured in .env file",
        },
        "gemini": {
            "configured": bool(settings.GOOGLE_API_KEY),
            "status": "configured" if settings.GOOGLE_API_KEY else "not_configured",
            "message": "Google API key is configured" if settings.GOOGLE_API_KEY else "Google API key not configured in .env file",
        },
    }

    return status
