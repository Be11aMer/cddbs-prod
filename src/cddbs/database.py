from sqlalchemy import create_engine
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

def init_db():
    Base.metadata.create_all(bind=engine)
