"""
Input validation and sanitization utilities.
"""

import re
from datetime import datetime

from fastapi import HTTPException, status


def validate_phone(phone: str) -> str:
    """
    Validate an Indian mobile phone number.

    Rules:
    - Exactly 10 digits after stripping optional ``+91`` or ``0`` prefix.
    - Must start with 6, 7, 8, or 9.

    Parameters
    ----------
    phone : str
        Raw phone input.

    Returns
    -------
    str
        Cleaned 10-digit phone number.

    Raises
    ------
    HTTPException 422
        If the phone number is invalid.
    """
    # Strip whitespace and common prefixes
    cleaned = phone.strip().replace(" ", "").replace("-", "")
    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("0"):
        cleaned = cleaned[1:]

    if not re.fullmatch(r"[6-9]\d{9}", cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid Indian phone number. Must be 10 digits starting with 6-9.",
        )
    return cleaned


def validate_pin(pin: str) -> str:
    """
    Validate a numeric PIN (4–6 digits).

    Parameters
    ----------
    pin : str
        Raw PIN input.

    Returns
    -------
    str
        Validated PIN string.

    Raises
    ------
    HTTPException 422
        If the PIN is invalid.
    """
    cleaned = pin.strip()
    if not re.fullmatch(r"\d{4,6}", cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PIN must be 4 to 6 digits.",
        )
    return cleaned


def sanitize_string(s: str, max_length: int = 500) -> str:
    """
    Strip leading/trailing whitespace and truncate to *max_length* characters.

    Parameters
    ----------
    s : str
        Raw input string.
    max_length : int
        Maximum allowed length (default 500).

    Returns
    -------
    str
        Sanitized string.
    """
    return s.strip()[:max_length]


def validate_date_range(start: datetime, end: datetime) -> None:
    """
    Ensure *start* is not after *end*.

    Parameters
    ----------
    start : datetime
        Range start (inclusive).
    end : datetime
        Range end (inclusive).

    Raises
    ------
    HTTPException 422
        If start > end.
    """
    if start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Start date must be on or before end date.",
        )
