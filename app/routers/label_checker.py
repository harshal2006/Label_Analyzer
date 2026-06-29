"""
Label Checker router – ``POST /check-label``

Accepts an image upload, runs OCR, and checks for label compliance
against mandatory requirements using Groq LLM.
"""

import logging
import os
import tempfile
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.auth import get_current_user
from app.services import analysis_service, ocr_service, storage_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Compliance"])

@router.post(
    "/check-label",
    status_code=status.HTTP_200_OK,
    summary="Check nutrition label compliance",
    description="Upload an image to get a fast compliance pass/fail check.",
)
async def check_label(
    file: UploadFile = File(..., description="Nutrition-label image file"),
    user_id: str = Depends(get_current_user),
):
    try:
        storage_service.validate_file_extension(file.filename or "")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    temp_path = None
    try:
        # Save file to a temporary location
        fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(file.filename or "")[1])
        with os.fdopen(fd, 'wb') as f:
            content = await file.read()
            f.write(content)

        # Run OCR
        try:
            ocr_result = ocr_service.extract_text(temp_path)
            ocr_text = ocr_result["ocr_text"]
        except Exception as exc:
            logger.exception("OCR failure")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not extract text from image. Please upload a clearer image."
            )

        if not ocr_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract text from image. Please upload a clearer image."
            )

        # Run Compliance Check
        try:
            compliance_data = analysis_service.check_label_compliance(ocr_text)
            if compliance_data is None:
                raise ValueError("Groq returned None")
        except Exception as exc:
            logger.exception("Groq compliance check failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Analysis failed. Please try again."
            )

        return compliance_data

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
