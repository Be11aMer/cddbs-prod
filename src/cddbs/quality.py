"""
CDDBS Briefing Quality Scorer

Validates briefing JSON output against the 7-dimension, 70-point quality
rubric. Integrated from research Sprint 1-2.

Dimensions:
  1. Structural Completeness (0-10)
  2. Attribution Quality (0-10)
  3. Confidence Signaling (0-10)
  4. Evidence Presentation (0-10)
  5. Analytical Rigor (0-10)
  6. Actionability (0-10)
  7. Readability (0-10)
"""

import json
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "data" / "briefing_v1.json"

REQUIRED_SECTIONS = [
    "executive_summary",
    "key_findings",
    "subject_profile",
    "narrative_analysis",
    "confidence_assessment",
    "limitations",
    "methodology",
]

CONFIDENCE_LEVELS = {"high", "moderate", "low"}
EVIDENCE_TYPES = {"post", "pattern", "network", "metadata", "external", "forward", "channel_meta"}
INDICATOR_TYPES = {
    "posting_frequency",
    "language_patterns",
    "engagement_ratio",
    "coordination_signals",
    "timing_patterns",
    "content_amplification",
    "forwarding_pattern",
    "channel_growth",
    "bot_activity",
    "message_deletion",
    "other",
}


def score_structural_completeness(briefing: dict) -> tuple:
    """Dimension 1: Does the briefing contain all required sections? (0-10)"""
    score = 0
    issues = []

    section_checks = [
        ("executive_summary", "Executive summary"),
        ("key_findings", "Key findings"),
        ("subject_profile", "Subject profile"),
        ("narrative_analysis", "Narrative analysis"),
        ("confidence_assessment", "Confidence assessment"),
        ("limitations", "Limitations & caveats"),
        ("methodology", "Methodology"),
    ]

    for field, label in section_checks:
        val = briefing.get(field)
        if val and (not isinstance(val, (dict, list)) or len(val) > 0):
            score += 1
        else:
            issues.append(f"Missing or empty: {label}")

    if briefing.get("evidence_references"):
        score += 1
    else:
        issues.append("No evidence_references appendix")

    if briefing.get("metadata"):
        meta = briefing["metadata"]
        if meta.get("briefing_id") and meta.get("generated_at"):
            score += 1
        else:
            issues.append("Metadata incomplete (missing briefing_id or generated_at)")
    else:
        issues.append("Missing metadata section")

    if briefing.get("related_briefings") is not None:
        score += 1
    else:
        issues.append("No related_briefings field")

    has_xp = bool(briefing.get("cross_platform_identities"))
    has_graph = bool(briefing.get("network_graph", {}).get("nodes"))
    if has_xp or has_graph:
        score += 1

    return min(score, 10), issues


def score_attribution_quality(briefing: dict) -> tuple:
    """Dimension 2: How well are claims attributed to evidence? (0-10)"""
    score = 0
    issues = []

    findings = briefing.get("key_findings", [])
    if not findings:
        issues.append("No key findings to evaluate attribution")
        return 0, issues

    findings_with_evidence = 0
    evidence_specific = 0
    evidence_typed = 0

    for f in findings:
        evidence = f.get("evidence", [])
        if evidence:
            findings_with_evidence += 1
            for ev in evidence:
                if ev.get("type") in EVIDENCE_TYPES:
                    evidence_typed += 1
                if ev.get("reference") and len(ev["reference"]) > 20:
                    evidence_specific += 1

    total_evidence = sum(len(f.get("evidence", [])) for f in findings)

    if findings_with_evidence == len(findings):
        score += 2
    elif findings_with_evidence > 0:
        score += 1
    else:
        issues.append("No findings have evidence references")

    if total_evidence > 0:
        specificity_rate = evidence_specific / total_evidence
        if specificity_rate >= 0.8:
            score += 2
        elif specificity_rate >= 0.5:
            score += 1
            issues.append(f"Only {specificity_rate:.0%} of evidence references are specific")
        else:
            issues.append(f"Only {specificity_rate:.0%} of evidence references are specific (need >= 50%)")
    else:
        issues.append("No evidence references to evaluate specificity")

    if total_evidence > 0:
        typed_rate = evidence_typed / total_evidence
        if typed_rate >= 0.8:
            score += 2
        elif typed_rate >= 0.5:
            score += 1
            issues.append(f"Only {typed_rate:.0%} of evidence is properly typed")
        else:
            issues.append(f"Only {typed_rate:.0%} of evidence is properly typed (need >= 50%)")

    narr = briefing.get("narrative_analysis", {})
    src_attr = narr.get("source_attribution", {})
    if src_attr.get("role") and src_attr.get("content_origin"):
        score += 2
    elif src_attr:
        score += 1
        issues.append("Source attribution incomplete")
    else:
        issues.append("No source attribution in narrative analysis")

    ev_refs = briefing.get("evidence_references", [])
    if len(ev_refs) >= 3:
        score += 2
    elif ev_refs:
        score += 1
        issues.append("Evidence references appendix has fewer than 3 entries")
    else:
        issues.append("No evidence references appendix")

    return min(score, 10), issues


def score_confidence_signaling(briefing: dict) -> tuple:
    """Dimension 3: How well does the briefing communicate certainty? (0-10)"""
    score = 0
    issues = []

    conf = briefing.get("confidence_assessment", {})

    if conf.get("overall") in CONFIDENCE_LEVELS:
        score += 2
    else:
        issues.append("No valid overall confidence level")

    findings = briefing.get("key_findings", [])
    if findings:
        findings_with_confidence = sum(
            1 for f in findings if f.get("confidence") in CONFIDENCE_LEVELS
        )
        if findings_with_confidence == len(findings):
            score += 2
        elif findings_with_confidence > 0:
            score += 1
            issues.append(
                f"Only {findings_with_confidence}/{len(findings)} findings have confidence levels"
            )
        else:
            issues.append("No findings have confidence levels")

    factors = conf.get("factors", {})
    required_factors = [
        "data_completeness",
        "source_reliability",
        "analytical_consistency",
        "corroboration",
    ]
    factors_present = sum(
        1 for f in required_factors if factors.get(f) in CONFIDENCE_LEVELS
    )
    if factors_present == 4:
        score += 2
    elif factors_present >= 2:
        score += 1
        issues.append(f"Only {factors_present}/4 confidence factors documented")
    else:
        issues.append("Confidence factors not documented")

    limitations = briefing.get("limitations", {})
    alt = limitations.get("alternative_interpretations", [])
    if alt and len(alt) >= 1:
        score += 2
    else:
        issues.append("No alternative interpretations acknowledged")

    changing = limitations.get("assessment_changing_factors", [])
    if changing and len(changing) >= 1:
        score += 2
    else:
        issues.append("No assessment-changing factors stated")

    return min(score, 10), issues


def score_evidence_presentation(briefing: dict) -> tuple:
    """Dimension 4: How effectively is evidence structured? (0-10)"""
    score = 0
    issues = []

    findings = briefing.get("key_findings", [])
    total_evidence = sum(len(f.get("evidence", [])) for f in findings)

    if findings and all(f.get("evidence") for f in findings):
        score += 2
    elif findings and any(f.get("evidence") for f in findings):
        score += 1
        issues.append("Not all findings have evidence")
    else:
        issues.append("No findings have evidence")

    if total_evidence >= 3:
        score += 2
    elif total_evidence >= 1:
        score += 1
        issues.append("Fewer than 3 evidence references across all findings")
    else:
        issues.append("No evidence references")

    narr = briefing.get("narrative_analysis", {})
    indicators = narr.get("behavioral_indicators", [])
    has_metrics = any(
        any(c.isdigit() for c in ind.get("description", "")) for ind in indicators
    )
    profile = briefing.get("subject_profile", {})
    has_counts = profile.get("followers") is not None or profile.get("total_posts_analyzed") is not None

    if has_metrics and has_counts:
        score += 2
    elif has_metrics or has_counts:
        score += 1
        issues.append("Limited quantitative data")
    else:
        issues.append("No quantitative data in behavioral indicators or profile")

    evidence_types_used = set()
    for f in findings:
        for ev in f.get("evidence", []):
            evidence_types_used.add(ev.get("type"))
    if len(evidence_types_used) >= 3:
        score += 2
    elif len(evidence_types_used) >= 2:
        score += 1
        issues.append(f"Only {len(evidence_types_used)} evidence types used (3+ recommended)")
    else:
        issues.append("Only 1 evidence type used; need multiple types for robust analysis")

    ev_refs = briefing.get("evidence_references", [])
    if len(ev_refs) >= 3:
        score += 2
    elif ev_refs:
        score += 1
    else:
        issues.append("No raw data references in appendix")

    return min(score, 10), issues


def score_analytical_rigor(briefing: dict) -> tuple:
    """Dimension 5: How sound is the analytical reasoning? (0-10)"""
    score = 0
    issues = []

    narr = briefing.get("narrative_analysis", {})
    src = narr.get("source_attribution", {})
    if src.get("role"):
        score += 2
    else:
        issues.append("No role assessment (fact vs. assessment distinction unclear)")

    meta = briefing.get("metadata", {})
    period = meta.get("analysis_period", {})
    profile = briefing.get("subject_profile", {})
    if period.get("start") and period.get("end") and profile.get("total_posts_analyzed"):
        score += 2
    elif profile.get("total_posts_analyzed"):
        score += 1
        issues.append("Analysis period not fully specified")
    else:
        issues.append("Scope not bounded (missing analysis period and post count)")

    limitations = briefing.get("limitations", {})
    cannot = limitations.get("cannot_determine", [])
    gaps = limitations.get("data_gaps", [])
    if cannot and gaps:
        score += 2
    elif cannot or gaps:
        score += 1
        issues.append("Limitations partially documented")
    else:
        issues.append("No limitations documented")

    findings = briefing.get("key_findings", [])
    conf = briefing.get("confidence_assessment", {})
    if findings and conf.get("overall"):
        finding_confidences = [f.get("confidence") for f in findings if f.get("confidence")]
        if finding_confidences:
            score += 2
        else:
            issues.append("Cannot assess if conclusions follow from evidence (no finding confidence)")
    else:
        issues.append("Cannot assess analytical chain (missing findings or overall confidence)")

    alt = limitations.get("alternative_interpretations", [])
    changing = limitations.get("assessment_changing_factors", [])
    if alt and changing:
        score += 2
    elif alt or changing:
        score += 1
        issues.append("Partial bias acknowledgment (missing alternatives or changing factors)")
    else:
        issues.append("No bias acknowledgment")

    return min(score, 10), issues


def score_actionability(briefing: dict) -> tuple:
    """Dimension 6: How useful is the briefing to an analyst? (0-10)"""
    score = 0
    issues = []

    findings = briefing.get("key_findings", [])
    if findings and all(len(f.get("finding", "")) > 30 for f in findings):
        score += 2
    elif findings:
        score += 1
        issues.append("Some findings are too brief to be actionable")
    else:
        issues.append("No findings")

    conf = briefing.get("confidence_assessment", {})
    narr = briefing.get("narrative_analysis", {})
    src = narr.get("source_attribution", {})
    if conf.get("overall") and src.get("role"):
        score += 2
    elif conf.get("overall"):
        score += 1
        issues.append("Role assessment missing (hard to prioritize without it)")
    else:
        issues.append("No confidence or role assessment for prioritization")

    summary = briefing.get("executive_summary", "")
    if len(summary) >= 100:
        score += 2
    elif len(summary) >= 50:
        score += 1
        issues.append("Executive summary is brief; may lack context for non-experts")
    else:
        issues.append("Executive summary too short or missing")

    narratives = narr.get("primary_narratives", [])
    has_alignment = any(n.get("alignment") for n in narratives)
    network = narr.get("network_context", {})
    has_associations = bool(network.get("known_associations"))
    if has_alignment and has_associations:
        score += 2
    elif has_alignment or has_associations:
        score += 1
        issues.append("Limited campaign/network context")
    else:
        issues.append("No campaign alignment or network associations documented")

    meth = briefing.get("methodology", {})
    if meth.get("data_collection") and meth.get("analysis_model") and meth.get("prompt_version"):
        score += 2
    elif meth:
        score += 1
        issues.append("Methodology incomplete for reproducibility")
    else:
        issues.append("No methodology section")

    return min(score, 10), issues


def score_readability(briefing: dict) -> tuple:
    """Dimension 7: How clear and professional is the output? (0-10)"""
    score = 0
    issues = []

    present = sum(1 for s in REQUIRED_SECTIONS if briefing.get(s))
    if present == len(REQUIRED_SECTIONS):
        score += 2
    elif present >= 5:
        score += 1
        issues.append(f"Only {present}/{len(REQUIRED_SECTIONS)} required sections present")
    else:
        issues.append(f"Only {present}/{len(REQUIRED_SECTIONS)} required sections present")

    findings = briefing.get("key_findings", [])
    if findings and all(f.get("finding") and f.get("confidence") and f.get("evidence") for f in findings):
        score += 2
    elif findings:
        score += 1
        issues.append("Some findings lack required fields (finding, confidence, evidence)")
    else:
        issues.append("No findings")

    all_confidences = []
    conf = briefing.get("confidence_assessment", {})
    if conf.get("overall"):
        all_confidences.append(conf["overall"])
    for f in conf.get("factors", {}).values():
        if isinstance(f, str):
            all_confidences.append(f)
    for f in findings:
        if f.get("confidence"):
            all_confidences.append(f["confidence"])

    if all_confidences and all(c in CONFIDENCE_LEVELS for c in all_confidences):
        score += 2
    elif all_confidences:
        invalid = [c for c in all_confidences if c not in CONFIDENCE_LEVELS]
        score += 1
        issues.append(f"Non-standard confidence values: {invalid}")
    else:
        issues.append("No confidence values found")

    summary = briefing.get("executive_summary", "")
    word_count = len(summary.split())
    if 20 <= word_count <= 150:
        score += 2
    elif 10 <= word_count <= 200:
        score += 1
        issues.append(f"Executive summary length ({word_count} words) outside ideal range (20-150)")
    else:
        issues.append(f"Executive summary length ({word_count} words) is problematic")

    if 3 <= len(findings) <= 5:
        score += 2
    elif 1 <= len(findings) <= 7:
        score += 1
        issues.append(f"{len(findings)} findings (3-5 recommended)")
    else:
        issues.append(f"{len(findings)} findings (3-5 recommended)")

    return min(score, 10), issues


def score_briefing(briefing: dict) -> dict:
    """Score a briefing across all 7 dimensions. Returns scorecard dict."""
    dimensions = {
        "structural_completeness": score_structural_completeness,
        "attribution_quality": score_attribution_quality,
        "confidence_signaling": score_confidence_signaling,
        "evidence_presentation": score_evidence_presentation,
        "analytical_rigor": score_analytical_rigor,
        "actionability": score_actionability,
        "readability": score_readability,
    }

    results = {}
    total = 0

    for name, scorer in dimensions.items():
        dim_score, dim_issues = scorer(briefing)
        results[name] = {"score": dim_score, "max": 10, "issues": dim_issues}
        total += dim_score

    if total >= 60:
        rating = "Excellent"
    elif total >= 50:
        rating = "Good"
    elif total >= 40:
        rating = "Acceptable"
    elif total >= 30:
        rating = "Poor"
    else:
        rating = "Failing"

    return {
        "total_score": total,
        "max_score": 70,
        "rating": rating,
        "dimensions": results,
    }


def format_scorecard(scorecard: dict, briefing_id: str = "unknown") -> str:
    """Format a scorecard as human-readable text."""
    lines = [
        f"CDDBS Quality Scorecard — Briefing: {briefing_id}",
        "=" * 60,
        f"Total Score: {scorecard['total_score']}/{scorecard['max_score']} ({scorecard['rating']})",
        "-" * 60,
    ]

    for name, dim in scorecard["dimensions"].items():
        label = name.replace("_", " ").title()
        bar = "#" * dim["score"] + "." * (dim["max"] - dim["score"])
        lines.append(f"  {label:30s} [{bar}] {dim['score']}/{dim['max']}")
        for issue in dim["issues"]:
            lines.append(f"    - {issue}")

    lines.append("-" * 60)
    return "\n".join(lines)
