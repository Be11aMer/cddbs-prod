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


def _extract_briefing(payload: dict) -> dict:
    """Extract the structured briefing from the Gemini payload.

    The Gemini response has the form:
      { "individual_analyses": [...], "structured_briefing": {...}, "final_briefing": "..." }

    The scorer needs the structured_briefing dict. If not present, fall back
    to the top-level payload (legacy format).
    """
    sb = payload.get("structured_briefing")
    if isinstance(sb, dict) and sb:
        return sb
    return payload


def _get_findings_evidence(finding: dict) -> list[dict]:
    """Normalize finding evidence to [{type, reference}] format.

    Handles both formats:
    - Legacy: finding["evidence"] = [{type: "pattern", reference: "..."}]
    - New prompt: finding["evidence_type"] = "PATTERN", finding["evidence"] = "specific text"
    """
    ev = finding.get("evidence", [])
    if isinstance(ev, list) and ev and isinstance(ev[0], dict):
        return ev

    # New flat format
    ev_type = finding.get("evidence_type", "")
    ev_text = finding.get("evidence", "")
    if isinstance(ev_text, str) and ev_text:
        return [{"type": ev_type.lower() if ev_type else "", "reference": ev_text}]
    return []


def _get_confidence_factors(conf: dict) -> dict[str, str]:
    """Normalize confidence factors to {factor_key: level} dict.

    Handles both formats:
    - Legacy: {"data_completeness": "high", "source_reliability": "moderate", ...}
    - New prompt: [{"factor": "Data Completeness", "level": "high", "notes": "..."}]
    """
    factors = conf.get("factors", {})
    if isinstance(factors, dict):
        return factors
    if isinstance(factors, list):
        result = {}
        for f in factors:
            key = f.get("factor", "").lower().replace(" ", "_")
            level = f.get("level", "")
            if key and level:
                result[key] = level
        return result
    return {}


def _get_limitations_structured(limitations) -> dict:
    """Normalize limitations to {cannot_determine, data_gaps, alternative_interpretations, ...}.

    Handles both formats:
    - Legacy dict: {"cannot_determine": [...], "data_gaps": [...], ...}
    - New prompt: flat list of strings
    """
    if isinstance(limitations, dict):
        return limitations
    if isinstance(limitations, list):
        # Try to categorize strings heuristically
        cannot = []
        gaps = []
        alternatives = []
        changing = []
        for item in limitations:
            lower = item.lower() if isinstance(item, str) else ""
            if "cannot" in lower or "unable" in lower or "not possible" in lower:
                cannot.append(item)
            elif "gap" in lower or "missing" in lower or "no access" in lower or "unavailable" in lower:
                gaps.append(item)
            elif "alternative" in lower or "could also" in lower or "may be" in lower or "plausible" in lower:
                alternatives.append(item)
            elif "change" in lower or "new evidence" in lower or "would alter" in lower:
                changing.append(item)
            else:
                # Default to cannot_determine
                cannot.append(item)
        return {
            "cannot_determine": cannot,
            "data_gaps": gaps,
            "alternative_interpretations": alternatives,
            "assessment_changing_factors": changing,
        }
    return {}


def _get_behavioral_indicators(narr: dict) -> list[dict]:
    """Normalize behavioral indicators.

    Handles both: [{indicator_type, description}] and [{indicator, value}]
    """
    indicators = narr.get("behavioral_indicators", [])
    if not isinstance(indicators, list):
        return []
    result = []
    for ind in indicators:
        desc = ind.get("description", "") or ind.get("value", "")
        result.append({
            "indicator_type": ind.get("indicator_type", ind.get("indicator", "other")),
            "description": desc,
        })
    return result


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
        if val and (isinstance(val, str) or (isinstance(val, (dict, list)) and len(val) > 0)):
            score += 1
        else:
            issues.append(f"Missing or empty: {label}")

    # Bonus for evidence_references (optional)
    if briefing.get("evidence_references"):
        score += 1
    else:
        issues.append("No evidence_references appendix")

    # Bonus for metadata
    meta = briefing.get("metadata", {})
    if isinstance(meta, dict) and meta.get("briefing_id") and meta.get("generated_at"):
        score += 1
    elif briefing.get("methodology"):
        # Count methodology as partial metadata credit
        score += 1
    else:
        issues.append("Metadata incomplete")

    # Cap at 10
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
    total_evidence = 0

    for f in findings:
        evidence_items = _get_findings_evidence(f)
        total_evidence += len(evidence_items)
        if evidence_items:
            findings_with_evidence += 1
            for ev in evidence_items:
                if ev.get("type", "").lower() in EVIDENCE_TYPES:
                    evidence_typed += 1
                ref = ev.get("reference", "")
                if ref and len(ref) > 20:
                    evidence_specific += 1

    # All findings have evidence? (0-2)
    if findings_with_evidence == len(findings):
        score += 2
    elif findings_with_evidence > 0:
        score += 1
    else:
        issues.append("No findings have evidence references")

    # Evidence specificity (0-2)
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

    # Evidence typing (0-2)
    if total_evidence > 0:
        typed_rate = evidence_typed / total_evidence
        if typed_rate >= 0.8:
            score += 2
        elif typed_rate >= 0.5:
            score += 1
            issues.append(f"Only {typed_rate:.0%} of evidence is properly typed")
        else:
            issues.append(f"Only {typed_rate:.0%} of evidence is properly typed (need >= 50%)")

    # Source attribution (0-2)
    narr = briefing.get("narrative_analysis", {})
    src_attr = narr.get("source_attribution", {})
    if isinstance(src_attr, dict) and src_attr.get("role") and src_attr.get("content_origin"):
        score += 2
    elif isinstance(src_attr, dict) and src_attr:
        score += 1
        issues.append("Source attribution incomplete")
    else:
        issues.append("No source attribution in narrative analysis")

    # Evidence references appendix (0-2)
    ev_refs = briefing.get("evidence_references", [])
    if len(ev_refs) >= 3:
        score += 2
    elif ev_refs:
        score += 1
        issues.append("Evidence references appendix has fewer than 3 entries")
    elif total_evidence >= 3:
        # Credit inline evidence as partial substitute
        score += 1
    else:
        issues.append("No evidence references appendix")

    return min(score, 10), issues


def score_confidence_signaling(briefing: dict) -> tuple:
    """Dimension 3: How well does the briefing communicate certainty? (0-10)"""
    score = 0
    issues = []

    conf = briefing.get("confidence_assessment", {})

    # Overall confidence (0-2)
    overall = conf.get("overall", "")
    if overall and overall.lower() in CONFIDENCE_LEVELS:
        score += 2
    else:
        issues.append("No valid overall confidence level")

    # Per-finding confidence (0-2)
    findings = briefing.get("key_findings", [])
    if findings:
        findings_with_confidence = sum(
            1 for f in findings if (f.get("confidence") or "").lower() in CONFIDENCE_LEVELS
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

    # Confidence factors (0-2)
    factors = _get_confidence_factors(conf)
    required_factors = [
        "data_completeness",
        "source_reliability",
        "analytical_consistency",
        "corroboration",
    ]
    factors_present = sum(
        1 for f in required_factors
        if factors.get(f, "").lower() in CONFIDENCE_LEVELS
    )
    if factors_present == 4:
        score += 2
    elif factors_present >= 2:
        score += 1
        issues.append(f"Only {factors_present}/4 confidence factors documented")
    elif len(factors) > 0:
        # Some factors present with different names
        score += 1
        issues.append("Confidence factors use non-standard names")
    else:
        issues.append("Confidence factors not documented")

    # Alternative interpretations (0-2)
    limitations = _get_limitations_structured(briefing.get("limitations"))
    alt = limitations.get("alternative_interpretations", [])
    if alt and len(alt) >= 1:
        score += 2
    elif isinstance(briefing.get("limitations"), list) and len(briefing.get("limitations", [])) >= 2:
        # Flat list with 2+ items gets partial credit
        score += 1
    else:
        issues.append("No alternative interpretations acknowledged")

    # Assessment-changing factors (0-2)
    changing = limitations.get("assessment_changing_factors", [])
    if changing and len(changing) >= 1:
        score += 2
    elif isinstance(briefing.get("limitations"), list) and len(briefing.get("limitations", [])) >= 3:
        score += 1
    else:
        issues.append("No assessment-changing factors stated")

    return min(score, 10), issues


def score_evidence_presentation(briefing: dict) -> tuple:
    """Dimension 4: How effectively is evidence structured? (0-10)"""
    score = 0
    issues = []

    findings = briefing.get("key_findings", [])
    total_evidence = 0

    for f in findings:
        total_evidence += len(_get_findings_evidence(f))

    # All findings have evidence (0-2)
    if findings and all(_get_findings_evidence(f) for f in findings):
        score += 2
    elif findings and any(_get_findings_evidence(f) for f in findings):
        score += 1
        issues.append("Not all findings have evidence")
    else:
        issues.append("No findings have evidence")

    # Total evidence count (0-2)
    if total_evidence >= 3:
        score += 2
    elif total_evidence >= 1:
        score += 1
        issues.append("Fewer than 3 evidence references across all findings")
    else:
        issues.append("No evidence references")

    # Quantitative data (0-2)
    narr = briefing.get("narrative_analysis", {})
    indicators = _get_behavioral_indicators(narr)
    has_metrics = any(
        any(c.isdigit() for c in ind.get("description", "")) for ind in indicators
    )
    profile = briefing.get("subject_profile", {})
    has_counts = (
        profile.get("followers") is not None
        or profile.get("total_posts_analyzed") is not None
        or profile.get("articles_analyzed") is not None
    )

    if has_metrics and has_counts:
        score += 2
    elif has_metrics or has_counts:
        score += 1
        issues.append("Limited quantitative data")
    else:
        issues.append("No quantitative data in behavioral indicators or profile")

    # Evidence type diversity (0-2)
    evidence_types_used = set()
    for f in findings:
        for ev in _get_findings_evidence(f):
            t = ev.get("type", "").lower()
            if t:
                evidence_types_used.add(t)
    if len(evidence_types_used) >= 3:
        score += 2
    elif len(evidence_types_used) >= 2:
        score += 1
        issues.append(f"Only {len(evidence_types_used)} evidence types used (3+ recommended)")
    elif len(evidence_types_used) == 1:
        issues.append("Only 1 evidence type used; need multiple types for robust analysis")

    # Evidence references appendix (0-2)
    ev_refs = briefing.get("evidence_references", [])
    if len(ev_refs) >= 3:
        score += 2
    elif ev_refs or total_evidence >= 3:
        score += 1
    else:
        issues.append("No raw data references in appendix")

    return min(score, 10), issues


def score_analytical_rigor(briefing: dict) -> tuple:
    """Dimension 5: How sound is the analytical reasoning? (0-10)"""
    score = 0
    issues = []

    # Source role assessment (0-2)
    narr = briefing.get("narrative_analysis", {})
    src = narr.get("source_attribution", {})
    if isinstance(src, dict) and src.get("role"):
        score += 2
    else:
        issues.append("No role assessment (fact vs. assessment distinction unclear)")

    # Scope bounding (0-2)
    meth = briefing.get("methodology", {})
    profile = briefing.get("subject_profile", {})
    has_period = bool(
        meth.get("analysis_period")
        or (meth.get("start") and meth.get("end"))
        or profile.get("analysis_period")
    )
    has_count = bool(
        profile.get("total_posts_analyzed")
        or profile.get("articles_analyzed")
        or meth.get("articles_analyzed")
    )
    if has_period and has_count:
        score += 2
    elif has_period or has_count:
        score += 1
        issues.append("Scope partially bounded")
    else:
        issues.append("Scope not bounded (missing analysis period and count)")

    # Limitations documentation (0-2)
    limitations = _get_limitations_structured(briefing.get("limitations"))
    cannot = limitations.get("cannot_determine", [])
    gaps = limitations.get("data_gaps", [])
    raw_limitations = briefing.get("limitations")
    if cannot and gaps:
        score += 2
    elif cannot or gaps:
        score += 1
        issues.append("Limitations partially documented")
    elif isinstance(raw_limitations, list) and len(raw_limitations) >= 2:
        # Flat list of limitations still shows awareness
        score += 2
    elif isinstance(raw_limitations, list) and len(raw_limitations) >= 1:
        score += 1
        issues.append("Limited limitations documentation")
    else:
        issues.append("No limitations documented")

    # Analytical chain (0-2)
    findings = briefing.get("key_findings", [])
    conf = briefing.get("confidence_assessment", {})
    if findings and conf.get("overall"):
        finding_confidences = [
            f.get("confidence") for f in findings if f.get("confidence")
        ]
        if finding_confidences:
            score += 2
        else:
            issues.append("Cannot assess if conclusions follow from evidence (no finding confidence)")
    else:
        issues.append("Cannot assess analytical chain (missing findings or overall confidence)")

    # Bias acknowledgment (0-2)
    alt = limitations.get("alternative_interpretations", [])
    changing = limitations.get("assessment_changing_factors", [])
    if alt and changing:
        score += 2
    elif alt or changing:
        score += 1
        issues.append("Partial bias acknowledgment")
    elif isinstance(raw_limitations, list) and len(raw_limitations) >= 3:
        # Comprehensive flat list shows bias awareness
        score += 1
    else:
        issues.append("No bias acknowledgment")

    return min(score, 10), issues


def score_actionability(briefing: dict) -> tuple:
    """Dimension 6: How useful is the briefing to an analyst? (0-10)"""
    score = 0
    issues = []

    # Actionable findings (0-2)
    findings = briefing.get("key_findings", [])
    if findings and all(len(f.get("finding", "")) > 30 for f in findings):
        score += 2
    elif findings:
        score += 1
        issues.append("Some findings are too brief to be actionable")
    else:
        issues.append("No findings")

    # Prioritization aids (0-2)
    conf = briefing.get("confidence_assessment", {})
    narr = briefing.get("narrative_analysis", {})
    src = narr.get("source_attribution", {})
    if conf.get("overall") and isinstance(src, dict) and src.get("role"):
        score += 2
    elif conf.get("overall"):
        score += 1
        issues.append("Role assessment missing (hard to prioritize without it)")
    else:
        issues.append("No confidence or role assessment for prioritization")

    # Executive summary quality (0-2)
    summary = briefing.get("executive_summary", "")
    if isinstance(summary, str) and len(summary) >= 100:
        score += 2
    elif isinstance(summary, str) and len(summary) >= 50:
        score += 1
        issues.append("Executive summary is brief; may lack context for non-experts")
    else:
        issues.append("Executive summary too short or missing")

    # Campaign/network context (0-2)
    narratives = narr.get("primary_narratives", [])
    has_alignment = any(n.get("alignment") for n in narratives) if isinstance(narratives, list) else False
    network = narr.get("network_context", {})
    has_associations = False
    if isinstance(network, dict):
        has_associations = bool(network.get("known_associations"))
    elif isinstance(network, list) and network:
        has_associations = True
    if has_alignment and has_associations:
        score += 2
    elif has_alignment or has_associations:
        score += 1
        issues.append("Limited campaign/network context")
    else:
        issues.append("No campaign alignment or network associations documented")

    # Methodology (0-2)
    meth = briefing.get("methodology", {})
    if isinstance(meth, dict) and meth.get("data_collection") and (meth.get("analysis_model") or meth.get("prompt_version")):
        score += 2
    elif isinstance(meth, dict) and meth:
        score += 1
        issues.append("Methodology incomplete for reproducibility")
    else:
        issues.append("No methodology section")

    return min(score, 10), issues


def score_readability(briefing: dict) -> tuple:
    """Dimension 7: How clear and professional is the output? (0-10)"""
    score = 0
    issues = []

    # Section coverage (0-2)
    present = sum(
        1 for s in REQUIRED_SECTIONS
        if briefing.get(s) and (
            isinstance(briefing[s], str) or
            (isinstance(briefing[s], (dict, list)) and len(briefing[s]) > 0)
        )
    )
    if present == len(REQUIRED_SECTIONS):
        score += 2
    elif present >= 5:
        score += 1
        issues.append(f"Only {present}/{len(REQUIRED_SECTIONS)} required sections present")
    else:
        issues.append(f"Only {present}/{len(REQUIRED_SECTIONS)} required sections present")

    # Finding format consistency (0-2)
    findings = briefing.get("key_findings", [])
    if findings and all(
        f.get("finding") and f.get("confidence") and (_get_findings_evidence(f))
        for f in findings
    ):
        score += 2
    elif findings:
        score += 1
        issues.append("Some findings lack required fields (finding, confidence, evidence)")
    else:
        issues.append("No findings")

    # Confidence value consistency (0-2)
    all_confidences = []
    conf = briefing.get("confidence_assessment", {})
    if conf.get("overall"):
        all_confidences.append(conf["overall"].lower() if isinstance(conf["overall"], str) else "")

    factors = _get_confidence_factors(conf)
    for v in factors.values():
        if isinstance(v, str):
            all_confidences.append(v.lower())

    for f in findings:
        c = f.get("confidence", "")
        if c:
            all_confidences.append(c.lower() if isinstance(c, str) else "")

    if all_confidences and all(c in CONFIDENCE_LEVELS for c in all_confidences):
        score += 2
    elif all_confidences:
        invalid = [c for c in all_confidences if c not in CONFIDENCE_LEVELS]
        score += 1
        if invalid:
            issues.append(f"Non-standard confidence values: {invalid}")
    else:
        issues.append("No confidence values found")

    # Executive summary length (0-2)
    summary = briefing.get("executive_summary", "")
    word_count = len(summary.split()) if isinstance(summary, str) else 0
    if 20 <= word_count <= 150:
        score += 2
    elif 10 <= word_count <= 200:
        score += 1
        issues.append(f"Executive summary length ({word_count} words) outside ideal range (20-150)")
    else:
        issues.append(f"Executive summary length ({word_count} words) is problematic")

    # Finding count (0-2)
    if 3 <= len(findings) <= 5:
        score += 2
    elif 1 <= len(findings) <= 7:
        score += 1
        issues.append(f"{len(findings)} findings (3-5 recommended)")
    else:
        issues.append(f"{len(findings)} findings (3-5 recommended)")

    return min(score, 10), issues


def score_briefing(payload: dict) -> dict:
    """Score a briefing across all 7 dimensions. Returns scorecard dict.

    Accepts either the full Gemini response payload (with structured_briefing
    nested inside) or a standalone briefing dict with top-level sections.
    """
    briefing = _extract_briefing(payload)

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
