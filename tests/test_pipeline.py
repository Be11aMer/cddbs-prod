"""Tests for pipeline modules."""
import pytest
from unittest.mock import Mock, patch

from src.cddbs.pipeline import fetch, analyze, digest, translate, summarize
from src.cddbs import config


def test_fetch_articles_without_api_key(monkeypatch):
    """Test fetch_articles falls back to mock when no API key."""
    monkeypatch.setattr(config.settings, "SERPAPI_KEY", None)
    result = fetch.fetch_articles("TestOutlet", "US")

    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0]["title"].startswith("Mock article")
    assert "link" in result[0]
    assert "snippet" in result[0]


def test_fetch_articles_mock_structure(monkeypatch):
    """Test that mock fetch returns properly structured data."""
    monkeypatch.setattr(config.settings, "SERPAPI_KEY", None)
    result = fetch.fetch_articles("TestOutlet", "US")

    article = result[0]
    assert "title" in article
    assert "link" in article
    assert "snippet" in article
    assert "date" in article
    assert "meta" in article
    assert "full_text" in article


@patch("src.cddbs.pipeline.fetch.requests.get")
def test_fetch_articles_with_api_key(mock_get, monkeypatch):
    """Test fetch_articles with API key (mocked request)."""
    monkeypatch.setattr(config.settings, "SERPAPI_KEY", "test_key")
    monkeypatch.setattr(config.settings, "ARTICLE_LIMIT", 3)

    mock_response = Mock()
    mock_response.json.return_value = {
        "news_results": [
            {"title": "Article 1", "link": "http://test.com/1"},
            {"title": "Article 2", "link": "http://test.com/2"},
            {"title": "Article 3", "link": "http://test.com/3"},
            {"title": "Article 4", "link": "http://test.com/4"},
        ]
    }
    mock_get.return_value = mock_response

    result = fetch.fetch_articles("TestOutlet", "US")

    assert len(result) == 3  # Limited by ARTICLE_LIMIT
    assert result[0]["title"] == "Article 1"
    mock_get.assert_called_once()


@patch("src.cddbs.pipeline.fetch.requests.get")
def test_fetch_articles_api_error(mock_get, monkeypatch):
    """Test fetch_articles handles API errors gracefully."""
    monkeypatch.setattr(config.settings, "SERPAPI_KEY", "test_key")
    mock_get.side_effect = Exception("API Error")

    # Should return empty list
    results = fetch.fetch_articles("TestOutlet", "US")
    assert results == []


def test_analyze_article_with_mock_data():
    """Test analyze_article with mock article data."""
    article = {
        "title": "Test Article",
        "full_text": "This is test content for analysis.",
        "snippet": "Test snippet",
    }

    with patch("src.cddbs.pipeline.analyze.call_gemini") as mock_gemini:
        mock_gemini.return_value = '{"propaganda_score": 0.7, "sentiment": "negative", "framing": "biased"}'
        result = analyze.analyze_article(article)

        assert "propaganda_score" in result
        assert "sentiment" in result
        assert "framing" in result


def test_analyze_article_fallback():
    """Test analyze_article fallback when Gemini fails."""
    article = {
        "title": "Test Article",
        "full_text": "Test content",
    }

    with patch("src.cddbs.pipeline.analyze.call_gemini") as mock_gemini:
        mock_gemini.side_effect = Exception("API Error")
        result = analyze.analyze_article(article)

        assert "propaganda_score" in result
        assert result["propaganda_score"] == 0.2
        assert result["sentiment"] == "neutral"


def test_analyze_article_without_full_text():
    """Test analyze_article uses snippet or title when full_text missing."""
    article = {
        "title": "Test Article Title",
        "snippet": "Test snippet",
    }

    with patch("src.cddbs.pipeline.analyze.call_gemini") as mock_gemini:
        mock_gemini.return_value = '{"propaganda_score": 0.5}'
        result = analyze.analyze_article(article)

        # Should use snippet
        assert result is not None


def test_digest_content():
    """Test digest_content function."""
    article = {
        "title": "Test Article",
        "full_text": "Test content with claims and actors.",
    }
    analysis = {"propaganda_score": 0.6, "sentiment": "negative"}

    with patch("src.cddbs.pipeline.digest.call_gemini") as mock_gemini:
        mock_gemini.return_value = '{"KEY_CLAIMS": ["Claim 1"], "KEY_ACTORS": ["Actor 1"]}'
        result = digest.digest_content(article, analysis)

        assert isinstance(result, dict)


def test_digest_content_fallback():
    """Test digest_content fallback when Gemini fails."""
    article = {
        "title": "Test Article",
        "full_text": "Test content",
    }
    analysis = {}

    with patch("src.cddbs.pipeline.digest.call_gemini") as mock_gemini:
        mock_gemini.side_effect = Exception("API Error")
        result = digest.digest_content(article, analysis)

        assert "KEY_CLAIMS" in result
        assert "KEY_ACTORS" in result
        assert result["KEY_CLAIMS"] == [article["title"]]


def test_translate_text():
    """Test translate_text function."""
    text = "Bonjour le monde"
    target_lang = "en"

    with patch("src.cddbs.pipeline.translate.call_gemini") as mock_gemini:
        mock_gemini.return_value = "Hello world"
        result = translate.translate_text(text, target_lang)

        assert result == "Hello world"
        mock_gemini.assert_called_once()


def test_translate_text_fallback():
    """Test translate_text fallback when Gemini fails."""
    text = "Test text"

    with patch("src.cddbs.pipeline.translate.call_gemini") as mock_gemini:
        mock_gemini.side_effect = Exception("API Error")
        result = translate.translate_text(text)

        assert result == text  # Should return original text


def test_summarize_digest():
    """Test summarize_digest function."""
    outlet = "TestOutlet"
    country = "US"
    digest_data = {
        "KEY_CLAIMS": ["Claim 1", "Claim 2"],
        "KEY_ACTORS": ["Actor 1"],
        "NARRATIVE_THEMES": ["Theme 1"],
    }

    with patch("src.cddbs.pipeline.summarize.call_gemini") as mock_gemini:
        mock_gemini.return_value = "Intelligence Briefing Summary"
        result = summarize.summarize_digest(outlet, country, digest_data)

        assert isinstance(result, str)
        assert len(result) > 0
        mock_gemini.assert_called_once()


def test_summarize_digest_with_complex_data():
    """Test summarize_digest with complex digest data."""
    outlet = "RT"
    country = "Russia"
    digest_data = {
        "KEY_CLAIMS": ["Complex claim with details"],
        "KEY_ACTORS": ["Actor 1", "Actor 2"],
        "NARRATIVE_THEMES": ["Theme 1", "Theme 2"],
        "UNVERIFIED_STATEMENTS": ["Statement 1"],
        "EMOTIONAL_LANGUAGE": ["word1", "word2"],
    }

    with patch("src.cddbs.pipeline.summarize.call_gemini") as mock_gemini:
        mock_gemini.return_value = "Detailed Intelligence Briefing"
        result = summarize.summarize_digest(outlet, country, digest_data)

        assert isinstance(result, str)
        # Should serialize digest_data to JSON in prompt
        call_args = mock_gemini.call_args[0][0]
        assert outlet in call_args
        assert country in call_args

