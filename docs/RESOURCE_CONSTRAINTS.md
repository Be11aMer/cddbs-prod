# CDDBS Resource Constraints

This document describes the resource budget assumptions baked into the
automated pipeline and provides guidance for tuning when moving off free-tier
infrastructure.

---

## Free-Tier Stack (Current Deployment)

| Service | Plan | Limit |
|---------|------|-------|
| **Neon DB** | Free | 100 compute-hours/month, 512 MB storage, 0.25 vCPU |
| **Gemini API** | Free | 1,500 requests/day, 1,000,000 tokens/day |
| **Render (backend)** | Free | Spins down after 15min inactivity; ~750 free hours/month |
| **Cloudflare Workers (frontend)** | Free | 100,000 requests/day |

---

## Daily Gemini Budget

| Feature | Calls/day | Tokens/day (approx.) | Trigger |
|---------|-----------|----------------------|---------|
| Manual outlet analysis | Variable (user-driven) | ~3,000/call | On demand |
| Manual topic analysis | Variable | ~5,000/call | On demand |
| SitRep generator | ≤6 (3 calls × 2 cycles) | ~8,000 | Scheduled, 12h interval |
| Daily digest | ≤1 | ~800 | Scheduled, 24h interval |
| **Automated total** | **≤7** | **~9,000** | — |
| **Free tier budget** | **1,500** | **1,000,000** | — |
| **% of budget used** | **<1%** | **<1%** | — |

The automated pipeline uses less than 1% of the Gemini free-tier allowance.
Manual analyses are the primary consumer.

---

## SitRep Token Sizing

SitRep prompts are intentionally compact — much shorter than the full outlet
analysis prompt:

| Prompt type | Input tokens (approx.) | Output tokens (approx.) |
|-------------|------------------------|--------------------------|
| Full outlet analysis | ~2,000 | ~3,000 |
| SitRep (with framing) | ~500–700 | ~800–1,000 |
| Daily digest | ~300 | ~500 |
| Quarterly report | ~600 | ~1,200 |

This is achieved by:
- Capping articles at 20 per cluster (truncated to 300 chars each)
- Piggybacking framing analysis into the same call when warranted (≥3 sources or ≥2 source types)
- Digests summarise existing AI outputs (SitReps), not raw articles

---

## Neon DB Compute Hours

The free tier grants **100 compute-hours/month**. The DB suspends after 5
minutes of inactivity (cold start ~500ms).

**Estimation methodology**: Each scheduler wakeup keeps the DB active for
~1–2 minutes. With a 1h collector interval that is ~48 wakeups/day × 2min =
~96 minutes/day = ~48 hours/month from the scheduler alone. User sessions add
to this.

**Mitigation already in place**:
- `DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=10` to limit concurrent connections
- Backend pinging via CI keep-alive workflow prevents full suspension during
  active use periods (see `.github/workflows/keep-alive.yml`)

---

## Production Scaling Guidance

When moving to paid tiers, the following changes unlock significantly higher
data freshness with manageable cost:

### Gemini API (Pay-as-you-go)

Gemini 2.5 Flash pricing (as of Q1 2026):
- Input: $0.075 / 1M tokens
- Output: $0.30 / 1M tokens

At maximum production load (10 SitReps/cycle × 4 cycles/day + 4 digests/day):
- SitReps: 40 calls × ~1,500 tokens avg = 60K tokens/day → **< $0.02/day**
- Digests: 4 calls × ~800 tokens = 3.2K tokens/day → **< $0.001/day**
- **Total automated cost: < $0.50/month** at aggressive settings

### Database (Neon paid / Supabase / RDS)

Move to a persistent compute plan when:
- Collector interval drops below 30 minutes (cold start latency becomes noticeable)
- Storage exceeds 512 MB (approximately 6–12 months of full collection)

### Render / Fly.io (Backend)

The backend is stateless — any container host works. The Render free tier is
kept alive by the CI keep-alive workflow; for production, move to a paid
instance to eliminate cold starts entirely.

---

## What NOT to Automate (Free Tier)

- **Per-article Gemini analysis**: Do not run Gemini on every ingested
  `RawArticle`. The two-gate system (risk score + article count) ensures
  Gemini is only called for clusters that have already been statistically
  validated as significant.
- **Real-time SitRep generation**: SitRep generation runs on a schedule, not
  in response to individual article ingestion events. This is intentional.
- **Framing analysis as a standalone job**: Framing is always piggybacked on
  SitRep generation to avoid a second Gemini call.
