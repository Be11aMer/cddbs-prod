from datetime import datetime, UTC
from typing import List, Optional, Tuple

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.cddbs.config import settings
from src.cddbs.database import SessionLocal, init_db
from src.cddbs.models import Article, Outlet, Report, Briefing, NarrativeMatch
from src.cddbs.pipeline.orchestrator import run_pipeline
from src.cddbs.narratives import get_all_narratives


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist on startup
    init_db()
    yield

app = FastAPI(title="CDDBS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    """Provide a SQLAlchemy session for request lifetime."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



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

    model_config = {
        "from_attributes": True
    }


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
    date_filter: Optional[str] = Field("m", description="Date filter for articles: h (hour), d (day), w (week), m (month), y (year)")


class RunStatusResponse(BaseModel):
    id: int
    outlet: str
    country: Optional[str] = None
    created_at: datetime
    status: str
    message: Optional[str] = None
    quality_score: Optional[int] = None
    quality_rating: Optional[str] = None
    narrative_count: Optional[int] = None


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
    google_api_key: Optional[str] = None,
    date_filter: str = "m"
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
            google_api_key=google_api_key,
            date_filter=date_filter
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
                "analysis_date": datetime.now(UTC).isoformat(),
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
            "analysis_date": datetime.now(UTC).isoformat(),
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
        google_api_key=payload.google_api_key,
        date_filter=payload.date_filter or "m"
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
        data = r.data or {}
        response.append(
            RunStatusResponse(
                id=r.id,
                outlet=r.outlet,
                country=r.country,
                created_at=r.created_at,
                status=status,
                message=msg,
                quality_score=data.get("quality_score") if isinstance(data, dict) else None,
                quality_rating=data.get("quality_rating") if isinstance(data, dict) else None,
                narrative_count=data.get("narrative_matches_count") if isinstance(data, dict) else None,
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
                    data.get("analysis_date", datetime.now(UTC).isoformat())
                ),
                articles_analyzed=data.get("articles_analyzed", 0),
            )
        except Exception:  # noqa: BLE001
            meta = None

    # Return articles linked to this specific report
    article_summaries: List[ArticleSummary] = [
        ArticleSummary.model_validate(a) for a in report.articles
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


# ---------------------------------------------------------------------------
# Sprint 4: Quality & Narrative Endpoints
# ---------------------------------------------------------------------------


class QualityDimension(BaseModel):
    score: int
    max: int
    issues: List[str] = Field(default_factory=list)


class QualityResponse(BaseModel):
    report_id: int
    total_score: Optional[int] = None
    max_score: int = 70
    rating: Optional[str] = None
    dimensions: Optional[dict] = None
    prompt_version: Optional[str] = None


class NarrativeMatchResponse(BaseModel):
    id: int
    narrative_id: str
    narrative_name: str
    category: Optional[str] = None
    confidence: Optional[str] = None
    matched_keywords: Optional[List[str]] = None
    match_count: int = 0

    model_config = {
        "from_attributes": True
    }


class NarrativeInfoResponse(BaseModel):
    id: str
    name: str
    category_id: str
    category_name: str
    description: str
    keywords: List[str] = Field(default_factory=list)
    frequency: str = "unknown"
    active: bool = True


@app.get("/analysis-runs/{report_id}/quality", response_model=QualityResponse)
def get_quality_score(report_id: int, db: Session = Depends(get_db)):
    """Return the quality scorecard for a completed analysis run."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    briefing = db.query(Briefing).filter(Briefing.report_id == report_id).first()
    if not briefing:
        return QualityResponse(
            report_id=report_id,
            total_score=None,
            rating=None,
            dimensions=None,
            prompt_version=None,
        )

    return QualityResponse(
        report_id=report_id,
        total_score=briefing.quality_score,
        max_score=70,
        rating=briefing.quality_rating,
        dimensions=briefing.quality_details.get("dimensions") if briefing.quality_details else None,
        prompt_version=briefing.prompt_version,
    )


@app.get("/analysis-runs/{report_id}/narratives", response_model=List[NarrativeMatchResponse])
def get_narrative_matches(report_id: int, db: Session = Depends(get_db)):
    """Return narrative matches for a completed analysis run."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    matches = db.query(NarrativeMatch).filter(
        NarrativeMatch.report_id == report_id
    ).order_by(NarrativeMatch.match_count.desc()).all()

    return [
        NarrativeMatchResponse(
            id=m.id,
            narrative_id=m.narrative_id,
            narrative_name=m.narrative_name,
            category=m.category,
            confidence=m.confidence,
            matched_keywords=m.matched_keywords,
            match_count=m.match_count,
        )
        for m in matches
    ]


@app.get("/narratives", response_model=List[NarrativeInfoResponse])
def list_narratives():
    """Return the full known narratives database (for reference/UI display)."""
    return [NarrativeInfoResponse(**n) for n in get_all_narratives()]
