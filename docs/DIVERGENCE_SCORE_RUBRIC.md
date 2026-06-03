# CDDBS Divergence Score Rubric

**Version:** 1.0  
**Date:** 2026-06-01  
**Status:** Active — used in production Topic Mode pipeline  
**Related audit finding:** C-2 (divergence score has no mathematical formula)  

---

## Overview

The `divergence_score` (0–100 integer) measures how far an outlet's coverage
of a topic deviates from a neutral wire-service baseline (Reuters, BBC, AP, AFP).
A score of 0 indicates coverage indistinguishable from the baseline.
A score of 100 indicates systematic opposition or inversion of baseline framing.

**Current implementation method:** Verbal rubric interpreted by Gemini at
`temperature=0.0`. This is Option (b) from the audit recommendation: a formally
documented rubric with deterministic execution.

**Known limitation:** This is not a mathematical formula over measurable text
features. It is an LLM-interpreted rubric. At `temperature=0.0` the output is
deterministic for a fixed model version, but not reproducible across model
versions (Gemini may silently update). Full research defensibility requires
Option (a): a deterministic formula — this is tracked as a future work item.

---

## The Five-Band Scale

| Band | Score Range | Label | Operational Definition |
|------|-------------|-------|------------------------|
| 0 | 0–15 | Aligned | Coverage consistent with wire-service framing. Key facts present, no systematic omissions, no loaded language specific to non-baseline actors. |
| 1 | 16–30 | Slightly Divergent | Minor framing differences. Emphasis or tone varies but factual content substantially matches baseline. Core claims are accurate. |
| 2 | 31–50 | Noticeable Divergence | Systematic framing shift detectable. Key baseline facts present but contextualised differently. At least one propaganda technique identifiable. |
| 3 | 51–70 | Significant Divergence | Multiple propaganda techniques present. Baseline facts selectively omitted or reframed. Narrative consistently at variance with wire services. |
| 4 | 71–100 | Strong Divergence | Systematic inversion or contradiction of baseline framing. High amplification signal. Coordination with other high-divergence outlets plausible. |

---

## Scoring Criteria

Gemini evaluates each outlet against four dimensions. Each dimension contributes
to the overall band selection:

### 1. Factual Omissions
- **0**: All key facts from baseline present
- **1**: Minor omissions, not systematic
- **2**: Notable omissions (e.g. casualty figures, official denials)
- **3**: Systematic omission of one category of facts
- **4**: Multiple categories of key facts absent

### 2. Framing and Contextualization
- **0**: Framing matches wire-service register
- **1**: Tone variation but equivalent informational content
- **2**: Consistent use of non-neutral terminology
- **3**: Loaded language pattern identifiable across articles
- **4**: Framing systematically opposed to baseline characterisation

### 3. Propaganda Technique Density
- **0**: No identifiable techniques
- **1**: Incidental technique, not systematic
- **2**: One technique used consistently (e.g. appeal to emotion)
- **3**: Two or more techniques used systematically
- **4**: Multiple techniques across all sampled articles

### 4. Amplification Signal
- **0 (low)**: Article frequency and engagement normal for topic
- **medium**: Above-baseline article frequency on this topic
- **high**: Disproportionate coverage relative to topic significance

The amplification signal is reported separately (`amplification_signal` field)
and contributes to band selection but does not mechanically determine it.

---

## Known Subjectivity Points

The following terms in the rubric prompt have subjective interpretations
that are sources of potential inter-run variance:

| Term | Operational bound (this document) |
|------|-----------------------------------|
| "key facts" | Facts present in ≥2 of the 4 reference sources |
| "systematic" | Present in ≥3 of the sampled articles for that outlet |
| "loaded language" | Terminology not used by any of the 4 reference sources to describe the same referent |
| "consistent" | Present in ≥2 of the sampled articles |

---

## Reproducibility Status

| Property | Current State |
|----------|---------------|
| Deterministic for fixed model version | ✅ (temperature=0.0) |
| Deterministic across model versions | ❌ (Gemini may silently update) |
| Mathematical derivation from text features | ❌ (future work) |
| Inter-rater reliability tested | ❌ (N=10 consistency test pending) |
| Model version logged per run | ❌ (tracked as H-4) |

---

## Planned Improvements

1. **N=10 consistency test**: Run 10 identical topic analyses on a canonical
   test case, compute variance of divergence scores, document. Target: <5 point
   standard deviation. (Blocked on live API access.)

2. **Model version logging**: Add `model_version` column to `TopicOutletResult`
   and populate with the actual model string. (H-4 fix.)

3. **Mathematical formula (Option a)**: Replace LLM rubric with a deterministic
   formula over measurable text features (TF-IDF distance from baseline,
   sentiment delta, propaganda lexicon frequency). This is the only path to
   full research defensibility for CII engagement.

---

## Citing Scores in Research Outputs

Until the Option (a) formula is implemented, all divergence scores in research
outputs **must** be annotated as follows:

> *Divergence scores are produced by an LLM-interpreted rubric (Gemini,
> temperature=0.0). They are deterministic for a fixed model version but are
> not reproducible across model updates. They should be treated as
> analyst-assistance indicators, not objective measurements.*
