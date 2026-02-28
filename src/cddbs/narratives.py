"""
CDDBS Narrative Matcher

Matches text content against the known disinformation narratives database.
Returns matched narrative IDs, confidence scores, and matched keywords.
Integrated from research Sprint 1-2.
"""

import json
from pathlib import Path

NARRATIVES_PATH = Path(__file__).parent / "data" / "known_narratives.json"

_narratives_cache = None


def _load_narratives() -> dict:
    """Load and cache the known narratives database."""
    global _narratives_cache
    if _narratives_cache is None:
        with open(NARRATIVES_PATH) as f:
            _narratives_cache = json.load(f)
    return _narratives_cache


def _build_flat_narratives() -> list:
    """Flatten the category → narrative hierarchy into a single list."""
    db = _load_narratives()
    flat = []
    for category in db.get("categories", []):
        cat_id = category["id"]
        cat_name = category["name"]
        for narr in category.get("narratives", []):
            flat.append({
                "id": narr["id"],
                "name": narr["name"],
                "category_id": cat_id,
                "category_name": cat_name,
                "keywords": [kw.lower() for kw in narr.get("keywords", [])],
                "description": narr.get("description", ""),
                "frequency": narr.get("frequency", "unknown"),
                "active": narr.get("active", True),
            })
    return flat


def match_narratives(text: str, threshold: int = 2) -> list:
    """
    Match text against known disinformation narratives.

    Args:
        text: The text content to analyze (briefing text, article text, etc.)
        threshold: Minimum number of keyword matches to consider a narrative matched.

    Returns:
        List of matched narratives sorted by match strength, each containing:
        - narrative_id: The narrative ID (e.g., "anti_nato_001")
        - narrative_name: Human-readable name
        - category: Category name
        - matched_keywords: List of keywords found in the text
        - match_count: Number of keywords matched
        - confidence: "high" (5+), "moderate" (3-4), "low" (2)
    """
    text_lower = text.lower()
    narratives = _build_flat_narratives()
    matches = []

    for narr in narratives:
        if not narr["active"]:
            continue

        matched_keywords = []
        for kw in narr["keywords"]:
            if kw in text_lower:
                matched_keywords.append(kw)

        if len(matched_keywords) >= threshold:
            match_count = len(matched_keywords)
            if match_count >= 5:
                confidence = "high"
            elif match_count >= 3:
                confidence = "moderate"
            else:
                confidence = "low"

            matches.append({
                "narrative_id": narr["id"],
                "narrative_name": narr["name"],
                "category": narr["category_name"],
                "matched_keywords": matched_keywords,
                "match_count": match_count,
                "confidence": confidence,
            })

    matches.sort(key=lambda m: m["match_count"], reverse=True)
    return matches


def match_narratives_from_report(report_text: str, articles: list = None) -> list:
    """
    Match narratives from a full report and its articles.

    Combines narrative matches from the report text and individual article texts,
    deduplicating by narrative_id and keeping the strongest match.
    """
    all_matches = {}

    # Match against the main report text
    for m in match_narratives(report_text):
        nid = m["narrative_id"]
        if nid not in all_matches or m["match_count"] > all_matches[nid]["match_count"]:
            m["source"] = "report"
            all_matches[nid] = m

    # Match against individual articles
    if articles:
        for article in articles:
            article_text = article.get("full_text") or article.get("snippet") or article.get("title", "")
            for m in match_narratives(article_text):
                nid = m["narrative_id"]
                if nid not in all_matches or m["match_count"] > all_matches[nid]["match_count"]:
                    m["source"] = "article"
                    all_matches[nid] = m

    result = sorted(all_matches.values(), key=lambda m: m["match_count"], reverse=True)
    return result


def get_all_narratives() -> list:
    """Return all narratives from the database (for the /narratives endpoint)."""
    db = _load_narratives()
    result = []
    for category in db.get("categories", []):
        for narr in category.get("narratives", []):
            result.append({
                "id": narr["id"],
                "name": narr["name"],
                "category_id": category["id"],
                "category_name": category["name"],
                "description": narr.get("description", ""),
                "keywords": narr.get("keywords", []),
                "frequency": narr.get("frequency", "unknown"),
                "active": narr.get("active", True),
            })
    return result
