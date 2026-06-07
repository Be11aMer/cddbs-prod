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
    analysis_status = Column(String, default="completed")  # completed/partial/failed
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
    model_version = Column(String, nullable=True)  # Gemini model string used for this run (audit H-4)
    validation_warnings = Column(JSON, nullable=True)  # List of validation errors/warnings from output_validator
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


class TopicBaseline(Base):
    """Cached neutral wire-service baseline for a topic.

    Generated once per topic and reused as a fixed, named artifact across all
    subsequent TopicRuns (audit M-2): regenerating the baseline on every run
    made comparative results across runs of the same topic non-comparable,
    since each run was scored against a different reference. Cached
    indefinitely; invalidation is manual (delete the row to force regeneration).
    """
    __tablename__ = "topic_baselines"
    __table_args__ = {'extend_existing': True}
    id                      = Column(Integer, primary_key=True, index=True)
    topic                   = Column(String, nullable=False)
    topic_key               = Column(String, nullable=False, unique=True, index=True)  # normalised lookup key
    baseline_summary        = Column(Text, nullable=True)
    baseline_raw            = Column(Text, nullable=True)
    reference_article_count = Column(Integer, default=0)
    model_version           = Column(String, nullable=True)
    created_at              = Column(DateTime, default=lambda: datetime.now(UTC))

    topic_runs = relationship("TopicRun", back_populates="baseline")


class TopicRun(Base):
    """A topic-mode analysis run: discover which outlets push narratives on a given topic."""
    __tablename__ = "topic_runs"
    __table_args__ = {'extend_existing': True}
    id               = Column(Integer, primary_key=True, index=True)
    topic            = Column(String, nullable=False)
    num_outlets      = Column(Integer, default=5)
    date_filter      = Column(String, default="m")
    status           = Column(String, default="pending")   # pending/running/completed/failed
    baseline_id      = Column(Integer, ForeignKey("topic_baselines.id"), nullable=True)
    baseline_summary = Column(Text, nullable=True)
    baseline_raw     = Column(Text, nullable=True)
    coordination_signal = Column(Float, nullable=True)
    coordination_detail = Column(JSON, nullable=True)
    created_at       = Column(DateTime, default=lambda: datetime.now(UTC))
    completed_at     = Column(DateTime, nullable=True)
    error            = Column(Text, nullable=True)

    baseline = relationship("TopicBaseline", back_populates="topic_runs")
    outlet_results = relationship("TopicOutletResult", back_populates="topic_run",
                                  cascade="all, delete-orphan")


class TopicOutletResult(Base):
    """Per-outlet comparative result for a TopicRun."""
    __tablename__ = "topic_outlet_results"
    __table_args__ = {'extend_existing': True}
    id                    = Column(Integer, primary_key=True, index=True)
    topic_run_id          = Column(Integer, ForeignKey("topic_runs.id"), nullable=False)
    outlet_name           = Column(String, nullable=False)
    outlet_domain         = Column(String, nullable=True)
    articles_analyzed     = Column(Integer, default=0)
    divergence_score      = Column(Integer, nullable=True)  # 0-100
    amplification_signal  = Column(String, nullable=True)   # low/medium/high
    propaganda_techniques = Column(JSON, nullable=True)     # list[str] — raw Gemini tags (free text)
    propaganda_techniques_normalized = Column(JSON, nullable=True)  # [{code, name, raw}] mapped onto closed taxonomy (audit M-1)
    framing_summary       = Column(Text, nullable=True)
    divergence_explanation = Column(Text, nullable=True)
    key_claims            = Column(JSON, nullable=True)
    omissions             = Column(JSON, nullable=True)
    gemini_raw            = Column(Text, nullable=True)
    article_links         = Column(JSON, nullable=True)     # [{title, url, date}]
    analysis_status       = Column(String, default="completed")  # completed/partial/failed
    validation_warnings   = Column(JSON, nullable=True)     # errors+warnings from output_validator
    model_version         = Column(String, nullable=True)   # Gemini model string used for this run (audit H-4)
    created_at            = Column(DateTime, default=lambda: datetime.now(UTC))

    topic_run = relationship("TopicRun", back_populates="outlet_results")


class Feedback(Base):
    """Tester feedback — standalone table, no relationships."""
    __tablename__ = "feedback"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    tester_name = Column(String, nullable=True)
    tester_role = Column(String, nullable=True)
    overall_rating = Column(Integer, nullable=False)
    accuracy_rating = Column(Integer, nullable=False)
    usability_rating = Column(Integer, nullable=False)
    bugs_encountered = Column(Text, nullable=False)
    misleading_outputs = Column(Text, nullable=True)
    missing_features = Column(Text, nullable=True)
    ux_pain_points = Column(Text, nullable=True)
    professional_concerns = Column(Text, nullable=True)
    would_recommend = Column(String, nullable=True)
    additional_comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


# ── Event Intelligence Pipeline models ────────────────────────────────


class RawArticle(Base):
    """Normalized article ingested from any collector source."""
    __tablename__ = "raw_articles"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    url_hash = Column(String(64), unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    source_name = Column(String, nullable=True)
    source_domain = Column(String, index=True, nullable=True)
    source_type = Column(String, nullable=True)
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
    event_type = Column(String, nullable=True)
    countries = Column(JSON, nullable=True)
    entities = Column(JSON, nullable=True)
    keywords = Column(JSON, nullable=True)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    article_count = Column(Integer, default=0)
    source_count = Column(Integer, default=0)
    burst_score = Column(Float, default=0.0)
    narrative_risk_score = Column(Float, default=0.0)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    articles = relationship("RawArticle", back_populates="cluster")


class NarrativeBurst(Base):
    """A detected keyword/topic frequency spike."""
    __tablename__ = "narrative_bursts"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, index=True, nullable=False)
    baseline_frequency = Column(Float, nullable=True)
    current_frequency = Column(Float, nullable=True)
    z_score = Column(Float, nullable=True)
    cluster_id = Column(Integer, ForeignKey("event_clusters.id"), nullable=True)
    detected_at = Column(DateTime, default=lambda: datetime.now(UTC))
    resolved_at = Column(DateTime, nullable=True)


class ThreatBriefing(Base):
    """Automated threat intelligence briefing."""
    __tablename__ = "threat_briefings"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("event_clusters.id"), nullable=True)
    briefing_type = Column(String, nullable=False)
    title = Column(String, nullable=True)
    executive_summary = Column(Text, nullable=True)
    briefing_json = Column(JSON, nullable=True)
    framing_analysis = Column(JSON, nullable=True)
    raw_response = Column(Text, nullable=True)
    articles_analyzed = Column(Integer, default=0)
    sources_compared = Column(Integer, default=0)
    gemini_tokens_used = Column(Integer, nullable=True)
    quality_score = Column(Integer, nullable=True)
    quality_rating = Column(String, nullable=True)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    cluster = relationship("EventCluster", backref="threat_briefings")


class SourceCredibility(Base):
    """Per-domain source credibility index."""
    __tablename__ = "source_credibility"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    source_domain = Column(String, unique=True, index=True, nullable=False)
    total_articles = Column(Integer, default=0)
    avg_propaganda_score = Column(Float, default=0.0)
    framing_divergence_score = Column(Float, default=0.0)
    coordination_count = Column(Integer, default=0)
    burst_participation_count = Column(Integer, default=0)
    reliability_index = Column(Float, default=0.5)
    trend_direction = Column(String, default="stable")
    previous_reliability_index = Column(Float, nullable=True)
    last_computed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class WebhookConfig(Base):
    """Webhook endpoint configuration for alert delivery."""
    __tablename__ = "webhook_configs"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    events = Column(JSON, default=list)
    secret = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    last_triggered_at = Column(DateTime, nullable=True)
    failure_count = Column(Integer, default=0)


class ApiKey(Base):
    """API key for endpoint authentication (Sprint 10 / C-1).

    Only the Argon2id hash is stored; plaintext is never persisted.
    key_prefix stores the first 8 chars for identification in logs.
    """
    __tablename__ = "api_keys"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)        # descriptive label (e.g. 'bootstrap', 'ci-runner')
    key_prefix = Column(String(8), nullable=False)  # first 8 chars of plaintext for identification
    key_hash = Column(String, nullable=False)    # argon2id hash of the full plaintext key
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    last_used_at = Column(DateTime, nullable=True)
