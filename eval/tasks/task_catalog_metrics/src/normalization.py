"""Catalog normalization helpers."""

import re


def normalize_sku(raw: str) -> str:
    """Normalize SKUs to ABC-123 style uppercase tokens."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", raw.strip()).strip("-")
    return cleaned.lower()


def normalize_email(raw: str) -> str:
    """Normalize an email address by trimming spaces and lowercasing."""
    local, at, domain = raw.partition("@")
    if not at or not local.strip() or not domain.strip():
        raise ValueError("invalid email")
    return f"{local.strip()}@{domain.strip().lower()}"
