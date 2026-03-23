"""
Input validation and sanitization for guest registration.

Copied from fgt-checkin-system/backend/validation.py — only the parts
needed for meetup guest → member registration.
"""

import logging

logger = logging.getLogger(__name__)

MAX_LENGTHS = {
    "tag": 30,
    "email": 254,
    "phone": 20,
    "telephone": 20,
    "personnummer": 12,
    "name": 100,
}


def sanitize_string(value: str, field_name: str = "") -> str:
    """Strip whitespace and enforce max length."""
    if not isinstance(value, str):
        return value
    result = value.strip()
    max_len = MAX_LENGTHS.get(field_name.lower())
    if max_len and len(result) > max_len:
        logger.warning(f"Field '{field_name}' truncated from {len(result)} to {max_len} chars")
        result = result[:max_len]
    return result


def sanitize_phone(value: str) -> str:
    """Normalize phone to digits only. '070-123 45 67' → '0701234567'."""
    if not isinstance(value, str):
        return value
    return "".join(c for c in value if c.isdigit())


def sanitize_personnummer(value: str) -> str:
    """Normalize Swedish personal ID. '19900101-1234' → '199001011234'."""
    if not isinstance(value, str):
        return value
    cleaned = value.replace("-", "").replace(" ", "")
    return "".join(c for c in cleaned if c.isdigit())


def validate_personnummer(value: str) -> tuple[bool, str]:
    """
    Validate Swedish personnummer using Luhn algorithm.
    Accepts 10 or 12 digit string.
    Returns (is_valid, error_message).
    """
    if not value:
        return (False, "Personnummer krävs")

    digits = sanitize_personnummer(value)
    if len(digits) not in (10, 12):
        return (False, f"Personnummer måste vara 10 eller 12 siffror (fick {len(digits)})")

    # Use last 10 digits for Luhn (strip century if 12 digits)
    d = digits[-10:]

    # Basic date sanity check (YYMMDD)
    month = int(d[2:4])
    day = int(d[4:6])
    if month < 1 or month > 12:
        return (False, "Ogiltig månad i personnummer")
    if day < 1 or day > 31:
        return (False, "Ogiltig dag i personnummer")

    # Luhn checksum on all 10 digits
    weights = [2, 1, 2, 1, 2, 1, 2, 1, 2, 1]
    total = 0
    for i in range(10):
        val = int(d[i]) * weights[i]
        if val >= 10:
            val -= 9
        total += val

    if total % 10 != 0:
        return (False, "Ogiltigt personnummer (checksumma)")

    return (True, "")
