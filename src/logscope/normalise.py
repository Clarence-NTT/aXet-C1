"""Message normalisation helpers."""

from __future__ import annotations

import re

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_HEX_RE = re.compile(r"\b0[xX][0-9a-fA-F]+\b")
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")


def normalise_message(message: str) -> str:
    """Return the normalised form of an error message."""
    message = _UUID_RE.sub("<uuid>", message)
    message = _HEX_RE.sub("<hex>", message)
    return _NUMBER_RE.sub("<n>", message)
