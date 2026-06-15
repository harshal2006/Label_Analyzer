"""
Upload router – ``POST /upload``

Accepts a multipart image upload, persists it to disk, runs OCR via
PaddleOCR, analyzes ingredients via Groq LLM, and stores the results
in the database.
"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.analysis import AnalysisResult
from app.models.upload import Upload
from app.schemas.upload import ErrorResponse, IngredientAnalysis, UploadResponse
from app.services import analysis_service, ocr_service, storage_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Upload"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a nutrition-label image",
    description=(
        "Upload a JPG, JPEG, PNG, or WebP image of a nutrition label. "
        "The server stores the image, runs OCR, analyzes ingredients via "
        "Groq LLM, and returns the extracted text with analysis."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file type"},
        500: {"model": ErrorResponse, "description": "OCR or database failure"},
    },
)
async def upload_image(
    file: UploadFile = File(..., description="Nutrition-label image file"),
    db: Session = Depends(get_db),
) -> UploadResponse:
    """Handle an image upload and return OCR + analysis results.

    Workflow
    --------
    1. Validate the file extension.
    2. Save the image to ``uploads/`` with a UUID filename.
    3. Create an ``Upload`` record in the database.
    4. Run PaddleOCR on the saved image.
    5. Run Groq LLM ingredient analysis on the OCR text.
    6. Create an ``AnalysisResult`` record with the extracted text and analysis.
    7. Return a success response containing the OCR text, nutrients, and analysis.
    """

    # ------------------------------------------------------------------
    # 1. Validate file type
    # ------------------------------------------------------------------
    try:
        storage_service.validate_file_extension(file.filename or "")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # ------------------------------------------------------------------
    # 2. Save image to disk
    # ------------------------------------------------------------------
    try:
        image_path = await storage_service.save_upload(file)
    except (ValueError, IOError) as exc:
        logger.exception("Failed to save uploaded file")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {exc}",
        )

    # ------------------------------------------------------------------
    # 3. Persist upload record
    # ------------------------------------------------------------------
    try:
        upload_record = Upload(image_path=image_path)
        db.add(upload_record)
        db.commit()
        db.refresh(upload_record)
    except Exception as exc:
        db.rollback()
        logger.exception("Database error while saving upload record")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {exc}",
        )

    # ------------------------------------------------------------------
    # 4. Run OCR
    # ------------------------------------------------------------------
    ocr_text: str = ""
    nutrients: list[dict] = []
    try:
        ocr_result = ocr_service.extract_text(image_path)
        ocr_text = ocr_result["ocr_text"]
        nutrients = ocr_result["nutrients"]
    except FileNotFoundError as exc:
        logger.exception("Image file not found for OCR")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR failure – image not found: {exc}",
        )
    except (RuntimeError, EnvironmentError) as exc:
        logger.exception("OCR service error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR failure: {exc}",
        )

    # ------------------------------------------------------------------
    # 5. Run Groq LLM ingredient analysis
    # ------------------------------------------------------------------
    analysis_data: dict | None = None
    analysis_obj: IngredientAnalysis | None = None
    try:
        analysis_data = analysis_service.analyze_ingredients(ocr_text)
        if analysis_data is not None:
            analysis_obj = IngredientAnalysis(**analysis_data)
    except Exception as exc:
        logger.exception("Ingredient analysis failed (non-fatal): %s", exc)
        # Analysis failure is non-fatal — we still return OCR results

    # ------------------------------------------------------------------
    # 6. Persist analysis result
    # ------------------------------------------------------------------
    try:
        analysis_record = AnalysisResult(
            upload_id=upload_record.id,
            ocr_text=ocr_text,
            health_score=(
                float(analysis_data["overall_health_score"])
                if analysis_data and "overall_health_score" in analysis_data
                else None
            ),
            analysis_json={
                "nutrients": nutrients,
                "analysis": analysis_data,
            },
        )
        db.add(analysis_record)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Database error while saving analysis result")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {exc}",
        )

    # ------------------------------------------------------------------
    # 7. Return response
    # ------------------------------------------------------------------
    return UploadResponse(
        success=True,
        upload_id=upload_record.id,
        image_path=image_path,
        ocr_text=ocr_text,
        nutrients=nutrients,
        analysis=analysis_obj,
    )
