"""
JWT authentication dependency for FastAPI.

Verifies Supabase Auth JWTs using the project's JWKS public key (ES256).
The ``get_current_user`` dependency extracts the ``sub`` (user UUID)
from a valid ``Authorization: Bearer <token>`` header.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import logging

import httpx
from fastapi import Header, HTTPException
from jose import JWTError, jwk, jwt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
ALGORITHM = "ES256"

# Module-level cache for the JWKS public key
_jwks_key = None


def _fetch_jwks_key():
    """Fetch the JWKS from Supabase and cache the first signing key."""
    global _jwks_key
    if _jwks_key is not None:
        return _jwks_key

    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is not configured.")

    jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    try:
        resp = httpx.get(jwks_url, timeout=10)
        resp.raise_for_status()
        jwks_data = resp.json()
    except Exception as exc:
        logger.error("Failed to fetch JWKS from %s: %s", jwks_url, exc)
        raise RuntimeError(f"Failed to fetch JWKS: {exc}")

    keys = jwks_data.get("keys", [])
    if not keys:
        raise RuntimeError("No keys found in JWKS response.")

    # Use the first key (Supabase typically provides one signing key)
    key_data = keys[0]
    _jwks_key = key_data
    logger.info("Cached JWKS public key (kid=%s, alg=%s)", key_data.get("kid"), key_data.get("alg"))
    return _jwks_key


# Eagerly fetch the key at import time so failures are caught early
try:
    _fetch_jwks_key()
except Exception as exc:
    logger.warning("Could not fetch JWKS at startup (will retry on first request): %s", exc)


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------
async def get_current_user(authorization: str = Header(None)) -> str:
    """Extract and verify the user UUID from a Supabase JWT.

    Parameters
    ----------
    authorization:
        The ``Authorization`` header value (e.g. ``Bearer eyJ...``).

    Returns
    -------
    str
        The Supabase Auth user UUID (``sub`` claim).

    Raises
    ------
    HTTPException (401)
        If the token is missing, expired, or otherwise invalid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token.",
        )

    token = authorization.split(" ")[1]

    try:
        key_data = _fetch_jwks_key()
    except RuntimeError as exc:
        logger.error("JWKS unavailable: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Server authentication is misconfigured.",
        )

    try:
        payload = jwt.decode(
            token,
            key_data,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        logger.warning("JWT verification failed: %s", exc)
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token.",
        )

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Token payload missing user identifier.",
        )

    return user_id
