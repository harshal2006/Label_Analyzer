"""
Storage service – handles saving uploaded images to the local filesystem.

All images are stored under the ``uploads/`` directory with UUID-based
filenames to avoid collisions.
"""

import os
import uuid
from pathlib import Path

from fastapi import UploadFile

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# The uploads directory lives at the project root (next to app/).
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"

# File extensions we accept (lowercase, with leading dot).
ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp"}


def _ensure_upload_dir() -> None:
    """Create the uploads directory if it does not exist."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def validate_file_extension(filename: str) -> str:
    """Return the lowercase file extension if it is allowed; raise ValueError otherwise."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return ext


async def save_upload(file: UploadFile) -> str:
    """Persist an uploaded file to disk with a unique name.

    Parameters
    ----------
    file:
        The incoming ``UploadFile`` from the request.

    Returns
    -------
    str
        The relative path (e.g. ``uploads/a1b2c3d4.jpg``) suitable for
        storing in the database and returning in the API response.

    Raises
    ------
    ValueError
        If the file extension is not in ``ALLOWED_EXTENSIONS``.
    IOError
        If writing to disk fails.
    """
    ext = validate_file_extension(file.filename or "unknown.bin")
    _ensure_upload_dir()

    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / unique_name
    relative_path = f"uploads/{unique_name}"

    # Read the file in chunks to keep memory usage bounded.
    contents = await file.read()
    dest.write_bytes(contents)

    return relative_path
