# Deployment Guide — Off Render

## Architecture

```
Browser → Cloudflare Worker (frontend SPA)   ← already live
              ↓ VITE_API_URL
         Koyeb (FastAPI backend, always-on)   ← deploy this next
              ↓ DATABASE_URL
         Neon (PostgreSQL, unchanged)

Backend → Cloudflare Worker (GDELT proxy)    ← already live
              ↓
         api.gdeltproject.org
```

**Why Koyeb for the backend:**
- Always-on free tier — no cold starts, no credit card required
- Frankfurt region — same city as Neon (AWS eu-central-1)
- Reads the existing `Dockerfile` directly, no extra config file needed
- Asyncio scheduler runs continuously → burst detection and GDELT collection work

---

## Step 1 — Deploy backend to Koyeb

1. Go to **koyeb.com** → sign up (no credit card required)
2. **Create Service → GitHub** → authorise → select `Be11aMer/cddbs-prod`
3. Fill in the service settings:

| Field | Value |
|---|---|
| Branch | `main` |
| Builder | Dockerfile *(auto-detected)* |
| Port | `8000` |
| Region | **Frankfurt** |
| Instance type | **Free (nano)** |
| Health check path | `/health` |

4. Add **Environment Variables** (Koyeb dashboard → Service → Environment):

| Key | Value |
|---|---|
| `DATABASE_URL` | Neon connection string *(from Neon dashboard → Connection string)* |
| `GOOGLE_API_KEY` | Your Google Gemini API key |
| `SERPAPI_KEY` | Your SerpAPI key |
| `GDELT_PROXY_URL` | `https://gdelt-proxy.<your-account>.workers.dev` |
| `ALLOWED_ORIGINS` | `https://cddbs-frontend.<your-account>.workers.dev` |
| `PYTHONPATH` | `/app` |
| `DB_POOL_SIZE` | `2` |
| `DB_MAX_OVERFLOW` | `3` |

> **Neon note:** Neon shows `postgres://` — `config.py` rewrites it to
> `postgresql://` automatically. Paste the connection string as-is.

5. Click **Deploy**. Koyeb assigns a URL like:
   `https://cddbs-prod-<hash>.koyeb.app`

6. Verify: `curl https://cddeb-prod-<hash>.koyeb.app/health`

---

## Step 2 — Wire the frontend to Koyeb

Update the `VITE_API_URL` GitHub secret with the Koyeb URL:

1. **GitHub → cddbs-prod → Settings → Secrets and variables → Actions**
2. Edit `VITE_API_URL` → set to `https://cddbs-prod-<hash>.koyeb.app`
3. Go to **Actions → Deploy to Cloudflare Workers → Run workflow** to
   trigger a redeploy with the new backend URL baked in.

---

## Step 3 — Delete Render services

Once the Koyeb backend and Cloudflare frontend are verified working:

- **Render dashboard → cddbs-api → Delete service**
- **Render dashboard → cddbs-frontend → Delete service**

Both can run in parallel during the transition — they share the same Neon DB
and `database.py` migrations are idempotent.

---

## Subsequent deploys

| What changed | Action |
|---|---|
| Backend code | Push to `main` — Koyeb auto-deploys from GitHub |
| Frontend code | Push to `main` — GitHub Actions redeploys Cloudflare Worker |
| GDELT proxy code | Push to `main` — GitHub Actions redeploys Cloudflare Worker |
| Backend env vars | Koyeb dashboard → Service → Environment → redeploy |

---

## GitHub Actions secrets (one-time setup)

Set in **GitHub → cddbs-prod → Settings → Secrets and variables → Actions**:

| Secret | Description |
|---|---|
| `CLOUDFLARE_API_TOKEN` | Custom token: Workers Scripts + KV Storage + Account Settings (Edit) |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare dashboard → right sidebar |
| `VITE_API_URL` | Koyeb backend URL (`https://cddbs-prod-<hash>.koyeb.app`) |

---

## Verifying everything works

```
# Backend
curl https://cddbs-prod-<hash>.koyeb.app/health
curl https://cddbs-prod-<hash>.koyeb.app/collector/status

# Frontend
open https://cddbs-frontend.<your-account>.workers.dev

# GDELT proxy
curl "https://gdelt-proxy.<your-account>.workers.dev?query=disinformation&mode=ArtList&maxrecords=1&format=json&timespan=1d&sort=DateDesc"
```
