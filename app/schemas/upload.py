"""
Pydantic schemas for the upload / analysis workflow.

Schemas enforce strict type checking on both request payloads and API
responses. They are intentionally decoupled from the ORM models so the
API contract can evolve independently of the database layer.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Upload schemas
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    """Returned after a successful image upload + OCR run."""

    success: bool = Field(default=True, description="Whether the operation succeeded")
    upload_id: int = Field(..., description="Primary key of the upload record")
    image_path: str = Field(..., description="Relative path to the stored image")
    ocr_text: str | None = Field(None, description="Extracted text from OCR (may be empty)")

    model_config = ConfigDict(from_attributes=True)


class UploadDetail(BaseModel):
    """Extended upload detail (for future GET endpoints)."""

    id: int
    user_id: int | None = None
    image_path: str
    uploaded_at: datetime
    ocr_text: str | None = None
    health_score: float | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Generic error response
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """Standard error envelope."""

    success: bool = Field(default=False)
    detail: str = Field(..., description="Human-readable error description")
