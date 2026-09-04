# CDDBS Backlog

**Maintained by**: Claude Code — append entries whenever the user flags deferred work.  
**Format rule**: one entry per item, ordered by priority within each section.  
**Sprint planning**: review this file at the start of each sprint and promote items to the sprint backlog as appropriate.

---

## How to Use

When the user says anything like *"we'll do this later"*, *"not urgent but we should"*, *"push to next sprint"*, *"at some point"*, *"clean up eventually"* — add an entry here immediately without being asked. Use the template at the bottom of this file.

---

## Sprint 11 — Blockers (Must Ship Before CII Engagement)

### B-001 — Fix C-2: Divergence Score Is Stochastic
- **Priority**: CRITICAL — blocks CII engagement
- **Source**: June 2026 technical audit (C-2); confirmed still open 2026-08-24
- **What**: `call_gemini()` in `src/cddbs/utils/genai_client.py` does not use `temperature=0.0`. The divergence score (0–100) is produced by an LLM at non-zero temperature, so two identical runs return different scores. This is irreconcilable with research reproducibility.
- **Fix**: Set `temperature=0.0` in `genai_client.py`. Run the N=10 consistency test protocol (`scripts/consistency_test.py`). Document variance in `docs/CONSISTENCY_TEST_RESULTS.md`.
- **Why it matters**: Any divergence score in a published research output cannot be reproduced. CII will not accept this as methodology.

### B-002 — Fix C-3: No Retry Logic in Gemini Client
- **Priority**: CRITICAL — blocks CII engagement
- **Source**: June 2026 technical audit (C-3); confirmed still open 2026-08-24
- **What**: `call_gemini()` catches all exceptions and returns an error string. No retry, no backoff. On Gemini free tier (10 req/min), a rate-limit mid-run stores partial results with no indication they are incomplete.
- **Fix**: Implement exponential backoff with jitter (3 attempts: 2s, 4s, 8s) in `genai_client.py`. Add `analysis_status` field to `TopicOutletResult` and `Report` (set to `"partial"` or `"failed"` on Gemini error). Surface status in frontend.
- **Why it matters**: Analysts reviewing results weeks later have no way to know which analyses failed silently.

---

## Sprint 11 — High Priority

### B-003 — Clean Up Legacy Deployment Artifacts
- **Priority**: HIGH
- **Source**: User clarification 2026-08-24 — prod stays on Render; Koyeb/Fly.io experiments failed
- **What**: The repo contains artifacts from failed migration experiments:
  - `fly.toml` — Fly.io config, no longer relevant
  - `DEPLOY.md` — describes a Koyeb + Cloudflare + Neon migration that was abandoned
  - `render.yaml` — marked "deprecated" in the agent notes but it IS the active blueprint
  - References to "always-on Koyeb" in various docs
- **Fix**: Delete `fly.toml`. Rewrite `DEPLOY.md` to document the actual Render blueprint deployment. Update `render.yaml` header comment to remove "deprecated" label. Update `DEVELOPER.md` Section 10.
- **Note**: Cloudflare Workers GDELT proxy (`cloudflare/gdelt-proxy/`) stays — it's a necessary workaround for Render's inability to reach the GDELT API directly. `deploy-cloudflare.yml` CI workflow deploys this proxy only — keep it.

### B-004 — Complete AI Trust Framework (Carried from Sprint 9 → 10)
- **Priority**: HIGH
- **Source**: Sprint 9 backlog deferred items; Sprint 10 execution plan "carried from Sprint 9"
- **What**: Three AI trust features were scoped in Sprint 9, deferred to Sprint 10, and still not shipped:
  - `TrustIndicator.tsx` component (per-outlet trust badge: grounding score, calibration, reproducibility)
  - `GET /metrics/calibration` endpoint (historical divergence score accuracy tracking)
  - `reproducibility_score` field in `TopicRun` (Jaccard similarity of technique lists across two identical runs)
- **Fix**: Implement these as a single Sprint 11 sub-track. TrustIndicator depends on the reproducibility score field existing.

### B-005 — Data Retention Enforcement
- **Priority**: HIGH
- **Source**: Sprint 9 backlog (task 9.10.3); deferred to Sprint 10; still open
- **What**: `GET /compliance/retention` endpoint exists (shows retention status) but actual deletion of analysis runs older than the configurable period requires a manual trigger. Automated cleanup was deferred.
- **Fix**: Add a scheduled job to `CddbsScheduler` that flags and (after confirmation) deletes expired records. Document the data retention policy formally in a compliance doc.

### B-006 — information_security.md Compliance Document
- **Priority**: HIGH
- **Source**: Sprint 9 backlog (task 9.11.3); deferred to Sprint 10; still open
- **What**: A compliance document mapping OWASP LLM Top 10 to implemented controls, prompt injection rationale, SSRF prevention, rate limiting reasoning. Was scoped in Sprint 9, never written.
- **Fix**: Create `cddbs-research/compliance-practices/information_security.md`.

---

## Sprint 11 — Standard Housekeeping

### B-007 — Split requirements-dev.txt
- **Priority**: LOW
- **Source**: Discussion 2026-08-24 (Q6 — deferred from governance planning)
- **What**: `ruff`, `pytest`, `pytest-cov`, `cyclonedx-bom`, `pip-audit` are in `requirements.txt` alongside runtime deps. Separating them would shrink the production Docker image and give a cleaner supply chain audit surface.
- **Fix**: Create `requirements-dev.txt` with dev tools. Update `Dockerfile` to install only `requirements.txt`. Update CI workflows (test jobs install both files). Update `DEVELOPER.md`.

---

## Unscheduled — Awaiting Data Accumulation

### B-008 — Phase 4B: Disinformation Network Graph (Enhanced)
- **Priority**: DEFERRED — needs accumulated data
- **Source**: `TODO_PHASE4_NETWORK_ML.md`
- **What**: Enhanced node types (outlet, narrative, cluster), temporal slider, community detection UI.
- **Gate**: Do not implement until 3+ months of collected `EventCluster` and `NarrativeBurst` data.

### B-009 — Phase 4C: ML Predictions
- **Priority**: DEFERRED — needs accumulated data
- **Source**: `TODO_PHASE4_NETWORK_ML.md`
- **What**: Anomaly detection, campaign detection, amplification chain analysis.
- **Gate**: Do not implement until 3–6 months of data accumulation.

---

## Entry Template

```
### B-XXX — Title
- **Priority**: CRITICAL | HIGH | MEDIUM | LOW | DEFERRED
- **Source**: Where this came from (user message date, sprint, audit finding ID)
- **What**: What needs to be done, and what currently exists (if anything)
- **Fix**: Specific action required
- **Why it matters**: Impact if not done (optional, for non-obvious items)
```

---

*Last updated: 2026-08-24*