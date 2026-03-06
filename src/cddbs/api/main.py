from datetime import datetime, UTC
from typing import List, Optional, Tuple

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.cddbs.config import settings
from src.cddbs.database import SessionLocal, init_db
from src.cddbs.models import (
    Article, Outlet, Report, Briefing, NarrativeMatch, Feedback,
    TopicRun, TopicOutletResult,
    RawArticle, EventCluster, NarrativeBurst,
)
from src.cddbs.pipeline.orchestrator import run_pipeline
from src.cddbs.pipeline.topic_pipeline import run_topic_pipeline
from src.cddbs.narratives import get_all_narratives


from contextlib import asynccontextmanager

from src.cddbs.collectors.manager import CollectorManager

# Global collector manager instance
_collector_manager: CollectorManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _collector_manager
    # Ensure tables exist on startup
    init_db()

    # Start collector manager for event intelligence pipeline
    _collector_manager = CollectorManager(db_session_factory=SessionLocal)
    _collector_manager.start_background(interval_seconds=180)  # every 3 minutes

    yield

    # Shutdown collectors
    if _collector_manager:
        _collector_manager.stop()

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


# ---------------------------------------------------------------------------
# Feedback (standalone, no relationships)
# ---------------------------------------------------------------------------


class FeedbackCreateRequest(BaseModel):
    tester_name: Optional[str] = None
    tester_role: Optional[str] = None
    overall_rating: int = Field(..., ge=1, le=5)
    accuracy_rating: int = Field(..., ge=1, le=5)
    usability_rating: int = Field(..., ge=1, le=5)
    bugs_encountered: str = Field(..., min_length=5)
    misleading_outputs: Optional[str] = None
    missing_features: Optional[str] = None
    ux_pain_points: Optional[str] = None
    professional_concerns: Optional[str] = None
    would_recommend: Optional[str] = None
    additional_comments: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    tester_name: Optional[str] = None
    tester_role: Optional[str] = None
    overall_rating: int
    accuracy_rating: int
    usability_rating: int
    bugs_encountered: str
    misleading_outputs: Optional[str] = None
    missing_features: Optional[str] = None
    ux_pain_points: Optional[str] = None
    professional_concerns: Optional[str] = None
    would_recommend: Optional[str] = None
    additional_comments: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


@app.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(payload: FeedbackCreateRequest, db: Session = Depends(get_db)):
    """Submit tester feedback (early-stage quality gate)."""
    fb = Feedback(
        tester_name=payload.tester_name,
        tester_role=payload.tester_role,
        overall_rating=payload.overall_rating,
        accuracy_rating=payload.accuracy_rating,
        usability_rating=payload.usability_rating,
        bugs_encountered=payload.bugs_encountered,
        misleading_outputs=payload.misleading_outputs,
        missing_features=payload.missing_features,
        ux_pain_points=payload.ux_pain_points,
        professional_concerns=payload.professional_concerns,
        would_recommend=payload.would_recommend,
        additional_comments=payload.additional_comments,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


@app.get("/feedback", response_model=List[FeedbackResponse])
def list_feedback(db: Session = Depends(get_db)):
    """List all feedback entries (for dev review)."""
    return db.query(Feedback).order_by(Feedback.created_at.desc()).all()


# ---------------------------------------------------------------------------
# Monitoring Dashboard Stats Endpoints
# ---------------------------------------------------------------------------


class GlobalStatsResponse(BaseModel):
    total_analyses: int
    countries_monitored: int
    total_narratives_detected: int
    active_runs: int
    completed_runs: int
    failed_runs: int
    avg_quality_score: Optional[float] = None


class CountryStatItem(BaseModel):
    country: str
    run_count: int
    completed_count: int
    narrative_count: int
    avg_quality: Optional[float] = None
    risk_score: float  # composite score for map coloring


class NarrativeTrendItem(BaseModel):
    narrative_id: str
    narrative_name: str
    category: Optional[str]
    total_matches: int
    report_count: int
    confidence_high: int
    confidence_medium: int
    confidence_low: int


class FeedItem(BaseModel):
    title: str
    url: str
    domain: str
    source_country: Optional[str]
    published: str
    language: str


class MonitoringFeedResponse(BaseModel):
    items: List[FeedItem]
    source: str
    fetched_at: str
    error: Optional[str] = None


@app.get("/stats/global", response_model=GlobalStatsResponse)
def get_global_stats(db: Session = Depends(get_db)):
    """Aggregate global stats for the monitoring dashboard metric bar."""
    from sqlalchemy import func

    reports = db.query(Report).all()
    total = len(reports)

    countries = set()
    active = 0
    completed = 0
    failed = 0
    quality_scores = []
    narrative_total = 0

    for r in reports:
        if r.country:
            countries.add(r.country)
        status, _ = _get_report_status(r)
        if status in ("running", "queued"):
            active += 1
        elif status == "completed":
            completed += 1
        elif status == "failed":
            failed += 1
        data = r.data or {}
        if isinstance(data, dict) and data.get("quality_score"):
            quality_scores.append(data["quality_score"])
        narrative_total += db.query(NarrativeMatch).filter(
            NarrativeMatch.report_id == r.id
        ).count()

    avg_quality = round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else None

    return GlobalStatsResponse(
        total_analyses=total,
        countries_monitored=len(countries),
        total_narratives_detected=narrative_total,
        active_runs=active,
        completed_runs=completed,
        failed_runs=failed,
        avg_quality_score=avg_quality,
    )


@app.get("/stats/by-country", response_model=List[CountryStatItem])
def get_stats_by_country(db: Session = Depends(get_db)):
    """Per-country roll-up for the world map and country risk index."""
    from collections import defaultdict

    reports = db.query(Report).all()
    country_data: dict = defaultdict(lambda: {
        "run_count": 0, "completed": 0, "narratives": 0, "quality_scores": []
    })

    for r in reports:
        country = r.country or "Unknown"
        country_data[country]["run_count"] += 1
        status, _ = _get_report_status(r)
        if status == "completed":
            country_data[country]["completed"] += 1
        data = r.data or {}
        if isinstance(data, dict) and data.get("quality_score"):
            country_data[country]["quality_scores"].append(data["quality_score"])
        n_count = db.query(NarrativeMatch).filter(NarrativeMatch.report_id == r.id).count()
        country_data[country]["narratives"] += n_count

    results = []
    for country, d in country_data.items():
        if country == "Unknown":
            continue
        avg_q = round(sum(d["quality_scores"]) / len(d["quality_scores"]), 1) if d["quality_scores"] else None
        # Risk score: more narratives relative to runs = higher risk (0-100)
        narrative_ratio = (d["narratives"] / max(d["run_count"], 1)) * 20
        risk_score = min(100.0, round(narrative_ratio + (d["run_count"] * 5), 1))
        results.append(CountryStatItem(
            country=country,
            run_count=d["run_count"],
            completed_count=d["completed"],
            narrative_count=d["narratives"],
            avg_quality=avg_q,
            risk_score=risk_score,
        ))

    results.sort(key=lambda x: x.risk_score, reverse=True)
    return results


@app.get("/stats/narrative-trends", response_model=List[NarrativeTrendItem])
def get_narrative_trends(db: Session = Depends(get_db)):
    """Top narratives by frequency across all analyses."""
    from collections import defaultdict

    matches = db.query(NarrativeMatch).all()
    trends: dict = defaultdict(lambda: {
        "name": "", "category": None, "total": 0, "reports": set(),
        "high": 0, "medium": 0, "low": 0
    })

    for m in matches:
        t = trends[m.narrative_id]
        t["name"] = m.narrative_name
        t["category"] = m.category
        t["total"] += m.match_count
        t["reports"].add(m.report_id)
        conf = (m.confidence or "").lower()
        if conf == "high":
            t["high"] += 1
        elif conf == "medium":
            t["medium"] += 1
        else:
            t["low"] += 1

    results = [
        NarrativeTrendItem(
            narrative_id=nid,
            narrative_name=d["name"],
            category=d["category"],
            total_matches=d["total"],
            report_count=len(d["reports"]),
            confidence_high=d["high"],
            confidence_medium=d["medium"],
            confidence_low=d["low"],
        )
        for nid, d in trends.items()
    ]
    results.sort(key=lambda x: x.total_matches, reverse=True)
    return results[:15]


_gdelt_cache: dict = {"items": [], "fetched_at": None, "error": None}
_GDELT_CACHE_TTL = 300  # seconds (5 minutes)


@app.get("/monitoring/feed", response_model=MonitoringFeedResponse)
def get_monitoring_feed():
    """Proxy GDELT news feed filtered for disinformation-relevant events."""
    import requests as req
    from datetime import datetime, UTC

    now = datetime.now(UTC)
    cached_at = _gdelt_cache["fetched_at"]
    if cached_at and (now - cached_at).total_seconds() < _GDELT_CACHE_TTL:
        return MonitoringFeedResponse(
            items=_gdelt_cache["items"],
            source="GDELT Project (cached)",
            fetched_at=cached_at.isoformat(),
            error=_gdelt_cache["error"],
        )

    gdelt_url = (
        "https://api.gdeltproject.org/api/v2/doc/doc"
        "?query=disinformation%20OR%20propaganda%20OR%20misinformation%20OR%20cyberattack"
        "%20OR%20election%20interference%20OR%20fake%20news"
        "&mode=ArtList&maxrecords=25&format=json&timespan=1d&sort=DateDesc"
    )

    items: List[FeedItem] = []
    feed_error: Optional[str] = None
    try:
        resp = req.get(gdelt_url, timeout=20)
        if resp.status_code == 200:
            payload = resp.json()
            for article in payload.get("articles", []):
                raw_date = article.get("seendate", "")
                try:
                    # GDELT format: YYYYMMDDTHHMMSSz
                    parsed = datetime.strptime(raw_date[:15], "%Y%m%dT%H%M%S")
                    formatted = parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
                except Exception:
                    formatted = raw_date
                items.append(FeedItem(
                    title=article.get("title", "No title"),
                    url=article.get("url", ""),
                    domain=article.get("domain", ""),
                    source_country=article.get("sourcecountry", None),
                    published=formatted,
                    language=article.get("language", "English"),
                ))
        else:
            feed_error = f"GDELT returned HTTP {resp.status_code}"
            print(f"DEBUG monitoring: {feed_error}")
    except Exception as exc:
        feed_error = str(exc)
        print(f"DEBUG monitoring: GDELT feed error: {exc}")

    if items:
        _gdelt_cache["items"] = items
        _gdelt_cache["fetched_at"] = now
        _gdelt_cache["error"] = None

    return MonitoringFeedResponse(
        items=items,
        source="GDELT Project",
        fetched_at=datetime.now(UTC).isoformat(),
        error=feed_error,
    )


# ---------------------------------------------------------------------------
# Topic Mode endpoints
# ---------------------------------------------------------------------------


class TopicRunCreateRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=300)
    num_outlets: int = Field(5, ge=1, le=10)
    date_filter: Optional[str] = Field("m", description="qdr: h/d/w/m/y")
    serpapi_key: Optional[str] = None
    google_api_key: Optional[str] = None


class TopicRunStatusResponse(BaseModel):
    id: int
    topic: str
    num_outlets: int
    date_filter: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    outlets_found: int = 0


class TopicOutletResultResponse(BaseModel):
    id: int
    outlet_name: str
    outlet_domain: Optional[str] = None
    articles_analyzed: int
    divergence_score: Optional[int] = None
    amplification_signal: Optional[str] = None
    propaganda_techniques: Optional[List[str]] = None
    framing_summary: Optional[str] = None
    divergence_explanation: Optional[str] = None
    article_links: Optional[List[dict]] = None

    model_config = {"from_attributes": True}


class TopicRunDetailResponse(TopicRunStatusResponse):
    baseline_summary: Optional[str] = None
    outlet_results: List[TopicOutletResultResponse] = Field(default_factory=list)


def _run_topic_job(
    topic_run_id: int,
    topic: str,
    num_outlets: int,
    date_filter: str,
    serpapi_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
):
    """Background wrapper for run_topic_pipeline with error handling."""
    db = SessionLocal()
    try:
        run_topic_pipeline(
            topic_run_id=topic_run_id,
            topic=topic,
            num_outlets=num_outlets,
            date_filter=date_filter,
            serpapi_key=serpapi_key,
            google_api_key=google_api_key,
        )
    except Exception as exc:
        topic_run = db.query(TopicRun).filter(TopicRun.id == topic_run_id).first()
        if topic_run:
            topic_run.status = "failed"
            topic_run.error = str(exc)
            db.commit()
    finally:
        db.close()


@app.post("/topic-runs", response_model=TopicRunStatusResponse)
def create_topic_run(
    payload: TopicRunCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create a new topic-mode analysis run."""
    serpapi_key = payload.serpapi_key
    google_api_key = payload.google_api_key

    topic_run = TopicRun(
        topic=payload.topic,
        num_outlets=payload.num_outlets,
        date_filter=payload.date_filter or "m",
        status="pending",
    )
    db.add(topic_run)
    db.commit()
    db.refresh(topic_run)

    background_tasks.add_task(
        _run_topic_job,
        topic_run_id=topic_run.id,
        topic=payload.topic,
        num_outlets=payload.num_outlets,
        date_filter=payload.date_filter or "m",
        serpapi_key=serpapi_key,
        google_api_key=google_api_key,
    )

    return TopicRunStatusResponse(
        id=topic_run.id,
        topic=topic_run.topic,
        num_outlets=topic_run.num_outlets,
        date_filter=topic_run.date_filter,
        status="pending",
        created_at=topic_run.created_at,
        outlets_found=0,
    )


@app.get("/topic-runs", response_model=List[TopicRunStatusResponse])
def list_topic_runs(db: Session = Depends(get_db)):
    """Return all topic runs ordered by creation date."""
    runs = db.query(TopicRun).order_by(TopicRun.created_at.desc()).all()
    result = []
    for r in runs:
        outlets_found = db.query(TopicOutletResult).filter(
            TopicOutletResult.topic_run_id == r.id
        ).count()
        result.append(TopicRunStatusResponse(
            id=r.id,
            topic=r.topic,
            num_outlets=r.num_outlets,
            date_filter=r.date_filter,
            status=r.status,
            created_at=r.created_at,
            completed_at=r.completed_at,
            error=r.error,
            outlets_found=outlets_found,
        ))
    return result


@app.get("/topic-runs/{topic_run_id}", response_model=TopicRunDetailResponse)
def get_topic_run(topic_run_id: int, db: Session = Depends(get_db)):
    """Return a topic run with its full outlet results ranked by divergence score."""
    topic_run = db.query(TopicRun).filter(TopicRun.id == topic_run_id).first()
    if not topic_run:
        raise HTTPException(status_code=404, detail="Topic run not found")

    results = (
        db.query(TopicOutletResult)
        .filter(TopicOutletResult.topic_run_id == topic_run_id)
        .order_by(TopicOutletResult.divergence_score.desc())
        .all()
    )

    outlet_responses = [
        TopicOutletResultResponse(
            id=r.id,
            outlet_name=r.outlet_name,
            outlet_domain=r.outlet_domain,
            articles_analyzed=r.articles_analyzed,
            divergence_score=r.divergence_score,
            amplification_signal=r.amplification_signal,
            propaganda_techniques=r.propaganda_techniques,
            framing_summary=r.framing_summary,
            divergence_explanation=r.divergence_explanation,
            article_links=r.article_links,
        )
        for r in results
    ]

    return TopicRunDetailResponse(
        id=topic_run.id,
        topic=topic_run.topic,
        num_outlets=topic_run.num_outlets,
        date_filter=topic_run.date_filter,
        status=topic_run.status,
        created_at=topic_run.created_at,
        completed_at=topic_run.completed_at,
        error=topic_run.error,
        outlets_found=len(results),
        baseline_summary=topic_run.baseline_summary,
        outlet_results=outlet_responses,
    )


# ---------------------------------------------------------------------------
# Event Intelligence Pipeline endpoints
# ---------------------------------------------------------------------------


class EventClusterResponse(BaseModel):
    id: int
    title: Optional[str] = None
    event_type: Optional[str] = None
    countries: Optional[list] = None
    keywords: Optional[list] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    article_count: int = 0
    source_count: int = 0
    burst_score: float = 0.0
    narrative_risk_score: float = 0.0
    status: str = "active"
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EventClusterDetailResponse(EventClusterResponse):
    entities: Optional[dict] = None
    articles: list[dict] = Field(default_factory=list)


class NarrativeBurstResponse(BaseModel):
    id: int
    keyword: str
    baseline_frequency: Optional[float] = None
    current_frequency: Optional[float] = None
    z_score: Optional[float] = None
    cluster_id: Optional[int] = None
    detected_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CollectorStatusResponse(BaseModel):
    collectors: list[dict]


class EventMapItem(BaseModel):
    country: str
    event_count: int
    avg_risk_score: float
    top_event_type: Optional[str] = None


@app.get("/events", response_model=List[EventClusterResponse])
def list_events(
    event_type: Optional[str] = None,
    country: Optional[str] = None,
    status: Optional[str] = "active",
    min_risk: Optional[float] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List event clusters with optional filtering."""
    query = db.query(EventCluster)

    if status:
        query = query.filter(EventCluster.status == status)
    if event_type:
        query = query.filter(EventCluster.event_type == event_type)
    if min_risk is not None:
        query = query.filter(EventCluster.narrative_risk_score >= min_risk)
    if country:
        # JSON array contains check
        query = query.filter(EventCluster.countries.contains([country]))

    events = (
        query.order_by(EventCluster.narrative_risk_score.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [EventClusterResponse.model_validate(e) for e in events]


@app.get("/events/map", response_model=List[EventMapItem])
def get_events_map(db: Session = Depends(get_db)):
    """Get events grouped by country for map visualization."""
    clusters = db.query(EventCluster).filter_by(status="active").all()

    country_data: dict[str, dict] = {}
    for cluster in clusters:
        for country in (cluster.countries or []):
            if country not in country_data:
                country_data[country] = {"events": [], "types": []}
            country_data[country]["events"].append(cluster)
            if cluster.event_type:
                country_data[country]["types"].append(cluster.event_type)

    result = []
    for country, data in country_data.items():
        events = data["events"]
        avg_risk = sum(e.narrative_risk_score or 0 for e in events) / len(events) if events else 0
        from collections import Counter
        type_counts = Counter(data["types"])
        top_type = type_counts.most_common(1)[0][0] if type_counts else None

        result.append(EventMapItem(
            country=country,
            event_count=len(events),
            avg_risk_score=round(avg_risk, 3),
            top_event_type=top_type,
        ))

    return sorted(result, key=lambda x: x.event_count, reverse=True)


@app.get("/events/bursts", response_model=List[NarrativeBurstResponse])
def list_bursts(
    min_zscore: Optional[float] = None,
    active_only: bool = True,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List detected narrative bursts (keyword frequency spikes)."""
    query = db.query(NarrativeBurst)

    if active_only:
        query = query.filter(NarrativeBurst.resolved_at == None)
    if min_zscore is not None:
        query = query.filter(NarrativeBurst.z_score >= min_zscore)

    bursts = (
        query.order_by(NarrativeBurst.z_score.desc())
        .limit(limit)
        .all()
    )

    return [NarrativeBurstResponse.model_validate(b) for b in bursts]


@app.get("/events/{event_id}", response_model=EventClusterDetailResponse)
def get_event_detail(event_id: int, db: Session = Depends(get_db)):
    """Get detailed event cluster with articles."""
    cluster = db.query(EventCluster).filter(EventCluster.id == event_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Event cluster not found")

    articles = (
        db.query(RawArticle)
        .filter(RawArticle.cluster_id == event_id, RawArticle.is_duplicate == False)
        .order_by(RawArticle.published_at.desc())
        .limit(100)
        .all()
    )

    article_dicts = [
        {
            "id": a.id,
            "title": a.title,
            "url": a.url,
            "source_name": a.source_name,
            "source_domain": a.source_domain,
            "source_type": a.source_type,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "country": a.country,
        }
        for a in articles
    ]

    return EventClusterDetailResponse(
        id=cluster.id,
        title=cluster.title,
        event_type=cluster.event_type,
        countries=cluster.countries,
        keywords=cluster.keywords,
        entities=cluster.entities,
        first_seen=cluster.first_seen,
        last_seen=cluster.last_seen,
        article_count=cluster.article_count,
        source_count=cluster.source_count,
        burst_score=cluster.burst_score,
        narrative_risk_score=cluster.narrative_risk_score,
        status=cluster.status,
        created_at=cluster.created_at,
        articles=article_dicts,
    )


@app.get("/collector/status", response_model=CollectorStatusResponse)
def get_collector_status():
    """Get health status of all news collectors."""
    if _collector_manager:
        return CollectorStatusResponse(collectors=_collector_manager.statuses)
    return CollectorStatusResponse(collectors=[])
