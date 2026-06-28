"""
Admin router – ``GET /admin/uploads`` and ``DELETE /admin/uploads/{upload_id}``

Per-user upload management endpoints.  All endpoints require authentication
and only return / operate on uploads owned by the current user.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.analysis import AnalysisResult
from app.models.upload import Upload
from app.services import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------
class UploadListItem(BaseModel):
    """Summary of a single upload in the user's list."""

    id: int
    filename: str
    created_at: str
    status: str  # "analysed" or "pending"
    image_url: str


# ---------------------------------------------------------------------------
# GET /admin/uploads
# ---------------------------------------------------------------------------
@router.get(
    "/uploads",
    response_model=list[UploadListItem],
    summary="List your uploads",
    description=(
        "Return all uploads belonging to the authenticated user, "
        "ordered by creation date (newest first)."
    ),
    responses={
        401: {"description": "Missing or invalid token"},
    },
)
async def list_uploads(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> list[UploadListItem]:
    """Return all uploads owned by the current user."""

    uploads = (
        db.query(Upload)
        .filter(Upload.user_id == user_id)
        .order_by(Upload.uploaded_at.desc())
        .all()
    )

    items: list[UploadListItem] = []
    for u in uploads:
        # Derive filename from the storage path (e.g. "user_id/1_abc123.jpg" → "1_abc123.jpg")
        filename = Path(u.image_path).name if u.image_path else "unknown"

        # Check if analysis exists
        has_analysis = u.analysis is not None
        upload_status = "analysed" if has_analysis else "pending"

        # Build a signed URL (valid for 1 hour)
        try:
            image_url = storage_service.get_signed_url(u.image_path, expires_in=3600)
        except Exception:
            image_url = u.image_path  # fallback to raw path

        items.append(
            UploadListItem(
                id=u.id,
                filename=filename,
                created_at=u.uploaded_at.isoformat() if u.uploaded_at else "",
                status=upload_status,
                image_url=image_url,
            )
        )

    return items


# ---------------------------------------------------------------------------
# DELETE /admin/uploads/{upload_id}
# ---------------------------------------------------------------------------
@router.delete(
    "/uploads/{upload_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an upload",
    description=(
        "Delete an upload and its associated analysis from the database, "
        "and remove the image from Supabase Storage.  Only the owner of "
        "the upload may delete it."
    ),
    responses={
        401: {"description": "Missing or invalid token"},
        403: {"description": "Not the owner of this upload"},
        404: {"description": "Upload not found"},
    },
)
async def delete_upload(
    upload_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> Response:
    """Delete an upload, its analysis, and the image from Supabase Storage."""

    # Fetch the upload
    upload_record = db.query(Upload).filter(Upload.id == upload_id).first()
    if upload_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload with id {upload_id} not found.",
        )

    # Verify ownership
    if upload_record.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this upload.",
        )

    # Delete from Supabase Storage
    storage_path = upload_record.image_path
    if storage_path and storage_path != "pending":
        try:
            storage_service.delete_from_supabase(storage_path)
        except Exception as exc:
            logger.warning(
                "Failed to delete from Supabase Storage (continuing): %s", exc
            )

    # Delete analysis record (if exists)
    analysis_record = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.upload_id == upload_id)
        .first()
    )
    if analysis_record:
        db.delete(analysis_record)

    # Delete upload record
    db.delete(upload_record)
    db.commit()

    logger.info("Deleted upload %d (user=%s)", upload_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
