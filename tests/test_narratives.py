"""Tests for CDDBS narrative matcher (production)."""

import pytest
from src.cddbs.narratives import (
    match_narratives,
    match_narratives_from_report,
    get_all_narratives,
)


class TestNarrativeMatcher:
    """Test keyword-based narrative matching."""

    def test_anti_nato_narrative_detected(self):
        text = (
            "NATO expansion threatens Russia's security. "
            "The encirclement of Russia continues with broken promises "
            "about security guarantees from the West."
        )
        matches = match_narratives(text, threshold=2)
        assert len(matches) >= 1
        ids = [m["narrative_id"] for m in matches]
        assert "anti_nato_001" in ids

    def test_ukraine_revisionism_detected(self):
        text = (
            "The neo-Nazi elements in Ukraine and the Azov battalion "
            "demonstrate why denazification was necessary. "
            "Bandera's legacy lives on in the current regime."
        )
        matches = match_narratives(text, threshold=2)
        assert len(matches) >= 1
        ids = [m["narrative_id"] for m in matches]
        assert "ukraine_001" in ids

    def test_no_match_on_clean_text(self):
        text = (
            "The weather today is sunny with a high of 72 degrees. "
            "Perfect for a walk in the park."
        )
        matches = match_narratives(text, threshold=2)
        assert len(matches) == 0

    def test_confidence_levels(self):
        text = (
            "NATO expansion encirclement broken promises security guarantees "
            "Article 5 military buildup"
        )
        matches = match_narratives(text, threshold=2)
        if matches:
            for m in matches:
                assert m["confidence"] in ("high", "moderate", "low")

    def test_match_count_ordering(self):
        text = (
            "NATO expansion encirclement broken promises security guarantees. "
            "EU is collapsing because Brussels bureaucrats made the EU undemocratic."
        )
        matches = match_narratives(text, threshold=2)
        if len(matches) >= 2:
            assert matches[0]["match_count"] >= matches[1]["match_count"]

    def test_matched_keywords_returned(self):
        text = "NATO expansion and encirclement of Russia with broken promises."
        matches = match_narratives(text, threshold=2)
        assert len(matches) >= 1
        assert len(matches[0]["matched_keywords"]) >= 2

    def test_threshold_parameter(self):
        text = "NATO expansion is a concern."
        matches_low = match_narratives(text, threshold=1)
        matches_high = match_narratives(text, threshold=3)
        assert len(matches_low) >= len(matches_high)


class TestNarrativeFromReport:
    """Test report-level narrative matching."""

    def test_combines_report_and_articles(self):
        report_text = "This report covers NATO expansion and encirclement."
        articles = [
            {"title": "Article about broken promises and security guarantees", "snippet": "NATO broken promises security guarantees"},
        ]
        matches = match_narratives_from_report(report_text, articles)
        assert len(matches) >= 1

    def test_deduplicates_by_narrative_id(self):
        report_text = "NATO expansion and encirclement and broken promises."
        articles = [
            {"snippet": "NATO expansion encirclement broken promises security guarantees"},
        ]
        matches = match_narratives_from_report(report_text, articles)
        ids = [m["narrative_id"] for m in matches]
        assert len(ids) == len(set(ids))  # No duplicates


class TestGetAllNarratives:
    """Test the narratives database accessor."""

    def test_returns_list(self):
        result = get_all_narratives()
        assert isinstance(result, list)
        assert len(result) >= 15

    def test_each_narrative_has_fields(self):
        result = get_all_narratives()
        for n in result:
            assert "id" in n
            assert "name" in n
            assert "category_id" in n
            assert "keywords" in n
            assert len(n["keywords"]) >= 1
