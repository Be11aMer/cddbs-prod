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

## Prerequisites

```bash
# Fly.io CLI
curl -L https://fly.io/install.sh | sh
fly auth login

# Wrangler (Cloudflare Workers CLI)
npm install -g wrangler
wrangler login
```

---

## Step 1 — Deploy the GDELT proxy Worker

```bash
cd cloudflare/gdelt-proxy
npm init -y                # only needed once
npx wrangler deploy
```

Copy the Worker URL printed after deploy, e.g.:
`https://gdelt-proxy.<your-account>.workers.dev`

---

## Step 2 — Deploy the Fly.io backend

```bash
# Create the app (once)
fly apps create cddbs-api   # or any name — must be globally unique

# Set secrets (never commit these)
fly secrets set \
  DATABASE_URL="postgresql://user:pass@host/dbname?sslmode=require" \
  GOOGLE_API_KEY="AIza..." \
  SERPAPI_KEY="..." \
  ALLOWED_ORIGINS="https://cddbs-frontend.<your-account>.workers.dev" \
  GDELT_PROXY_URL="https://gdelt-proxy.<your-account>.workers.dev" \
  DB_POOL_SIZE="2" \
  DB_MAX_OVERFLOW="3"

# Deploy (from repo root)
fly deploy
```

The API will be live at `https://cddbs-api.fly.dev` (or your chosen name).

> **Neon note:** Copy the DATABASE_URL from Neon dashboard → Connection string.
> Neon uses `postgres://` — the app's `config.py` automatically rewrites it to
> `postgresql://` for SQLAlchemy.

---

## Step 3 — Deploy the frontend Worker

```bash
cd frontend
npm install

# Build with the Fly.io backend URL baked in
VITE_API_URL=https://cddbs-api.fly.dev npm run build

# Deploy
npx wrangler deploy
```

The frontend will be live at `https://cddbs-frontend.<your-account>.workers.dev`.

---

## Step 4 — Update ALLOWED_ORIGINS on the backend

After the frontend is deployed, update the backend to only accept requests from
your Cloudflare Workers domain:

```bash
fly secrets set ALLOWED_ORIGINS="https://cddbs-frontend.<your-account>.workers.dev"
fly deploy
```

---

## Subsequent deploys

**Backend only:**
```bash
fly deploy
```

**Frontend only:**
```bash
cd frontend
VITE_API_URL=https://cddbs-api.fly.dev npm run build
npx wrangler deploy
```

**GDELT proxy only:**
```bash
cd cloudflare/gdelt-proxy
npx wrangler deploy
```

---

## Environment variables reference

### Fly.io secrets (`fly secrets set KEY=VALUE`)

| Key | Description |
|-----|-------------|
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `GOOGLE_API_KEY` | Google Gemini API key |
| `SERPAPI_KEY` | SerpAPI key for news search |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins |
| `GDELT_PROXY_URL` | Cloudflare Worker URL for GDELT proxy |
| `DB_POOL_SIZE` | SQLAlchemy pool size (default 2 for free tier) |
| `DB_MAX_OVERFLOW` | Max overflow connections (default 3) |

### Cloudflare (frontend build-time)

| Key | Set via |
|-----|---------|
| `VITE_API_URL` | Shell env before `npm run build` |

---

## Keeping Render running during transition

Until DNS / links are switched, Render can stay up. Both can run in parallel
since they share the same Neon DB. The `_MIGRATIONS` in `database.py` are
idempotent — safe to run from multiple instances simultaneously.

---

## Verifying the deploy

```bash
# Backend health
curl https://cddbs-api.fly.dev/health

# Collector status (should show gdelt + rss running)
curl https://cddbs-api.fly.dev/collector/status

# GDELT proxy
curl "https://gdelt-proxy.<account>.workers.dev?query=test&mode=ArtList&maxrecords=1&format=json&timespan=1d&sort=DateDesc"
```
