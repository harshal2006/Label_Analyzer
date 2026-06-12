"""
Upload router – ``POST /upload``

Accepts a multipart image upload, persists it to disk, runs OCR via
Google Cloud Vision, and stores the results in PostgreSQL.
"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.analysis import AnalysisResult
from app.models.upload import Upload
from app.schemas.upload import ErrorResponse, UploadResponse
from app.services import ocr_service, storage_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Upload"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a nutrition-label image",
    description=(
        "Upload a JPG, JPEG, PNG, or WebP image of a nutrition label. "
        "The server stores the image, runs OCR, and returns the extracted text."
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
    """Handle an image upload and return OCR results.

    Workflow
    --------
    1. Validate the file extension.
    2. Save the image to ``uploads/`` with a UUID filename.
    3. Create an ``Upload`` record in PostgreSQL.
    4. Run Google Vision OCR on the saved image.
    5. Create an ``AnalysisResult`` record with the extracted text.
    6. Return a success response containing the OCR text.
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
    try:
        ocr_text = ocr_service.extract_text(image_path)
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
    # 5. Persist analysis result
    # ------------------------------------------------------------------
    try:
        analysis_record = AnalysisResult(
            upload_id=upload_record.id,
            ocr_text=ocr_text,
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
    # 6. Return response
    # ------------------------------------------------------------------
    return UploadResponse(
        success=True,
        upload_id=upload_record.id,
        image_path=image_path,
        ocr_text=ocr_text,
    )
