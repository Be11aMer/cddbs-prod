"""TF-IDF based event clustering — groups related articles into events."""

from datetime import datetime, timedelta, UTC

from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.cddbs.models import RawArticle, EventCluster


# Event type keyword heuristics
_EVENT_TYPE_KEYWORDS = {
    "conflict": {"attack", "strike", "war", "bomb", "missile", "military", "killed", "troops", "battle", "airstrike"},
    "protest": {"protest", "demonstration", "rally", "march", "strike", "unrest", "riot"},
    "diplomacy": {"summit", "talks", "treaty", "agreement", "diplomatic", "ambassador", "negotiate"},
    "disaster": {"earthquake", "flood", "hurricane", "tsunami", "wildfire", "collapse", "disaster"},
    "cyber": {"hack", "cyber", "breach", "ransomware", "malware", "vulnerability", "data leak"},
    "info_warfare": {"propaganda", "disinformation", "misinformation", "fake news", "influence operation", "troll"},
    "economic": {"sanctions", "tariff", "trade war", "embargo", "recession", "inflation", "debt"},
}


def cluster_articles(session, window_hours: int = 24, distance_threshold: float = 0.6) -> list[EventCluster]:
    """Cluster recent non-duplicate articles into event groups.

    Uses TF-IDF + Agglomerative Clustering.
    Returns list of newly created EventCluster objects.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    articles = (
        session.query(RawArticle)
        .filter(
            RawArticle.is_duplicate == False,
            RawArticle.cluster_id == None,
            RawArticle.created_at >= cutoff,
        )
        .order_by(RawArticle.created_at)
        .all()
    )

    if len(articles) < 3:
        return []

    # Build TF-IDF from title + content snippet
    texts = []
    for a in articles:
        text = a.title or ""
        if a.content:
            text += " " + a.content[:500]
        texts.append(text)

    vectorizer = TfidfVectorizer(stop_words="english", max_features=10000)
    tfidf_matrix = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()

    # Agglomerative clustering with cosine distance
    distance_matrix = 1 - cosine_similarity(tfidf_matrix)
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="precomputed",
        linkage="average",
    )
    labels = clustering.fit_predict(distance_matrix)

    # Group articles by cluster label
    clusters_map: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        if label == -1:
            continue
        clusters_map.setdefault(label, []).append(idx)

    # Create EventCluster records for clusters with 3+ articles
    new_clusters = []
    for label, article_indices in clusters_map.items():
        if len(article_indices) < 3:
            continue

        cluster_articles = [articles[i] for i in article_indices]
        cluster = _create_event_cluster(cluster_articles, tfidf_matrix, article_indices, feature_names)
        session.add(cluster)
        session.flush()  # get cluster.id

        for a in cluster_articles:
            a.cluster_id = cluster.id

        new_clusters.append(cluster)

    if new_clusters:
        session.commit()

    return new_clusters


def _create_event_cluster(
    articles: list[RawArticle],
    tfidf_matrix,
    indices: list[int],
    feature_names,
) -> EventCluster:
    """Build an EventCluster from a group of articles."""
    # Extract top keywords from TF-IDF
    cluster_tfidf = tfidf_matrix[indices].toarray().mean(axis=0)
    top_keyword_indices = cluster_tfidf.argsort()[-10:][::-1]
    keywords = [feature_names[i] for i in top_keyword_indices if cluster_tfidf[i] > 0]

    # Determine event type from keywords
    event_type = _classify_event_type(keywords, articles)

    # Extract countries
    countries = list({a.country for a in articles if a.country})

    # Extract unique sources
    sources = {a.source_domain for a in articles if a.source_domain}

    # Timeline
    pub_dates = [a.published_at for a in articles if a.published_at]
    first_seen = min(pub_dates) if pub_dates else articles[0].created_at
    last_seen = max(pub_dates) if pub_dates else articles[-1].created_at

    # Title: use the most representative article (first one by time)
    title = articles[0].title

    return EventCluster(
        title=title,
        event_type=event_type,
        countries=countries,
        entities=None,
        keywords=keywords,
        first_seen=first_seen,
        last_seen=last_seen,
        article_count=len(articles),
        source_count=len(sources),
        burst_score=0.0,
        narrative_risk_score=0.0,
        status="active",
    )


def _classify_event_type(keywords: list[str], articles: list[RawArticle]) -> str:
    """Classify event type based on keyword heuristics."""
    all_text = " ".join(keywords).lower()
    for a in articles:
        all_text += " " + (a.title or "").lower()

    scores = {}
    for event_type, type_keywords in _EVENT_TYPE_KEYWORDS.items():
        score = sum(1 for kw in type_keywords if kw in all_text)
        if score > 0:
            scores[event_type] = score

    if scores:
        return max(scores, key=scores.get)
    return "other"
