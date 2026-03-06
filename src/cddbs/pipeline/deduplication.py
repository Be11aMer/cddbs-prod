"""Article deduplication — URL hash and title similarity."""

from datetime import datetime, timedelta, UTC

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.cddbs.models import RawArticle


TITLE_SIMILARITY_THRESHOLD = 0.85


def find_title_duplicates(session, window_hours: int = 24) -> int:
    """Mark articles with near-identical titles as duplicates.

    Compares articles within a time window using TF-IDF cosine similarity.
    Returns count of newly marked duplicates.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    articles = (
        session.query(RawArticle)
        .filter(
            RawArticle.is_duplicate == False,
            RawArticle.created_at >= cutoff,
        )
        .order_by(RawArticle.created_at)
        .all()
    )

    if len(articles) < 2:
        return 0

    titles = [a.title for a in articles]
    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    tfidf_matrix = vectorizer.fit_transform(titles)

    sim_matrix = cosine_similarity(tfidf_matrix)
    marked = 0

    for i in range(len(articles)):
        if articles[i].is_duplicate:
            continue
        for j in range(i + 1, len(articles)):
            if articles[j].is_duplicate:
                continue
            if sim_matrix[i, j] >= TITLE_SIMILARITY_THRESHOLD:
                articles[j].is_duplicate = True
                articles[j].duplicate_of = articles[i].id
                marked += 1

    if marked:
        session.commit()

    return marked
