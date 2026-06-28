"""
Database configuration and session management.

Uses SQLAlchemy async-compatible session factory with PostgreSQL.
All database credentials are loaded from environment variables.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

# ---------------------------------------------------------------------------
# Database URL construction
# ---------------------------------------------------------------------------
# Resolve the DB path relative to this file so it always points to the project
# root, regardless of the working directory uvicorn is launched from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB_URL = f"sqlite:///{_PROJECT_ROOT / 'nutrition_label.db'}"

DATABASE_URL: str = os.getenv("DATABASE_URL", _DEFAULT_DB_URL)

# ---------------------------------------------------------------------------
# Engine & session
# ---------------------------------------------------------------------------
_connect_args: dict = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL, 
    echo=False, 
    pool_pre_ping=True,
    connect_args=_connect_args,
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
