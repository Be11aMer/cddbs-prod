from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.cddbs.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)
