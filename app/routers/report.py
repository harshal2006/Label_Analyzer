"""
Report router – ``GET /report/{upload_id}/download``

Generates a downloadable PDF nutrition analysis report for a given upload.
Fetches the upload record and its parsed nutrients from the database,
enriches them with Groq-powered insights, computes %DV flags, detects
allergens, calculates macro split, and streams the PDF back.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.analysis import AnalysisResult
from app.models.upload import Upload
from app.services import groq_service, pdf_service
from app.services.nutrition_analysis import (
    calculate_dv_flags,
    calculate_macro_split,
    detect_allergens,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/report", tags=["Reports"])


@router.get(
    "/{upload_id}/download",
    summary="Download a PDF nutrition report",
    description=(
        "Generate and download a PDF report for a previously analysed upload. "
        "The report includes a nutrient summary table with %DV flags, allergen "
        "warnings, a macronutrient pie chart, and a detailed breakdown with "
        "source and usage information powered by Groq LLM."
    ),
    responses={
        200: {"content": {"application/pdf": {}}, "description": "PDF report file"},
        404: {"description": "Upload or analysis not found"},
        500: {"description": "Report generation failed"},
    },
)
async def download_report(
    upload_id: int,
    db: Session = Depends(get_db),
):
    """Generate and stream a PDF nutrition report for the given upload."""

    # ------------------------------------------------------------------
    # 1. Fetch the upload record
    # ------------------------------------------------------------------
    try:
        upload_record = db.query(Upload).filter(Upload.id == upload_id).first()
    except Exception as exc:
        logger.exception("Database error fetching upload %d", upload_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {exc}",
        )

    if upload_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload with id {upload_id} not found.",
        )

    # ------------------------------------------------------------------
    # 2. Fetch the analysis result
    # ------------------------------------------------------------------
    try:
        analysis_record = (
            db.query(AnalysisResult)
            .filter(AnalysisResult.upload_id == upload_id)
            .first()
        )
    except Exception as exc:
        logger.exception("Database error fetching analysis for upload %d", upload_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {exc}",
        )

    if analysis_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis found for upload {upload_id}. Please analyse the image first.",
        )

    # ------------------------------------------------------------------
    # 3. Extract nutrients from the stored analysis JSON
    # ------------------------------------------------------------------
    nutrients_list: list[dict] = []
    try:
        analysis_json = analysis_record.analysis_json or {}
        nutrients_list = analysis_json.get("nutrients", [])
    except Exception as exc:
        logger.exception("Failed to extract nutrients from analysis JSON")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read analysis data: {exc}",
        )

    # Build a simple {name: "value unit"} dict for Groq and PDF
    nutrients_dict: dict[str, str] = {}
    for item in nutrients_list:
        name = item.get("name", "Unknown")
        value = item.get("value", "")
        unit = item.get("unit", "")
        nutrients_dict[name] = f"{value} {unit}".strip()

    # ------------------------------------------------------------------
    # 4. Compute %DV flags and macro split (pure, no API calls)
    # ------------------------------------------------------------------
    dv_flags = calculate_dv_flags(nutrients_dict)
    macro_split = calculate_macro_split(nutrients_dict)

    # ------------------------------------------------------------------
    # 5. Detect allergens from OCR text
    # ------------------------------------------------------------------
    ocr_text = analysis_record.ocr_text or ""
    allergens = detect_allergens(ocr_text)

    # ------------------------------------------------------------------
    # 6. Get Groq nutrient insights (defensive — never crashes)
    # ------------------------------------------------------------------
    try:
        insights = groq_service.get_nutrient_insights(nutrients_dict)
    except Exception as exc:
        logger.exception("Groq insights failed (non-fatal): %s", exc)
        # Build fallback so PDF can still be generated
        insights = {
            name: {
                "source": "Information not available.",
                "usage": "Information not available.",
            }
            for name in nutrients_dict
        }

    # ------------------------------------------------------------------
    # 7. Generate the PDF
    # ------------------------------------------------------------------
    product_info = {
        "upload_id": upload_record.id,
        "image_path": upload_record.image_path,
        "uploaded_at": upload_record.uploaded_at,
    }

    try:
        pdf_buffer = pdf_service.generate_report_pdf(
            product_info,
            nutrients_dict,
            insights,
            dv_flags=dv_flags,
            allergens=allergens,
            macro_split=macro_split,
        )
    except Exception as exc:
        logger.exception("PDF generation failed for upload %d", upload_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {exc}",
        )

    # ------------------------------------------------------------------
    # 8. Stream the PDF back
    # ------------------------------------------------------------------
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="report_{upload_id}.pdf"',
        },
    )
