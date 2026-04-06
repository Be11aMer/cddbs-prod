# CDDBS Scheduled Jobs

All automated jobs are managed by `CddbsScheduler` (`src/cddbs/scheduler.py`).
Each job has a dedicated, descriptively named environment variable so there is
no ambiguity about which job an interval controls.

---

## Jobs

### 1. Article Collector
**Env var**: `CDDBS_COLLECTOR_INTERVAL_HOURS`
**Default**: `1` hour
**What it does**: RSS + GDELT fetch → deduplication → TF-IDF clustering → Z-score burst detection → narrative risk scoring.
**Zero Gemini API cost.**

### 2. SitRep Generator
**Env var**: `CDDBS_SITREP_INTERVAL_HOURS`
**Default**: `12` hours
**What it does**: Identifies the top N high-risk, un-briefed `EventCluster` rows and calls Gemini to produce a Situational Report. If a cluster has articles from ≥3 distinct source domains or ≥2 source types, a cross-source framing analysis is embedded in the same Gemini call at no extra cost.
**Gemini cost**: max `CDDBS_SITREP_MAX_PER_CYCLE` calls per run (default 3).

**Gate conditions** — a cluster must pass both:
| Gate | Setting | Default |
|------|---------|---------|
| `narrative_risk_score >=` | `CDDBS_SITREP_MIN_RISK_SCORE` | `0.5` |
| `article_count >=` | `CDDBS_SITREP_MIN_ARTICLES` | `5` |

### 3. Daily Threat Digest
**Env var**: `CDDBS_THREAT_DIGEST_INTERVAL_HOURS`
**Default**: `24` hours
**What it does**: Aggregates recent SitReps and `NarrativeBurst` rows from the last period into an executive digest via a single compact Gemini call. If nothing was produced in the period, **no API call is made**.
**Gemini cost**: max 1 call per run.

### 4. Source Credibility Recomputation
**Env var**: `CDDBS_SOURCE_CREDIBILITY_INTERVAL_HOURS`
**Default**: `24` hours
**What it does**: Scans all domains in `raw_articles` with ≥5 articles and computes a `reliability_index` (0–1) from four signals: propaganda score (narrative risk proxy), framing divergence, coordination indicators, and burst participation. Results upserted into `source_credibility` table with trend direction tracking.
**Zero Gemini API cost** — pure local SQL aggregation.

---

## All Environment Variables

| Variable | Default | Units | Description |
|----------|---------|-------|-------------|
| `CDDBS_COLLECTOR_INTERVAL_HOURS` | `1` | hours | How often to fetch new articles from RSS + GDELT |
| `CDDBS_SITREP_INTERVAL_HOURS` | `12` | hours | How often to check for qualifying clusters and generate SitReps |
| `CDDBS_SITREP_MAX_PER_CYCLE` | `3` | count | Max SitReps generated per cycle (limits Gemini calls) |
| `CDDBS_SITREP_MIN_RISK_SCORE` | `0.5` | 0.0–1.0 | Minimum `narrative_risk_score` for a cluster to qualify for SitRep |
| `CDDBS_SITREP_MIN_ARTICLES` | `5` | count | Minimum article count in a cluster to qualify for SitRep |
| `CDDBS_THREAT_DIGEST_INTERVAL_HOURS` | `24` | hours | How often to generate the daily threat intel digest |
| `CDDBS_SOURCE_CREDIBILITY_INTERVAL_HOURS` | `24` | hours | How often to recompute domain reliability scores (zero API cost) |

---

## Monitoring

The `/scheduler/status` endpoint returns live status for all jobs:

```json
{
  "jobs": [
    {
      "name": "collector",
      "description": "RSS + GDELT article collection, dedup, clustering, burst detection",
      "interval_hours": 1.0,
      "last_run": "2026-04-01T10:00:00Z",
      "next_run": "2026-04-01T10:00:01Z",
      "run_count": 42,
      "last_error": null,
      "is_running": false
    }
  ]
}
```

---

## Production Configuration Recommendations

These are conservative free-tier defaults. When moving to paid infrastructure,
intervals can be reduced for higher freshness.

| Job | Free Tier Default | Recommended (Production) | Notes |
|-----|------------------|--------------------------|-------|
| Collector | 1h | 15–30 min | Neon DB on paid tier; GDELT data is at most ~15min stale |
| SitRep | 12h | 2–4h | Depends on Gemini API quota and how many clusters are active |
| SitRep max/cycle | 3 | 10 | At 4h interval × 10 calls = 60 Gemini calls/day max |
| SitRep min risk | 0.5 | 0.35 | Lower threshold catches emerging threats earlier |
| SitRep min articles | 5 | 3 | Smaller threshold for faster reaction to breaking news |
| Daily digest | 24h | 6–12h | Becomes "shift digest" for 24/7 analyst coverage |
| Source credibility | 24h | 6–12h | No API cost — safe to run more frequently once data volume grows |

### Neon DB Compute-Hour Budget (Free Tier: 100 hours/month)

The free tier suspends after 5 minutes of inactivity and resumes on the next
request (~500ms cold start). The backend keeps it alive via the scheduler.

| Scenario | Compute hours/month estimate |
|----------|------------------------------|
| Current (collector 1h, sitrep 12h, digest 24h) | ~40–60h |
| Higher frequency (collector 30min, sitrep 4h) | ~70–90h |
| Exceeds free tier | collector < 20min + active user sessions |

To stay within budget: keep `CDDBS_COLLECTOR_INTERVAL_HOURS >= 1` on the free tier.
