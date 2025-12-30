from src.cddbs.pipeline.orchestrator import run_pipeline
from unittest.mock import patch
from src.cddbs.database import SessionLocal
from src.cddbs import models


def test_run_pipeline(monkeypatch):
    """Test run_pipeline executes all stages and returns structured output."""
    from src.cddbs import config
    monkeypatch.setattr(config.settings, "SERPAPI_KEY", None)
    monkeypatch.setattr(config.settings, "GOOGLE_API_KEY", None)

    # Mock the Gemini calls to avoid actual API calls
    with patch("src.cddbs.pipeline.orchestrator.call_gemini") as mock_gemini:

        mock_gemini.return_value = '{"individual_analyses": [{"title": "Art1", "propaganda_score": 0.5}], "final_briefing": "Summary text"}'

        out = run_pipeline('test-outlet', 'US', num_articles=1)

        assert out['outlet'] == 'test-outlet'
        assert out['country'] == 'US'
        assert 'final_report' in out
        assert 'articles' in out
        assert 'raw_response' in out
        
        # Verify database state
        db = SessionLocal()
        try:
            report = db.query(models.Report).filter(models.Report.outlet == 'test-outlet').first()
            assert report is not None
            assert report.data['articles_analyzed'] == 1
            assert report.data['status'] == 'completed'
        finally:
            db.close()


def test_run_pipeline_creates_outlet_in_db(monkeypatch):
    """Test that run_pipeline creates outlet in database."""
    from src.cddbs import config
    from src.cddbs.database import SessionLocal
    from src.cddbs.models import Outlet

    monkeypatch.setattr(config.settings, "SERPAPI_KEY", None)
    monkeypatch.setattr(config.settings, "GOOGLE_API_KEY", None)

    with patch("src.cddbs.pipeline.orchestrator.call_gemini") as mock_gemini:
        mock_gemini.return_value = '{"individual_analyses": [], "final_briefing": "Summary"}'

        run_pipeline('new-outlet', 'US', num_articles=1)

        # Verify outlet was created
        db = SessionLocal()
        try:
            outlet = db.query(Outlet).filter(Outlet.name == 'new-outlet').first()
            assert outlet is not None
            assert outlet.name == 'new-outlet'
        finally:
            db.close()


def test_run_pipeline_handles_existing_outlet(monkeypatch):
    """Test that run_pipeline uses existing outlet if present."""
    from src.cddbs import config
    from src.cddbs.database import SessionLocal
    from src.cddbs.models import Outlet

    monkeypatch.setattr(config.settings, "SERPAPI_KEY", None)
    monkeypatch.setattr(config.settings, "GOOGLE_API_KEY", None)

    # Create outlet first
    db = SessionLocal()
    try:
        existing_outlet = Outlet(name='existing-outlet', url='existing.com')
        db.add(existing_outlet)
        db.commit()
        outlet_id = existing_outlet.id
    finally:
        db.close()

    with patch("src.cddbs.pipeline.orchestrator.call_gemini") as mock_gemini:
        mock_gemini.return_value = '{"individual_analyses": [], "final_briefing": "Summary"}'

        run_pipeline('existing-outlet', 'US', num_articles=1)

        # Verify same outlet was used
        db = SessionLocal()
        try:
            outlet = db.query(Outlet).filter(Outlet.name == 'existing-outlet').first()
            assert outlet is not None
            assert outlet.id == outlet_id
        finally:
            db.close()

