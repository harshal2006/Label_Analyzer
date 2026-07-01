"""
Upload router – ``POST /upload``

Accepts a multipart image upload, stores it in Supabase Storage,
runs OCR via PaddleOCR, analyzes ingredients via Groq LLM, and
stores the results in the database.  Requires authentication.
"""

import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.analysis import AnalysisResult
from app.models.upload import Upload
from app.schemas.upload import ErrorResponse, IngredientAnalysis, UploadResponse
from app.services import analysis_service, ocr_service, storage_service
from app.services.health_score import calculate_health_score

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Upload"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a nutrition-label image",
    description=(
        "Upload a JPG, JPEG, PNG, or WebP image of a nutrition label. "
        "The server stores the image in Supabase Storage, runs OCR, "
        "analyzes ingredients via Groq LLM, and returns the extracted "
        "text with analysis.  Requires a valid Supabase Auth JWT."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file type"},
        401: {"model": ErrorResponse, "description": "Missing or invalid token"},
        500: {"model": ErrorResponse, "description": "OCR or database failure"},
    },
)
async def upload_image(
    file: UploadFile = File(..., description="Nutrition-label image file"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> UploadResponse:
    """Handle an image upload and return OCR + analysis results.

    Workflow
    --------
    1. Validate the file extension.
    2. Create an ``Upload`` record in the database (to obtain an ID).
    3. Upload the image to Supabase Storage.
    4. Update the ``Upload`` record with the Supabase storage path.
    5. Download the image to a temp file and run PaddleOCR.
    6. Run Groq LLM ingredient analysis on the OCR text.
    7. Create an ``AnalysisResult`` record with the extracted text and analysis.
    8. Return a success response containing the OCR text, nutrients, and analysis.
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
    # 2. Create upload record (to get the ID for the storage path)
    # ------------------------------------------------------------------
    try:
        upload_record = Upload(
            image_path="pending",  # placeholder — updated after Supabase upload
            user_id=user_id,
        )
        db.add(upload_record)
        db.commit()
        db.refresh(upload_record)
    except Exception as exc:
        db.rollback()
        logger.exception("Database error while creating upload record")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {exc}",
        )

    # ------------------------------------------------------------------
    # 3. Upload image to Supabase Storage
    # ------------------------------------------------------------------
    try:
        file_bytes = await file.read()
        storage_path = await storage_service.upload_to_supabase(
            file_bytes=file_bytes,
            filename=file.filename or "upload.jpg",
            user_id=user_id,
            upload_id=upload_record.id,
        )
    except (ValueError, IOError) as exc:
        # Clean up the DB record if storage fails
        db.delete(upload_record)
        db.commit()
        logger.exception("Failed to upload to Supabase Storage")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {exc}",
        )

    # ------------------------------------------------------------------
    # 4. Update the upload record with the storage path
    # ------------------------------------------------------------------
    try:
        upload_record.image_path = storage_path
        db.commit()
        db.refresh(upload_record)
    except Exception as exc:
        db.rollback()
        logger.exception("Database error while updating image path")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {exc}",
        )

    # ------------------------------------------------------------------
    # 5. Download image to temp file and run OCR
    # ------------------------------------------------------------------
    ocr_text: str = ""
    nutrients: list[dict] = []
    temp_path: str | None = None
    try:
        temp_path = storage_service.download_image(storage_path)
        ocr_result = ocr_service.extract_text(temp_path)
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
    finally:
        # Always clean up the temp file
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # 6. Run Groq LLM ingredient analysis
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
    # 6b. Override LLM health score with deterministic rule-based score
    # ------------------------------------------------------------------
    if analysis_data is not None:
        # Build a {name: "value unit"} dict from the parsed nutrient list
        nutrient_dict = {
            n["name"]: f'{n["value"]} {n.get("unit", "")}'.strip()
            for n in nutrients
            if "name" in n and "value" in n
        }
        ingredient_names = [
            ing.get("name", "")
            for ing in analysis_data.get("ingredients", [])
            if ing.get("name")
        ]
        det_score, det_reasoning = calculate_health_score(
            nutrient_dict, ingredient_names
        )
        analysis_data["overall_health_score"] = int(round(det_score))
        analysis_data["health_score_reasoning"] = det_reasoning
        # Re-validate the Pydantic model with the overridden score
        try:
            analysis_obj = IngredientAnalysis(**analysis_data)
        except Exception as exc:
            logger.warning("Failed to re-validate analysis after score override: %s", exc)

    # ------------------------------------------------------------------
    # 7. Persist analysis result
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
    # 8. Return response
    # ------------------------------------------------------------------
    return UploadResponse(
        success=True,
        upload_id=upload_record.id,
        image_path=storage_path,
        ocr_text=ocr_text,
        nutrients=nutrients,
        analysis=analysis_obj,
    )
