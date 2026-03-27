# Deployment Guide — Migrating off Render

## Architecture after migration

```
Browser → Cloudflare Worker (frontend SPA)
              ↓ VITE_API_URL
         Fly.io (FastAPI backend, always-on)
              ↓ DATABASE_URL
         Neon (PostgreSQL, unchanged)

Backend → Cloudflare Worker (GDELT proxy)
              ↓
         api.gdeltproject.org
```

**Why Fly.io over Render free tier:**
- No cold starts (`auto_stop_machines = "off"`)
- Asyncio scheduler runs continuously → burst detection accumulates data
- 256MB shared VM, always alive

**Why Cloudflare Workers over Pages for the frontend:**
- `not_found_handling: "single-page-application"` in `wrangler.jsonc` handles SPA
  routing in the Worker runtime — no `_redirects` file, no infinite loops
- Workers are the modern Cloudflare primitive; Pages is built on top of them

---

## No CLI required — everything via dashboards + GitHub Actions

Subsequent deploys happen automatically on push to `main` via GitHub Actions
(`.github/workflows/deploy-cloudflare.yml`). The one-time setup below uses
dashboards only.

---

## Step 1 — Deploy the GDELT proxy Worker (Cloudflare dashboard)

The GDELT proxy is a single JS file — easiest to create directly in the dashboard:

1. Go to **Cloudflare dashboard → Workers & Pages → Create**
2. Choose **"Hello World"** starter, name it `gdelt-proxy`, click Deploy
3. Click **"Edit code"**, replace everything with the contents of
   `cloudflare/gdelt-proxy/src/index.js` from this repo, click **Deploy**
4. Copy the Worker URL — e.g. `https://gdelt-proxy.<your-account>.workers.dev`

---

## Step 2 — Deploy the Fly.io backend (Fly.io dashboard)

1. Go to **fly.io/dashboard → New app → Deploy from GitHub**
2. Select repository: `Be11aMer/cddbs-prod`
3. Branch: `main` (after merging the migration branch)
4. **Current Working Directory**: leave blank (fly.toml is at repo root)
5. **Config path**: leave blank (defaults to `fly.toml`)
6. Click **Deploy**

After the first deploy completes, set secrets via **Fly.io dashboard → your app → Secrets**:

| Secret | Value |
|--------|-------|
| `DATABASE_URL` | Neon connection string (from Neon dashboard → Connection string) |
| `GOOGLE_API_KEY` | Your Google Gemini API key |
| `SERPAPI_KEY` | Your SerpAPI key |
| `GDELT_PROXY_URL` | `https://gdelt-proxy.<your-account>.workers.dev` (from Step 1) |
| `ALLOWED_ORIGINS` | `https://cddbs-frontend.<your-account>.workers.dev` (set after Step 3) |

> **Neon note:** Neon shows `postgres://` in the dashboard — the app's `config.py`
> automatically rewrites it to `postgresql://` for SQLAlchemy. Paste as-is.

Fly.io redeploys automatically on every push to `main` going forward.

---

## Step 3 — Deploy the frontend + GDELT proxy Workers (GitHub Actions)

The `deploy-cloudflare.yml` workflow builds and deploys both Workers on every
push to `main`. It needs three secrets added to GitHub once:

1. Go to **GitHub → cddbs-prod → Settings → Secrets and variables → Actions**
2. Add these three repository secrets:

| Secret | Where to find it |
|--------|-----------------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare dashboard → My Profile → API Tokens → Create Token → use the **"Edit Cloudflare Workers"** template |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare dashboard → any page → right sidebar under "Account ID" |
| `VITE_API_URL` | `https://cddbs-api.fly.dev` (your Fly.io app URL from Step 2) |

3. Push or merge to `main` — GitHub Actions triggers the deployment automatically.
4. The frontend Worker URL will be printed in the Actions logs:
   `https://cddbs-frontend.<your-account>.workers.dev`

---

## Step 4 — Update ALLOWED_ORIGINS

Once you have the frontend Worker URL from Step 3:

Go to **Fly.io dashboard → cddbs-api → Secrets** and update:

```
ALLOWED_ORIGINS = https://cddbs-frontend.<your-account>.workers.dev
```

Fly.io will restart the app automatically.

---

## Step 5 — Verify, then delete Render services

```bash
# Backend health
curl https://cddbs-api.fly.dev/health

# Collector status (gdelt should now work via proxy)
curl https://cddbs-api.fly.dev/collector/status

# Open the frontend Worker URL in a browser
https://cddbs-frontend.<your-account>.workers.dev
```

Once verified → **Render dashboard → delete both services** (cddbs-api and cddbs-frontend).

---

## Environment variables reference

### Fly.io secrets (set in Fly.io dashboard → app → Secrets)

| Key | Description |
|-----|-------------|
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `GOOGLE_API_KEY` | Google Gemini API key |
| `SERPAPI_KEY` | SerpAPI key for news search |
| `ALLOWED_ORIGINS` | Cloudflare Workers frontend URL (comma-separated) |
| `GDELT_PROXY_URL` | Cloudflare Worker URL for GDELT proxy |
| `DB_POOL_SIZE` | SQLAlchemy pool size (default `2` for free tier) |
| `DB_MAX_OVERFLOW` | Max overflow connections (default `3`) |

### GitHub Actions secrets (set in GitHub → Settings → Secrets → Actions)

| Key | Description |
|-----|-------------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token with Workers edit permissions |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account ID |
| `VITE_API_URL` | Fly.io backend URL baked into the frontend build |

---

## Keeping Render running during transition

Both can run in parallel — they share the same Neon DB. The `_MIGRATIONS` in
`database.py` are idempotent, safe to run from multiple instances simultaneously.
Only delete Render after verifying the new stack works end-to-end.
