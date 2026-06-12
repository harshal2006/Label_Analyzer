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
# Prefer an explicit DATABASE_URL; fall back to composing from parts.
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://{user}:{password}@{host}:{port}/{name}".format(
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        name=os.getenv("DB_NAME", "nutrition_label_db"),
    ),
)

# ---------------------------------------------------------------------------
# Engine & session
# ---------------------------------------------------------------------------
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

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
