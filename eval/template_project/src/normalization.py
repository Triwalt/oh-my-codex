"""Data normalization helpers."""

import re


def normalize_name(name: str) -> str:
    """Normalize a person's name."""
    collapsed = " ".join(name.split())
    return collapsed.lower()


def normalize_phone(raw: str) -> str:
    """Normalize phone numbers to +1-XXX-XXX-XXXX format."""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        pass
    elif len(digits) != 10:
        raise ValueError("invalid phone number")

    return f"+1-{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
