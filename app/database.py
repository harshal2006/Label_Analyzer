"""
Database configuration and session management.

Uses SQLAlchemy async-compatible session factory with PostgreSQL.
All database credentials are loaded from environment variables.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

# ---------------------------------------------------------------------------
# Database URL construction
# ---------------------------------------------------------------------------
# Use SQLite for easier local development
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./nutrition_label.db")

# ---------------------------------------------------------------------------
# Engine & session
# ---------------------------------------------------------------------------
engine = create_engine(
    DATABASE_URL, 
    echo=False, 
    pool_pre_ping=True,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


# ---------------------------------------------------------------------------
# Dependency – yields a DB session per request
# ---------------------------------------------------------------------------
def get_db():
    """FastAPI dependency that provides a database session.

    Yields a SQLAlchemy session and ensures it is closed after the request,
    even if an exception occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
