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
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import upload as upload_router
from app.routers import report as report_router
from app.services.storage_service import UPLOAD_DIR

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

    # Ensure the uploads directory exists.
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Uploads directory: %s", UPLOAD_DIR)

    yield  # Application runs here

    logger.info("Shutting down…")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Nutrition Label Analyzer",
    description=(
        "Upload a nutrition / supplement label image and get back "
        "OCR-extracted text powered by Google Cloud Vision."
    ),
    version="0.1.0",
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

# ---------------------------------------------------------------------------
# Static files – serve uploaded images (development only)
# ---------------------------------------------------------------------------
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health-check endpoint."""
    return {"status": "healthy"}
