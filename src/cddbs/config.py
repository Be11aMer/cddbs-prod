import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    SERPAPI_KEY = os.getenv("SERPAPI_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    ARTICLE_LIMIT = int(os.getenv("ARTICLE_LIMIT", 3))
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://admin:admin@db:5432/cddbs")

settings = Settings()
