from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from src.cddbs.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=False,
    future=True
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# Columns added after initial deployment — run at startup to keep Neon schema in sync.
# Using IF NOT EXISTS so this is safe to run on every boot.
_MIGRATIONS = [
    # Sprint 8: coordination signal on topic_runs
    "ALTER TABLE topic_runs ADD COLUMN IF NOT EXISTS coordination_signal FLOAT",
    "ALTER TABLE topic_runs ADD COLUMN IF NOT EXISTS coordination_detail JSONB",
    # Sprint 8: key claims and omissions on topic_outlet_results
    "ALTER TABLE topic_outlet_results ADD COLUMN IF NOT EXISTS key_claims JSONB",
    "ALTER TABLE topic_outlet_results ADD COLUMN IF NOT EXISTS omissions JSONB",
]

def init_db():
    Base.metadata.create_all(bind=engine)
    _run_migrations()

def _run_migrations():
    """Apply additive schema migrations that create_all cannot handle."""
    with engine.begin() as conn:
        for stmt in _MIGRATIONS:
            try:
                conn.execute(text(stmt))
            except Exception as exc:
                # Log but don't crash — table may not exist yet (create_all handles it)
                print(f"Migration skipped ({exc}): {stmt}")
