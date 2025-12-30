from src.cddbs.pipeline.fetch import fetch_articles


def test_fetch_mock(monkeypatch):
    """Test fetch_articles returns mock data when no API key."""
    from src.cddbs import config
    monkeypatch.setattr(config.settings, "SERPAPI_KEY", None)
    res = fetch_articles('test', 'us')
    assert isinstance(res, list)
    assert len(res) > 0
    assert res[0]['title'].startswith('Mock article')
    assert 'link' in res[0]
    assert 'snippet' in res[0]
