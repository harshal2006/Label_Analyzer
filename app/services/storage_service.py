"""
Storage service – Supabase Storage integration.

Handles uploading images to Supabase Storage, downloading them for
local OCR processing, and deleting them when an upload is removed.
All operations use the **service-role key** for full bucket access.
"""

import logging
import os
import tempfile
import uuid
from pathlib import Path

import httpx
from supabase import Client, create_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
BUCKET_NAME = "label-images"

# File extensions we accept (lowercase, with leading dot).
ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp"}

# Fallback local uploads dir — kept so main.py doesn't crash if it
# still references UPLOAD_DIR at import time during migration.
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"


def _get_supabase_client() -> Client:
    """Return a Supabase client initialised with the service-role key."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise EnvironmentError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env"
        )
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return client


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_file_extension(filename: str) -> str:
    """Return the lowercase file extension if it is allowed; raise ValueError otherwise."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return ext


# ---------------------------------------------------------------------------
# Upload to Supabase Storage
# ---------------------------------------------------------------------------
async def upload_to_supabase(
    file_bytes: bytes,
    filename: str,
    user_id: str,
    upload_id: int,
) -> str:
    """Upload an image to Supabase Storage and return its public/signed URL.

    The file is stored at ``{user_id}/{upload_id}_{filename}`` inside the
    ``label-images`` bucket.

    Parameters
    ----------
    file_bytes:
        Raw image bytes.
    filename:
        Original filename from the upload (used for extension & naming).
    user_id:
        Supabase Auth user UUID.
    upload_id:
        Primary key of the Upload record in the database.

    Returns
    -------
    str
        The Supabase Storage path (relative to the bucket) for the uploaded file.
    """
    ext = validate_file_extension(filename)
    safe_name = f"{upload_id}_{uuid.uuid4().hex[:8]}{ext}"
    storage_path = f"{user_id}/{safe_name}"

    client = _get_supabase_client()

    # Determine MIME type
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    content_type = mime_map.get(ext, "application/octet-stream")

    try:
        client.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": content_type},
        )
    except Exception as exc:
        logger.exception("Failed to upload to Supabase Storage: %s", exc)
        raise IOError(f"Supabase Storage upload failed: {exc}")

    logger.info("Uploaded to Supabase Storage: %s/%s", BUCKET_NAME, storage_path)
    return storage_path


def get_public_url(storage_path: str) -> str:
    """Get the public URL for a file in Supabase Storage.

    Works for public buckets. For private buckets, use ``get_signed_url``.
    """
    client = _get_supabase_client()
    resp = client.storage.from_(BUCKET_NAME).get_public_url(storage_path)
    return resp


def get_signed_url(storage_path: str, expires_in: int = 3600) -> str:
    """Generate a time-limited signed URL for a private bucket file.

    Parameters
    ----------
    storage_path:
        Path inside the bucket (e.g. ``user_uuid/1_abc123.jpg``).
    expires_in:
        Seconds until the URL expires (default: 1 hour).

    Returns
    -------
    str
        A signed URL that can be used to download the file.
    """
    client = _get_supabase_client()
    resp = client.storage.from_(BUCKET_NAME).create_signed_url(
        storage_path, expires_in
    )
    return resp.get("signedURL", "")


# ---------------------------------------------------------------------------
# Download from Supabase Storage (for OCR processing)
# ---------------------------------------------------------------------------
def download_image(storage_path: str) -> str:
    """Download an image from Supabase Storage to a local temp file.

    Parameters
    ----------
    storage_path:
        The storage path inside the bucket (e.g. ``user_uuid/1_abc.jpg``).

    Returns
    -------
    str
        Absolute path to the downloaded temp file.  The caller is responsible
        for deleting this file after use.
    """
    client = _get_supabase_client()

    try:
        file_bytes = client.storage.from_(BUCKET_NAME).download(storage_path)
    except Exception as exc:
        logger.exception("Failed to download from Supabase Storage: %s", exc)
        raise IOError(f"Supabase Storage download failed: {exc}")

    # Determine extension from the storage path
    ext = Path(storage_path).suffix or ".jpg"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        tmp.write(file_bytes)
        tmp.flush()
    finally:
        tmp.close()

    logger.info("Downloaded image to temp file: %s", tmp.name)
    return tmp.name


# ---------------------------------------------------------------------------
# Delete from Supabase Storage
# ---------------------------------------------------------------------------
def delete_from_supabase(storage_path: str) -> None:
    """Delete a file from Supabase Storage.

    Parameters
    ----------
    storage_path:
        The storage path inside the bucket to delete.
    """
    client = _get_supabase_client()

    try:
        client.storage.from_(BUCKET_NAME).remove([storage_path])
    except Exception as exc:
        logger.exception("Failed to delete from Supabase Storage: %s", exc)
        raise IOError(f"Supabase Storage deletion failed: {exc}")

    logger.info("Deleted from Supabase Storage: %s/%s", BUCKET_NAME, storage_path)
