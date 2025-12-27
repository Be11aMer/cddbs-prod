# CDDBS Quick Start Guide

This guide will help you get the Cybersecurity Disinformation Detection Briefing System running locally.

## Prerequisites

- **Docker** and **Docker Compose** installed and running
- **Node.js 20+** (if running frontend locally)
- **Python 3.11+** (if running backend locally)
- API keys:
  - **SerpAPI key** ([Get one here](https://serpapi.com/users/sign_up))
  - **Google Gemini API key** ([Get one here](https://makersuite.google.com/app/apikey))

## Step 1: Clone the Repository

```bash
git clone https://codeberg.org/projectsfiae/cddbs.git
cd cddbs
```

## Step 2: Configure Environment Variables

**IMPORTANT**: The application requires a `.env` file with API keys. Without it, the application will not run.

1. Create a `.env` file in the project root. 
```env
# Database Configuration
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
POSTGRES_DB=cddbs
DATABASE_URL=postgresql+psycopg2://admin:admin@db:5432/cddbs

# API Keys (REQUIRED - Application will not run without these)
SERPAPI_KEY=your_serpapi_key_here
GOOGLE_API_KEY=your_google_gemini_api_key_here

# Optional Configuration
GEMINI_MODEL=gemini-2.5-flash
ARTICLE_LIMIT=3
```

2. Edit `.env` and replace the placeholder values with your actual API keys:


**⚠️ Friendly Reminder**: Make sure to replace `your_serpapi_key_here` and `your_google_gemini_api_key_here` with your actual API keys. The application will fail to start or run analyses without valid keys.

## Step 3: Start the Application

### Option A: Full Stack with Docker (Recommended)

This starts all services (database, backend, frontend) in containers:

```bash
docker compose up --build
```

Wait for all services to start. You should see:
- Database initialized
- Backend API running on port 8000
- Frontend running on port 5173

### Option B: Development Mode (Backend + Frontend separately)

**Backend:**
```bash
docker compose up db web
```

**Frontend** (in a new terminal):
```bash
cd frontend
npm install
npm run dev
```

## Step 4: Access the Application

Once all services are running:

- **Frontend Dashboard**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)

## Step 5: Run Your First Analysis

1. Open the frontend at `http://localhost:5173`
2. Click **"New Analysis"** button in the top bar
3. Fill in the form:
   - **Outlet**: RT
   - **Domain**: rt.com
   - **Country/Region**: Russia
   - **Number of Articles**: 5
4. Click **"Run Analysis"**
5. The analysis will appear in the runs table with status "queued" → "running" → "completed"
6. Click on a completed run to view the intelligence briefing

## Testing the API Directly

You can also test the API using curl or the Swagger UI:

### Create an Analysis Run

```bash
curl -X POST "http://localhost:8000/analysis-runs" \
  -H "Content-Type: application/json" \
  -d '{
    "outlet": "RT",
    "url": "rt.com",
    "country": "Russia",
    "num_articles": 5
  }'
```

Response:
```json
{
  "id": 1,
  "status": "queued",
  "message": "Analysis started"
}
```

### List All Runs

```bash
curl http://localhost:8000/analysis-runs
```

### Get Detailed Report

```bash
curl http://localhost:8000/analysis-runs/1
```

## Troubleshooting

### Application won't start

- **Check `.env` file exists**: Make sure you created `.env` from `.env.example`
- **Verify API keys**: Ensure `SERPAPI_KEY` and `GOOGLE_API_KEY` are set correctly
- **Check Docker**: Ensure Docker daemon is running (`docker ps` should work)

### Database connection errors

- Wait a few seconds after starting services for the database to initialize
- Check database logs: `docker compose logs db`
- Verify `.env` has correct database credentials

### Frontend can't connect to backend

- Ensure backend is running: `http://localhost:8000/health` should return `{"status": "ok"}`
- Check frontend proxy configuration in `vite.config.ts`
- In Docker, frontend automatically proxies `/api` to the backend service

### Analysis runs fail

- Verify API keys are valid and have sufficient quota
- Check backend logs: `docker compose logs web`
- Review error messages in the run detail view

## Development Tips

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f web
docker compose logs -f frontend
docker compose logs -f db
```

### Reset Database

```bash
docker compose down -v
docker compose up --build
```

### Run Tests

```bash
# Backend tests
pytest -q

# Or in Docker
docker compose exec web pytest -q
```

### Frontend Development

```bash
cd frontend
npm run dev  # Hot reload development server
npm run build  # Production build
npm run preview  # Preview production build
```

## Next Steps

- Explore the API documentation at `http://localhost:8000/docs`
- Review the code structure in `src/cddbs/` and `frontend/src/`
- Check out the pipeline stages in `src/cddbs/pipeline/`
- Read the main [README.md](./README.md) for architecture details

## Support

If you encounter issues:

1. Check the [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) guide
2. Review Docker logs for error messages
3. Verify all environment variables are set correctly
4. Ensure API keys are valid and have quota remaining

---


