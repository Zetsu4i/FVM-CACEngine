"""Content-defined chunking for deduplicated storage."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkingConfig:
    min_size: int = 2048
    avg_size: int = 8192
    max_size: int = 16384


def chunk_bytes(data: bytes, config: ChunkingConfig = ChunkingConfig()) -> list[bytes]:
    """Split bytes using lightweight FastCDC-style boundaries."""
    if not data:
        return []

    mask = config.avg_size - 1
    chunks: list[bytes] = []
    start = 0
    n = len(data)

    while start < n:
        i = min(start + config.min_size, n)
        end_limit = min(start + config.max_size, n)
        fingerprint = 0

        while i < end_limit:
            fingerprint = ((fingerprint << 1) + data[i]) & 0xFFFFFFFF
            if (fingerprint & mask) == 0:
                i += 1
                break
            i += 1

        if i >= n:
            i = n
        elif i > end_limit:
            i = end_limit

        chunks.append(data[start:i])
        start = i

    return chunks
