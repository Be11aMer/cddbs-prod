# Topic-Mode Consistency Testing Protocol

**Version:** 1.0
**Date:** 2026-06-08
**Status:** Active protocol — run manually before research engagements
**Related audit finding:** M-4 (no consistency testing protocol)

---

## Why this exists

The audit noted that `divergence_score` is produced by a sampled LLM call and
that no test measured how stable that score is for identical inputs. Research
conclusions ("Outlet A scored 62, Outlet B scored 45 — A is pushing the
narrative harder") are only meaningful if the run-to-run variance for a single
outlet is small relative to the gaps being compared between outlets.

`temperature` was already reduced to `0.0` as part of the C-2 critical-finding
fix (see `src/cddbs/utils/genai_client.py`), which is the audit's own
recommended mitigation if variance turns out to be high. This protocol exists
to **measure** the resulting variance empirically and document it — temperature
alone does not guarantee bit-identical output from a hosted LLM API (batching,
infrastructure-level nondeterminism, etc. can still introduce drift), and the
model version can change over time.

## How to run it

```bash
export GOOGLE_API_KEY=<your key>
python scripts/consistency_test.py --runs 10 --output docs/CONSISTENCY_TEST_RESULTS.md
```

This runs the **same** comparative-analysis prompt `--runs` times (the audit
recommends N=10) against a frozen, canonical topic/baseline/outlet/article
corpus defined in the script — so the model's sampling behaviour is the only
variable — and writes a Markdown report containing:

- the `divergence_score` for every run, plus mean / standard deviation /
  variance / min / max / range
- a **pass/fail verdict against the audit's 10-point range threshold**
- the distribution of `amplification_signal` values across runs
- which `propaganda_techniques` tags were stable across all runs vs. which
  only appeared in some runs
- the raw Gemini response for every run, for manual inspection

This is a **manual research-protocol tool** — it makes live, billed Gemini API
calls and is intentionally not part of the automated test suite or CI
(`tests/test_consistency_harness.py` covers its analysis logic with canned
data, without live calls).

## Interpreting the result

- **Range ≤ 10 points:** scores are stable enough for comparative research use
  at the current settings. No action needed beyond periodic re-runs (e.g. when
  `GEMINI_MODEL` is upgraded).
- **Range > 10 points:** per the audit recommendation, since `temperature` is
  already at its minimum (`0.0`), investigate further determinism controls —
  e.g. a fixed `seed` if the model API supports one, tighter rubric anchoring
  in `topic_prompt_templates.get_comparative_prompt`, or averaging multiple
  samples per outlet before reporting a single score — before relying on
  point-in-time `divergence_score` values for cross-outlet comparison.

## When to run it

- Before any CII (or similar third-party research) engagement — this is
  flagged in the audit as the single highest-priority pre-engagement action.
- After any `GEMINI_MODEL` version change, since model upgrades can silently
  change sampling behaviour even at `temperature=0.0`.
- Periodically (e.g. quarterly) as a standing reliability check.

Commit the resulting `docs/CONSISTENCY_TEST_RESULTS.md` so the measured
variance is part of the project's audit trail.
