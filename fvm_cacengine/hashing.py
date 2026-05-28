"""Hashing utilities."""

from __future__ import annotations

import hashlib

try:
    import blake3 as _blake3
except ImportError:  # pragma: no cover - fallback for environments without blake3
    _blake3 = None

_ALGORITHM = "blake3" if _blake3 is not None else "blake2b-256"


def hash_algorithm() -> str:
    """Return the active hash algorithm name."""
    return _ALGORITHM


def hash_bytes(data: bytes) -> str:
    """Hash bytes using the configured algorithm."""
    if _blake3 is not None:
        return _blake3.blake3(data).hexdigest()
    return hashlib.blake2b(data, digest_size=32).hexdigest()
