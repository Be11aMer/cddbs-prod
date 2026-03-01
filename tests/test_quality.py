"""Tests for the CDDBS quality scorer (production)."""

import json
from pathlib import Path

import pytest

from src.cddbs.quality import (
    score_actionability,
    score_analytical_rigor,
    score_attribution_quality,
    score_briefing,
    score_confidence_signaling,
    score_evidence_presentation,
    score_readability,
    score_structural_completeness,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def high_quality():
    with open(FIXTURES_DIR / "high_quality_briefing.json") as f:
        return json.load(f)


@pytest.fixture
def medium_quality():
    with open(FIXTURES_DIR / "medium_quality_briefing.json") as f:
        return json.load(f)


@pytest.fixture
def low_quality():
    with open(FIXTURES_DIR / "low_quality_briefing.json") as f:
        return json.load(f)


@pytest.fixture
def minimal_valid():
    with open(FIXTURES_DIR / "minimal_valid_briefing.json") as f:
        return json.load(f)


class TestHighQualityBriefing:
    """High quality briefing should score >= 60/70 (Excellent)."""

    def test_total_score_excellent(self, high_quality):
        result = score_briefing(high_quality)
        assert result["total_score"] >= 60, (
            f"Expected >= 60, got {result['total_score']}"
        )
        assert result["rating"] == "Excellent"

    def test_structural_completeness(self, high_quality):
        score, issues = score_structural_completeness(high_quality)
        assert score >= 8, f"Expected >= 8, got {score}. Issues: {issues}"

    def test_attribution_quality(self, high_quality):
        score, issues = score_attribution_quality(high_quality)
        assert score >= 8, f"Expected >= 8, got {score}. Issues: {issues}"

    def test_confidence_signaling(self, high_quality):
        score, issues = score_confidence_signaling(high_quality)
        assert score >= 8, f"Expected >= 8, got {score}. Issues: {issues}"

    def test_evidence_presentation(self, high_quality):
        score, issues = score_evidence_presentation(high_quality)
        assert score >= 8, f"Expected >= 8, got {score}. Issues: {issues}"

    def test_analytical_rigor(self, high_quality):
        score, issues = score_analytical_rigor(high_quality)
        assert score >= 8, f"Expected >= 8, got {score}. Issues: {issues}"

    def test_actionability(self, high_quality):
        score, issues = score_actionability(high_quality)
        assert score >= 8, f"Expected >= 8, got {score}. Issues: {issues}"

    def test_readability(self, high_quality):
        score, issues = score_readability(high_quality)
        assert score >= 8, f"Expected >= 8, got {score}. Issues: {issues}"


class TestMediumQualityBriefing:
    """Medium quality briefing should score 40-59 (Acceptable to Good)."""

    def test_total_score_below_high(self, medium_quality):
        result = score_briefing(medium_quality)
        assert 40 <= result["total_score"] < 70, (
            f"Expected 40-69, got {result['total_score']}"
        )

    def test_rating_not_failing(self, medium_quality):
        result = score_briefing(medium_quality)
        assert result["rating"] in ("Acceptable", "Good", "Excellent")


class TestLowQualityBriefing:
    """Low quality briefing should score < 40 (Poor or Failing)."""

    def test_total_score_low(self, low_quality):
        result = score_briefing(low_quality)
        assert result["total_score"] < 40, (
            f"Expected < 40, got {result['total_score']}"
        )

    def test_rating(self, low_quality):
        result = score_briefing(low_quality)
        assert result["rating"] in ("Poor", "Failing")

    def test_has_many_issues(self, low_quality):
        result = score_briefing(low_quality)
        total_issues = sum(
            len(d["issues"]) for d in result["dimensions"].values()
        )
        assert total_issues >= 10, f"Expected >= 10 issues, got {total_issues}"


class TestMinimalBriefing:
    """Minimal valid briefing should score in acceptable range."""

    def test_total_score_range(self, minimal_valid):
        result = score_briefing(minimal_valid)
        assert 20 <= result["total_score"] <= 50, (
            f"Expected 20-50, got {result['total_score']}"
        )


class TestTelegramBriefing:
    """Telegram channel briefing should score well (>= 60)."""

    @pytest.fixture
    def telegram_channel(self):
        with open(FIXTURES_DIR / "telegram_channel_briefing.json") as f:
            return json.load(f)

    def test_total_score_excellent(self, telegram_channel):
        result = score_briefing(telegram_channel)
        assert result["total_score"] >= 60, (
            f"Expected >= 60, got {result['total_score']}"
        )

    def test_evidence_types_recognized(self, telegram_channel):
        score, issues = score_attribution_quality(telegram_channel)
        assert score >= 8, f"Expected >= 8, got {score}. Issues: {issues}"

    def test_structural_with_network_graph(self, telegram_channel):
        score, issues = score_structural_completeness(telegram_channel)
        assert score >= 9, f"Expected >= 9, got {score}. Issues: {issues}"


class TestCrossPlatformBriefing:
    """Cross-platform briefing should score well."""

    @pytest.fixture
    def cross_platform(self):
        with open(FIXTURES_DIR / "cross_platform_briefing.json") as f:
            return json.load(f)

    def test_total_score_excellent(self, cross_platform):
        result = score_briefing(cross_platform)
        assert result["total_score"] >= 60, (
            f"Expected >= 60, got {result['total_score']}"
        )

    def test_has_cross_platform_bonus(self, cross_platform):
        score, _ = score_structural_completeness(cross_platform)
        assert score >= 9  # Should get bonus for cross_platform_identities


class TestScorerEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_briefing(self):
        result = score_briefing({})
        assert result["total_score"] == 0
        assert result["rating"] == "Failing"

    def test_all_dimensions_return_max_10(self, high_quality):
        result = score_briefing(high_quality)
        for dim in result["dimensions"].values():
            assert 0 <= dim["score"] <= 10

    def test_total_equals_sum_of_dimensions(self, high_quality):
        result = score_briefing(high_quality)
        dim_sum = sum(d["score"] for d in result["dimensions"].values())
        assert result["total_score"] == dim_sum

    def test_scorecard_has_all_dimensions(self, high_quality):
        result = score_briefing(high_quality)
        expected_dims = {
            "structural_completeness",
            "attribution_quality",
            "confidence_signaling",
            "evidence_presentation",
            "analytical_rigor",
            "actionability",
            "readability",
        }
        assert set(result["dimensions"].keys()) == expected_dims
