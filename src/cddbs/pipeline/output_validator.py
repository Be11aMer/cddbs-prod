"""AI output validation layer for CDDBS.

Validates Gemini JSON responses before they are stored in the database.
Implements grounding score computation for Topic Mode results.

OWASP LLM Top 10 — LLM02 (Insecure Output Handling)
EU AI Act — Art. 9 (Quality management), Art. 14 (Human oversight)
"""

from typing import Any


# --- Schema validation for analysis pipeline output ---

_REQUIRED_BRIEFING_FIELDS = {
    "executive_summary", "key_findings", "subject_profile",
    "narrative_analysis", "confidence_assessment", "limitations",
    "methodology",
}

_REQUIRED_TOPIC_BASELINE_FIELDS = {
    "baseline_summary", "key_facts", "neutral_framing",
}

_REQUIRED_TOPIC_COMPARATIVE_FIELDS = {
    "divergence_score", "amplification_signal", "propaganda_techniques",
    "framing_summary", "divergence_explanation",
}


class OutputValidationResult:
    """Result of validating an LLM output."""

    def __init__(self):
        self.is_valid: bool = True
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.grounding_score: float | None = None

    def add_error(self, msg: str):
        self.is_valid = False
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)


def validate_analysis_output(data: dict[str, Any]) -> OutputValidationResult:
    """Validate the structured briefing output from the analysis pipeline."""
    result = OutputValidationResult()

    if not isinstance(data, dict):
        result.add_error("Output is not a JSON object")
        return result

    # Check top-level structure
    briefing = data.get("structured_briefing")
    if not briefing:
        result.add_warning("Missing structured_briefing — legacy format")
        return result

    if not isinstance(briefing, dict):
        result.add_error("structured_briefing is not a JSON object")
        return result

    # Check required fields
    missing = _REQUIRED_BRIEFING_FIELDS - set(briefing.keys())
    for field in missing:
        result.add_error(f"Missing required field: structured_briefing.{field}")

    # Validate key_findings structure
    findings = briefing.get("key_findings", [])
    if isinstance(findings, list):
        for i, f in enumerate(findings):
            if isinstance(f, dict):
                if not f.get("finding"):
                    result.add_warning(f"key_findings[{i}] has empty finding")
                confidence = f.get("confidence", "")
                if confidence not in ("high", "moderate", "low", ""):
                    result.add_warning(f"key_findings[{i}] has invalid confidence: {confidence}")

    # Validate confidence_assessment
    conf = briefing.get("confidence_assessment")
    if isinstance(conf, dict):
        overall = conf.get("overall", "")
        if overall not in ("high", "moderate", "low", ""):
            result.add_warning(f"confidence_assessment.overall invalid: {overall}")

    # Check for suspiciously short executive summary
    exec_summary = briefing.get("executive_summary", "")
    if isinstance(exec_summary, str) and len(exec_summary) < 50:
        result.add_warning("Executive summary suspiciously short (<50 chars)")

    return result


def validate_topic_baseline(data: dict[str, Any]) -> OutputValidationResult:
    """Validate the baseline response from Topic Mode step 1."""
    result = OutputValidationResult()

    if not isinstance(data, dict):
        result.add_error("Baseline output is not a JSON object")
        return result

    missing = _REQUIRED_TOPIC_BASELINE_FIELDS - set(data.keys())
    for field in missing:
        result.add_error(f"Missing required field: {field}")

    summary = data.get("baseline_summary", "")
    if isinstance(summary, str) and len(summary) < 30:
        result.add_warning("Baseline summary suspiciously short")

    key_facts = data.get("key_facts", [])
    if not isinstance(key_facts, list) or len(key_facts) == 0:
        result.add_warning("No key_facts in baseline — grounding will be weak")

    return result


def validate_topic_comparative(data: dict[str, Any]) -> OutputValidationResult:
    """Validate a single outlet's comparative analysis result."""
    result = OutputValidationResult()

    if not isinstance(data, dict):
        result.add_error("Comparative output is not a JSON object")
        return result

    missing = _REQUIRED_TOPIC_COMPARATIVE_FIELDS - set(data.keys())
    for field in missing:
        result.add_error(f"Missing required field: {field}")

    # Validate divergence_score range
    score = data.get("divergence_score")
    if score is not None:
        try:
            score_int = int(score)
            if not 0 <= score_int <= 100:
                result.add_error(f"divergence_score out of range: {score_int}")
        except (ValueError, TypeError):
            result.add_error(f"divergence_score not an integer: {score}")

    # Validate amplification_signal enum
    amp = data.get("amplification_signal", "")
    if amp and amp not in ("low", "medium", "high"):
        result.add_warning(f"Invalid amplification_signal: {amp}")

    # Validate propaganda_techniques is a list
    techniques = data.get("propaganda_techniques")
    if techniques is not None and not isinstance(techniques, list):
        result.add_error("propaganda_techniques is not a list")

    return result


# --- Grounding score computation ---

def compute_grounding_score(
    claims: list[str],
    reference_texts: list[str],
    threshold: float = 0.3,
) -> tuple[float, list[dict]]:
    """Compute how well LLM claims are grounded in source articles.

    For each claim, computes TF-IDF cosine similarity against all reference
    texts. A claim is "grounded" if its max similarity exceeds the threshold.

    Returns:
        (grounding_score, claim_details) where grounding_score is 0.0-1.0
        and claim_details is a list of {claim, max_similarity, grounded} dicts.
    """
    if not claims:
        return 1.0, []  # No claims = fully grounded (vacuously)

    if not reference_texts:
        return 0.0, [
            {"claim": c, "max_similarity": 0.0, "grounded": False}
            for c in claims
        ]

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        # Fallback: can't compute grounding without sklearn
        return None, []

    # Build corpus: claims + reference texts
    corpus = list(claims) + list(reference_texts)
    n_claims = len(claims)

    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        # Empty vocabulary (e.g. all stop words)
        return 0.0, [
            {"claim": c, "max_similarity": 0.0, "grounded": False}
            for c in claims
        ]

    claim_vectors = tfidf_matrix[:n_claims]
    ref_vectors = tfidf_matrix[n_claims:]

    similarities = cosine_similarity(claim_vectors, ref_vectors)

    claim_details = []
    grounded_count = 0
    for i, claim in enumerate(claims):
        max_sim = float(similarities[i].max()) if similarities[i].size > 0 else 0.0
        is_grounded = max_sim >= threshold
        if is_grounded:
            grounded_count += 1
        claim_details.append({
            "claim": claim,
            "max_similarity": round(max_sim, 3),
            "grounded": is_grounded,
        })

    grounding_score = grounded_count / len(claims) if claims else 1.0
    return round(grounding_score, 3), claim_details
