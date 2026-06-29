"""
Nutrition Label Analyzer – FastAPI Application Entry Point.

Starts the FastAPI server with Swagger documentation enabled.
Creates all database tables on startup (development convenience).

Usage:
    uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import upload as upload_router
from app.routers import report as report_router
from app.routers import admin as admin_router
from app.routers import label_checker as label_checker_router

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan – runs once on startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup (dev convenience).

    In production, swap this for Alembic migrations.
    """
    # -- Import models so Base.metadata is populated --
    import app.models  # noqa: F401

    logger.info("Creating database tables (if they don't exist)…")
    Base.metadata.create_all(bind=engine)

    yield  # Application runs here

    logger.info("Shutting down…")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Nutrition Label Analyzer",
    description=(
        "Upload a nutrition / supplement label image and get back "
        "OCR-extracted text with AI-powered ingredient analysis."
    ),
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",        # Swagger UI
    redoc_url="/redoc",      # ReDoc alternative
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS – allow the Streamlit frontend (port 8501) to call the API
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(upload_router.router)
app.include_router(report_router.router)
app.include_router(admin_router.router)
app.include_router(label_checker_router.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health-check endpoint."""
    return {"status": "healthy"}
