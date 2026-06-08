"""Propaganda technique taxonomy normalisation (audit M-1).

Gemini returns `propaganda_techniques` as free text (e.g. "Loaded language" vs
"loaded rhetoric" vs "emotionally loaded terminology" — the same construct,
different strings). The coordination signal in `topic_pipeline.py` matched
techniques with `.lower().strip()` only, so synonymous tags never collided and
the signal was systematically undercounted.

This module maps raw tags onto a closed taxonomy (`data/propaganda_techniques_taxonomy.json`,
based on the DISARM Framework and the classical propaganda-technique taxonomy)
via alias lookup, so that "loaded language" and "emotionally loaded terminology"
both normalise to the same `loaded_language` code and can be matched reliably
across outlets.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

TAXONOMY_PATH = Path(__file__).parent.parent / "data" / "propaganda_techniques_taxonomy.json"

_taxonomy_cache: Optional[dict] = None
_alias_index_cache: Optional[Dict[str, dict]] = None


def _load_taxonomy() -> dict:
    global _taxonomy_cache
    if _taxonomy_cache is None:
        with open(TAXONOMY_PATH) as f:
            _taxonomy_cache = json.load(f)
    return _taxonomy_cache


def _build_alias_index() -> Dict[str, dict]:
    """Map every lower-cased alias (and the canonical name) to its technique entry."""
    global _alias_index_cache
    if _alias_index_cache is None:
        index: Dict[str, dict] = {}
        for tech in _load_taxonomy().get("techniques", []):
            for alias in [tech["name"], *tech.get("aliases", [])]:
                index[alias.strip().lower()] = tech
        _alias_index_cache = index
    return _alias_index_cache


def normalize_technique(raw_tag: str) -> Optional[dict]:
    """Map a single raw technique tag onto the closed taxonomy.

    Matches by exact alias first, then by substring containment in either
    direction (handles minor wording variations like "use of loaded language").

    Returns a dict with `code`, `name`, and `raw`, or None if no category matches.
    """
    if not raw_tag or not raw_tag.strip():
        return None

    cleaned = raw_tag.strip().lower()
    index = _build_alias_index()

    match = index.get(cleaned)
    if match is None:
        for alias, tech in index.items():
            if alias in cleaned or cleaned in alias:
                match = tech
                break

    if match is None:
        return None

    return {"code": match["id"], "name": match["name"], "raw": raw_tag}


def normalize_techniques(raw_tags: List[str]) -> List[dict]:
    """Normalise a list of raw technique tags, dropping unmatched ones.

    Returns a list of `{code, name, raw}` dicts (one per matched tag, in order,
    duplicates by code preserved so callers can see how many raw tags mapped to
    the same category).
    """
    normalized = []
    for tag in raw_tags or []:
        result = normalize_technique(tag)
        if result:
            normalized.append(result)
    return normalized


def normalized_codes(raw_tags: List[str]) -> List[str]:
    """Convenience helper: unique normalised codes for a list of raw tags."""
    seen = []
    for entry in normalize_techniques(raw_tags):
        if entry["code"] not in seen:
            seen.append(entry["code"])
    return seen
