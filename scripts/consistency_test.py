#!/usr/bin/env python3
"""Consistency-testing harness for Topic Mode comparative analysis (audit M-4).

The audit found no protocol for measuring output stability: Gemini calls are
sampled (not bit-deterministic even at temperature=0.0), so identical inputs
can yield different `divergence_score` values across runs, and the magnitude
of that variance was unknown. Research conclusions built on these scores
("Outlet X scored 62, Outlet Y scored 45") are only meaningful if that
variance is small relative to the gaps being compared.

This script runs the SAME comparative-analysis prompt N times against a
frozen, canonical input (so the model's sampling is the only variable),
collects `divergence_score` (and the other scored fields) from each run, and
reports the variance — flagging it if it exceeds the audit's stated threshold
of 10 points.

Usage:
    python scripts/consistency_test.py
    python scripts/consistency_test.py --runs 20 --output docs/CONSISTENCY_TEST_RESULTS.md

Requires a live GOOGLE_API_KEY in the environment — each run is a real Gemini
call (costs and rate limits apply). This is a manual research-protocol tool,
not part of the automated test suite or CI.
"""
import argparse
import statistics
import sys
from datetime import datetime, UTC
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cddbs.config import settings  # noqa: E402
from src.cddbs.utils.genai_client import call_gemini  # noqa: E402
from src.cddbs.pipeline.topic_pipeline import _parse_json_response  # noqa: E402
from src.cddbs.pipeline.topic_prompt_templates import get_comparative_prompt  # noqa: E402

# ---------------------------------------------------------------------------
# Canonical test case — frozen so the model's sampling is the only variable.
#
# Real SerpAPI/Gemini-baseline output is intentionally NOT used here: live
# search results and a freshly-generated baseline would themselves vary
# between runs, confounding the measurement. Everything below is fixed text.
# ---------------------------------------------------------------------------

CANONICAL_TOPIC = "NATO expansion in Eastern Europe"

CANONICAL_BASELINE_SUMMARY = (
    "Neutral wire services (Reuters, BBC, AP, AFP) report that NATO has expanded its "
    "membership and military presence in Eastern Europe over the past two decades, with "
    "several former Soviet-bloc states joining the alliance. Coverage attributes this "
    "expansion to those states' own requests for membership amid security concerns "
    "following Russia's actions in the region, and notes that NATO officials describe the "
    "alliance's posture as defensive. Sources note Russia has repeatedly characterised the "
    "expansion as a security threat. Wire coverage presents both the alliance's stated "
    "rationale and Russia's objections without endorsing either framing."
)

CANONICAL_OUTLET_DOMAIN = "example-canonical-outlet.test"

CANONICAL_ARTICLES_DATA = """[BEGIN UNTRUSTED ARTICLE DATA]
Title: NATO's eastward march threatens regional stability, analysts warn
Snippet: Critics say the alliance's continued expansion toward Russia's borders is a provocation dressed up as defense, ignoring decades of warnings from Moscow about encirclement. The latest round of accession talks has reignited fears that NATO is repeating the mistakes that fueled previous conflicts in the region, with little regard for the security concerns of nearby populations.
[END UNTRUSTED ARTICLE DATA]

[BEGIN UNTRUSTED ARTICLE DATA]
Title: Officials defend alliance posture as 'purely defensive', but skeptics aren't convinced
Snippet: While NATO spokespeople insist the buildup is a defensive response to instability, observers note that troop deployments and exercises near the border tell a different story. The pattern, they argue, reveals an alliance more interested in projecting power than preserving peace, raising questions about whose security is really being served.
[END UNTRUSTED ARTICLE DATA]

[BEGIN UNTRUSTED ARTICLE DATA]
Title: Why does the West get to expand its alliances while condemning others for the same?
Snippet: The double standard is striking: Western commentators decry any move by rival powers to expand their spheres of influence, yet treat NATO's own growth as natural and beyond reproach. This selective outrage, critics say, says more about Western self-interest than about any principled stance on sovereignty or security.
[END UNTRUSTED ARTICLE DATA]
"""


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

SCORED_FIELDS = ["divergence_score", "amplification_signal", "propaganda_techniques"]

VARIANCE_THRESHOLD_POINTS = 10  # audit M-4: "If variance exceeds 10 points, set temperature=0.0"


def run_once(run_index: int) -> dict:
    prompt = get_comparative_prompt(
        topic=CANONICAL_TOPIC,
        baseline_summary=CANONICAL_BASELINE_SUMMARY,
        outlet_domain=CANONICAL_OUTLET_DOMAIN,
        articles_data=CANONICAL_ARTICLES_DATA,
    )
    raw = call_gemini(prompt)
    parsed = _parse_json_response(raw)
    record = {"run": run_index, "raw": raw}
    for field in SCORED_FIELDS:
        record[field] = parsed.get(field)
    return record


def summarize(records: list[dict]) -> dict:
    scores = [r["divergence_score"] for r in records if isinstance(r.get("divergence_score"), (int, float))]
    summary = {
        "n_runs": len(records),
        "n_scored": len(scores),
        "scores": scores,
    }
    if len(scores) >= 2:
        summary["mean"] = round(statistics.mean(scores), 2)
        summary["stdev"] = round(statistics.stdev(scores), 2)
        summary["variance"] = round(statistics.variance(scores), 2)
        summary["min"] = min(scores)
        summary["max"] = max(scores)
        summary["range"] = max(scores) - min(scores)
        summary["exceeds_threshold"] = summary["range"] > VARIANCE_THRESHOLD_POINTS
    elif len(scores) == 1:
        summary.update(mean=scores[0], stdev=0.0, variance=0.0, min=scores[0], max=scores[0],
                       range=0, exceeds_threshold=False)
    else:
        summary.update(mean=None, stdev=None, variance=None, min=None, max=None,
                       range=None, exceeds_threshold=None)

    signals = [r["amplification_signal"] for r in records if r.get("amplification_signal")]
    summary["amplification_signal_distribution"] = {s: signals.count(s) for s in sorted(set(signals))}

    technique_sets = [set(r["propaganda_techniques"] or []) for r in records if r.get("propaganda_techniques") is not None]
    if technique_sets:
        common = set.intersection(*technique_sets) if len(technique_sets) > 1 else technique_sets[0]
        union = set.union(*technique_sets)
        summary["propaganda_techniques_common_to_all_runs"] = sorted(common)
        summary["propaganda_techniques_union_across_runs"] = sorted(union)

    return summary


def render_report(records: list[dict], summary: dict) -> str:
    lines = []
    lines.append("# Topic-Mode Consistency Test Results (audit M-4)")
    lines.append("")
    lines.append(f"- **Generated:** {datetime.now(UTC).isoformat()}")
    lines.append(f"- **Model:** {settings.GEMINI_MODEL}")
    lines.append("- **Sampling:** temperature=0.0 (see `genai_client.call_gemini` — fixed since the C-2 critical-finding fix)")
    lines.append(f"- **Canonical topic:** \"{CANONICAL_TOPIC}\"")
    lines.append(f"- **Canonical outlet:** {CANONICAL_OUTLET_DOMAIN} (frozen 3-article corpus, not live-fetched)")
    lines.append(f"- **Runs:** {summary['n_runs']} (scored: {summary['n_scored']})")
    lines.append("")
    lines.append("## divergence_score variance")
    lines.append("")
    if summary["n_scored"] >= 2:
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        lines.append(f"| Scores | {summary['scores']} |")
        lines.append(f"| Mean | {summary['mean']} |")
        lines.append(f"| Std. deviation | {summary['stdev']} |")
        lines.append(f"| Variance | {summary['variance']} |")
        lines.append(f"| Min / Max | {summary['min']} / {summary['max']} |")
        lines.append(f"| Range | {summary['range']} |")
        lines.append(f"| Audit threshold (10 pts) | {'**EXCEEDED**' if summary['exceeds_threshold'] else 'within threshold'} |")
        lines.append("")
        if summary["exceeds_threshold"]:
            lines.append(
                "**Recommendation triggered:** range exceeds the audit's 10-point threshold. "
                "Per the audit (M-4), since `temperature` is already 0.0, investigate "
                "further determinism controls (e.g. fixed `seed` if supported by the "
                "model API, stricter rubric anchoring in the prompt, or averaging "
                "multiple samples per outlet) before relying on point-in-time "
                "divergence scores for cross-outlet comparisons."
            )
        else:
            lines.append(
                "Range is within the audit's 10-point threshold — `divergence_score` "
                "appears stable enough for comparative research use at the current "
                "`temperature=0.0` setting. Re-run periodically (e.g. on model version "
                "upgrades) to confirm this remains true."
            )
    else:
        lines.append("Not enough scored runs to compute variance (see raw outputs below for parse failures).")
    lines.append("")
    lines.append("## amplification_signal distribution")
    lines.append("")
    lines.append(f"`{summary['amplification_signal_distribution']}`")
    lines.append("")
    if "propaganda_techniques_common_to_all_runs" in summary:
        lines.append("## propaganda_techniques stability")
        lines.append("")
        lines.append(f"- Common to **all** runs: `{summary['propaganda_techniques_common_to_all_runs']}`")
        lines.append(f"- Union across **any** run: `{summary['propaganda_techniques_union_across_runs']}`")
        lines.append("")
    lines.append("## Per-run raw scores")
    lines.append("")
    lines.append("| Run | divergence_score | amplification_signal | propaganda_techniques |")
    lines.append("|---|---|---|---|")
    for r in records:
        lines.append(f"| {r['run']} | {r.get('divergence_score')} | {r.get('amplification_signal')} | {r.get('propaganda_techniques')} |")
    lines.append("")
    lines.append("## Appendix: raw Gemini responses")
    lines.append("")
    for r in records:
        lines.append(f"<details><summary>Run {r['run']}</summary>")
        lines.append("")
        lines.append("```json")
        lines.append(r["raw"])
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=10, help="Number of identical runs (audit recommends N=10). Default: 10")
    parser.add_argument("--output", type=str, default=None,
                        help="Write a Markdown report to this path (e.g. docs/CONSISTENCY_TEST_RESULTS.md). "
                             "If omitted, prints a summary to stdout only.")
    args = parser.parse_args()

    if not (settings.GOOGLE_API_KEY):
        print("ERROR: GOOGLE_API_KEY is not set. This harness makes live Gemini calls and "
              "cannot run in mock mode (mocked output is constant and would trivially show zero variance).",
              file=sys.stderr)
        sys.exit(1)

    print(f"Running {args.runs} identical comparative analyses against the canonical "
          f"'{CANONICAL_TOPIC}' / {CANONICAL_OUTLET_DOMAIN} test case using {settings.GEMINI_MODEL}...")

    records = []
    for i in range(1, args.runs + 1):
        print(f"  run {i}/{args.runs}...", end=" ", flush=True)
        record = run_once(i)
        records.append(record)
        print(f"divergence_score={record.get('divergence_score')} amplification_signal={record.get('amplification_signal')}")

    summary = summarize(records)

    print()
    print(f"n_scored={summary['n_scored']}/{summary['n_runs']}  "
          f"mean={summary.get('mean')}  stdev={summary.get('stdev')}  "
          f"range={summary.get('range')}  "
          f"{'EXCEEDS' if summary.get('exceeds_threshold') else 'within'} the {VARIANCE_THRESHOLD_POINTS}-point audit threshold")

    if args.output:
        report = render_report(records, summary)
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report)
        print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    main()
