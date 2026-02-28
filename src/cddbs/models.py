from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, ForeignKey
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
