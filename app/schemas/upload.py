"""
Pydantic schemas for the upload / analysis workflow.

Schemas enforce strict type checking on both request payloads and API
responses. They are intentionally decoupled from the ORM models so the
API contract can evolve independently of the database layer.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Upload schemas
# ---------------------------------------------------------------------------

class NutrientItem(BaseModel):
    """A single parsed nutrient with its per-serving value."""

    name: str = Field(..., description="Nutrient name (e.g. Protein, Sodium)")
    value: float = Field(..., description="Numeric value per serving")
    unit: str = Field("", description="Unit of measurement (g, mg, kcal, etc.)")


# ---------------------------------------------------------------------------
# Ingredient analysis schemas (from Groq LLM)
# ---------------------------------------------------------------------------

class HarmfulFlags(BaseModel):
    """Health risk flags for specific conditions."""

    diabetes: bool = False
    kidney: bool = False
    pregnancy: bool = False


class IngredientDetail(BaseModel):
    """A single ingredient with its analysis."""

    name: str = Field(..., description="Ingredient name (in English)")
    purpose: str = Field("", description="What this ingredient does")
    harmful_flags: HarmfulFlags = Field(default_factory=HarmfulFlags)
    is_allergen: bool = False
    allergen_type: str | None = None


class IngredientAnalysis(BaseModel):
    """Full ingredient analysis from the Groq LLM."""

    ingredients: list[IngredientDetail] = Field(default_factory=list)
    overall_health_score: int = Field(0, ge=0, le=10)
    health_score_reasoning: str = ""
    summary: str = ""
    warnings: list[str] = Field(default_factory=list)
    ocr_quality_issue: bool = False
    low_confidence_items: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API response
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    """Returned after a successful image upload + OCR + analysis run."""

    success: bool = Field(default=True, description="Whether the operation succeeded")
    upload_id: int = Field(..., description="Primary key of the upload record")
    image_path: str = Field(..., description="Relative path to the stored image")
    ocr_text: str | None = Field(None, description="Extracted text from OCR (may be empty)")
    nutrients: list[NutrientItem] = Field(
        default_factory=list,
        description="Structured nutrient data parsed from the OCR text",
    )
    analysis: IngredientAnalysis | None = Field(
        None,
        description="LLM-powered ingredient analysis (None if Groq API unavailable)",
    )

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
