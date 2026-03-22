from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from src.cddbs.database import Base

class Outlet(Base):
    __tablename__ = "outlets"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    url = Column(String, nullable=True)

    articles = relationship("Article", back_populates="outlet")

class Article(Base):
    __tablename__ = "articles"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    outlet_id = Column(Integer, ForeignKey("outlets.id"))
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)
    title = Column(String, nullable=False)
    link = Column(String, nullable=True)
    snippet = Column(Text, nullable=True)
    date = Column(String, nullable=True)
    meta = Column(JSON, nullable=True)
    full_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    outlet = relationship("Outlet", back_populates="articles")
    report = relationship("Report", back_populates="articles")

class Report(Base):
    __tablename__ = "reports"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    outlet = Column(String, nullable=False)
    country = Column(String, nullable=True)
    final_report = Column(Text, nullable=True)
    raw_response = Column(Text, nullable=True)
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    articles = relationship("Article", back_populates="report")
    briefing = relationship("Briefing", back_populates="report", uselist=False)
    narrative_matches = relationship("NarrativeMatch", back_populates="report")


class Briefing(Base):
    """Structured briefing output with quality scoring."""
    __tablename__ = "briefings"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, unique=True)
    briefing_json = Column(JSON, nullable=True)
    quality_score = Column(Integer, nullable=True)
    quality_rating = Column(String, nullable=True)  # Excellent/Good/Acceptable/Poor/Failing
    quality_details = Column(JSON, nullable=True)  # Full scorecard breakdown
    prompt_version = Column(String, default="v1.3")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    report = relationship("Report", back_populates="briefing")


class NarrativeMatch(Base):
    """Matched known disinformation narratives for a report."""
    __tablename__ = "narrative_matches"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    narrative_id = Column(String, nullable=False)  # e.g., "anti_nato_001"
    narrative_name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    confidence = Column(String, nullable=True)  # high/moderate/low
    matched_keywords = Column(JSON, nullable=True)
    match_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    report = relationship("Report", back_populates="narrative_matches")


class TopicRun(Base):
    """A topic-mode analysis run: discover which outlets push narratives on a given topic."""
    __tablename__ = "topic_runs"
    __table_args__ = {'extend_existing': True}
    id               = Column(Integer, primary_key=True, index=True)
    topic            = Column(String, nullable=False)       # e.g. "NATO expansion eastward"
    num_outlets      = Column(Integer, default=5)
    date_filter      = Column(String, default="m")
    status           = Column(String, default="pending")   # pending/running/completed/failed
    baseline_summary = Column(Text, nullable=True)         # Gemini neutral baseline prose
    baseline_raw     = Column(Text, nullable=True)         # raw Gemini JSON response
    coordination_signal = Column(Float, nullable=True)     # 0.0-1.0 — fraction of high-divergence outlets sharing ≥2 techniques
    coordination_detail = Column(JSON, nullable=True)      # {shared_techniques: [...], coordinated_outlets: [...]}
    created_at       = Column(DateTime, default=lambda: datetime.now(UTC))
    completed_at     = Column(DateTime, nullable=True)
    error            = Column(Text, nullable=True)

    outlet_results = relationship("TopicOutletResult", back_populates="topic_run",
                                  cascade="all, delete-orphan")


class TopicOutletResult(Base):
    """Per-outlet comparative result for a TopicRun."""
    __tablename__ = "topic_outlet_results"
    __table_args__ = {'extend_existing': True}
    id                    = Column(Integer, primary_key=True, index=True)
    topic_run_id          = Column(Integer, ForeignKey("topic_runs.id"), nullable=False)
    outlet_name           = Column(String, nullable=False)  # discovered domain / name
    outlet_domain         = Column(String, nullable=True)
    articles_analyzed     = Column(Integer, default=0)
    divergence_score      = Column(Integer, nullable=True)  # 0-100
    amplification_signal  = Column(String, nullable=True)   # low/medium/high
    propaganda_techniques = Column(JSON, nullable=True)     # list[str]
    framing_summary       = Column(Text, nullable=True)
    divergence_explanation = Column(Text, nullable=True)
    key_claims            = Column(JSON, nullable=True)     # list[str] — specific claims made by outlet
    omissions             = Column(JSON, nullable=True)     # list[str] — key facts omitted vs baseline
    gemini_raw            = Column(Text, nullable=True)
    article_links         = Column(JSON, nullable=True)     # [{title, url, date}]
    created_at            = Column(DateTime, default=lambda: datetime.now(UTC))

    topic_run = relationship("TopicRun", back_populates="outlet_results")


class Feedback(Base):
    """Tester feedback — standalone table, no relationships."""
    __tablename__ = "feedback"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    # Who
    tester_name = Column(String, nullable=True)
    tester_role = Column(String, nullable=True)  # analyst, developer, researcher, other
    # Core feedback (mandatory fields)
    overall_rating = Column(Integer, nullable=False)  # 1-5
    accuracy_rating = Column(Integer, nullable=False)  # 1-5: Are analysis results accurate?
    usability_rating = Column(Integer, nullable=False)  # 1-5: Is the UI intuitive?
    bugs_encountered = Column(Text, nullable=False)  # Describe any bugs found
    # Detailed feedback (optional)
    misleading_outputs = Column(Text, nullable=True)  # Any misleading/incorrect AI outputs?
    missing_features = Column(Text, nullable=True)  # What features are missing?
    ux_pain_points = Column(Text, nullable=True)  # What was frustrating to use?
    professional_concerns = Column(Text, nullable=True)  # Anything unprofessional/inappropriate?
    would_recommend = Column(String, nullable=True)  # yes/no/maybe
    additional_comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


# ── Event Intelligence Pipeline models ────────────────────────────────


class RawArticle(Base):
    """Normalized article ingested from any collector source (RSS, GDELT, news API)."""
    __tablename__ = "raw_articles"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    url_hash = Column(String(64), unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    source_name = Column(String, nullable=True)
    source_domain = Column(String, index=True, nullable=True)
    source_type = Column(String, nullable=True)  # rss, gdelt, news_api
    published_at = Column(DateTime, nullable=True)
    language = Column(String(10), nullable=True)
    country = Column(String(100), nullable=True)
    raw_meta = Column(JSON, nullable=True)
    cluster_id = Column(Integer, ForeignKey("event_clusters.id"), nullable=True)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(Integer, ForeignKey("raw_articles.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    cluster = relationship("EventCluster", back_populates="articles")


class EventCluster(Base):
    """A detected event — group of related articles about the same event."""
    __tablename__ = "event_clusters"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    event_type = Column(String, nullable=True)  # conflict, protest, diplomacy, disaster, cyber, info_warfare
    countries = Column(JSON, nullable=True)      # ["Ukraine", "Russia"]
    entities = Column(JSON, nullable=True)       # {"people": [], "orgs": [], "locations": []}
    keywords = Column(JSON, nullable=True)       # ["explosion", "port"]
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    article_count = Column(Integer, default=0)
    source_count = Column(Integer, default=0)
    burst_score = Column(Float, default=0.0)
    narrative_risk_score = Column(Float, default=0.0)
    status = Column(String, default="active")    # active, declining, resolved
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    articles = relationship("RawArticle", back_populates="cluster")


class NarrativeBurst(Base):
    """A detected keyword/topic frequency spike."""
    __tablename__ = "narrative_bursts"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, index=True, nullable=False)
    baseline_frequency = Column(Float, nullable=True)   # articles/hour (rolling 24h avg)
    current_frequency = Column(Float, nullable=True)     # articles/hour (last 1h)
    z_score = Column(Float, nullable=True)
    cluster_id = Column(Integer, ForeignKey("event_clusters.id"), nullable=True)
    detected_at = Column(DateTime, default=lambda: datetime.now(UTC))
    resolved_at = Column(DateTime, nullable=True)


class WebhookConfig(Base):
    """Webhook endpoint configuration for alert delivery."""
    __tablename__ = "webhook_configs"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    events = Column(JSON, default=list)   # ["pipeline_failure", "narrative_burst"]
    secret = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    last_triggered_at = Column(DateTime, nullable=True)
    failure_count = Column(Integer, default=0)
