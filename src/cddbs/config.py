import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    SERPAPI_KEY = os.getenv("SERPAPI_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    ARTICLE_LIMIT = int(os.getenv("ARTICLE_LIMIT", 3))
    
    _db_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://admin:admin@db:5432/cddbs")
    # Render uses postgres:// but SQLAlchemy needs postgresql://
    if _db_url and _db_url.startswith("postgres://"):
        DATABASE_URL = _db_url.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URL = _db_url
        
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://cddbs-frontend.projectsfiae.workers.dev,https://cddbs-frontend.onrender.com,http://localhost:5173").split(",")
    
    # Database pooling settings
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))

    # GDELT proxy — Cloudflare Worker URL that forwards to GDELT Doc API.
    # Bypasses datacenter IP rate-limiting on Render/Fly free tiers.
    # Leave empty to hit GDELT directly (likely blocked on shared IPs).
    GDELT_PROXY_URL = os.getenv("GDELT_PROXY_URL", "")

    # Twitter/X API v2 credentials
    TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")
    TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
    TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")

    # Telegram Bot API credentials
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # ── Automated Job Scheduling ─────────────────────────────────────
    # All intervals are in HOURS. Defaults are free-tier-friendly.
    # See docs/SCHEDULING.md and docs/RESOURCE_CONSTRAINTS.md for
    # production tuning guidance.

    # Collector: how often RSS + GDELT fetch new articles
    CDDBS_COLLECTOR_INTERVAL_HOURS = float(os.getenv("CDDBS_COLLECTOR_INTERVAL_HOURS", "1"))

    # SitRep generator: how often to check for high-risk clusters and
    # generate automated threat briefings (Gemini API call)
    CDDBS_SITREP_INTERVAL_HOURS = float(os.getenv("CDDBS_SITREP_INTERVAL_HOURS", "12"))

    # SitRep budget: max briefings generated per cycle (limits API calls)
    CDDBS_SITREP_MAX_PER_CYCLE = int(os.getenv("CDDBS_SITREP_MAX_PER_CYCLE", "3"))

    # SitRep trigger: minimum narrative_risk_score to qualify
    CDDBS_SITREP_MIN_RISK_SCORE = float(os.getenv("CDDBS_SITREP_MIN_RISK_SCORE", "0.5"))

    # SitRep trigger: minimum article count in cluster to qualify
    CDDBS_SITREP_MIN_ARTICLES = int(os.getenv("CDDBS_SITREP_MIN_ARTICLES", "5"))

    # Daily threat intel digest: how often to generate (Gemini API call)
    CDDBS_THREAT_DIGEST_INTERVAL_HOURS = float(os.getenv("CDDBS_THREAT_DIGEST_INTERVAL_HOURS", "24"))

    # Source Credibility Index recomputation: how often to update per-domain scores
    # Zero Gemini cost — local aggregation only.
    CDDBS_SOURCE_CREDIBILITY_INTERVAL_HOURS = float(os.getenv("CDDBS_SOURCE_CREDIBILITY_INTERVAL_HOURS", "24"))

settings = Settings()
