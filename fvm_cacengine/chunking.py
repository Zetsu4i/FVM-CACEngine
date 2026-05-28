"""Content-defined chunking for deduplicated storage."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


def _build_gear_table(seed: int = 0x0123456789ABCDEF) -> tuple[int, ...]:
    """Deterministically build a 256-entry gear table for FastCDC.

    The seed is used to generate a stable pseudo-random table for rolling hash updates.
    """
    value = seed & 0xFFFFFFFFFFFFFFFF
    table = []
    for _ in range(256):
        value ^= (value << 13) & 0xFFFFFFFFFFFFFFFF
        value ^= (value >> 7) & 0xFFFFFFFFFFFFFFFF
        value ^= (value << 17) & 0xFFFFFFFFFFFFFFFF
        table.append(value & 0xFFFFFFFFFFFFFFFF)
    return tuple(table)


_GEAR_TABLE = _build_gear_table()


@dataclass(frozen=True)
class ChunkingConfig:
    min_size: int = 2048
    avg_size: int = 8192
    max_size: int = 16384

    def __post_init__(self) -> None:
        if self.min_size <= 0 or self.avg_size <= 0 or self.max_size <= 0:
            raise ValueError("Chunk sizes must be positive")
        if not (self.min_size <= self.avg_size <= self.max_size):
            raise ValueError("Chunk sizes must satisfy min <= avg <= max")


class FastCDCChunker:
    def __init__(self, config: ChunkingConfig):
        self.config = config
        self._mask_small, self._mask_large = self._compute_masks(config.avg_size)

    @staticmethod
    def _compute_masks(avg_size: int) -> tuple[int, int]:
        if avg_size <= 1:
            bits = 1
        else:
            bits = max(1, int(math.log2(avg_size)))
        mask_small = (1 << (bits + 1)) - 1
        mask_large = (1 << max(1, bits - 1)) - 1
        return mask_small, mask_large

    def _roll_hash(self, value: int, byte: int) -> int:
        return ((value >> 1) + _GEAR_TABLE[byte]) & 0xFFFFFFFFFFFFFFFF

    def find_cut(self, data: bytes | bytearray, eof: bool) -> int | None:
        """Return the next cut index.

        If ``eof`` is False and no cut can be determined yet, returns None to request
        more data. When a cut is found, returns the index after the cut byte (the
        chunk length). When ``eof`` is True, returns the remaining length.
        """
        view = memoryview(data)
        length = len(view)
        if length == 0:
            return 0 if eof else None
        if length <= self.config.min_size:
            return length if eof else None

        end = min(self.config.max_size, length)
        normal_end = min(self.config.avg_size, end)
        value = 0
        i = self.config.min_size

        while i < normal_end:
            value = self._roll_hash(value, view[i])
            if (value & self._mask_small) == 0:
                return i + 1
            i += 1

        while i < end:
            value = self._roll_hash(value, view[i])
            if (value & self._mask_large) == 0:
                return i + 1
            i += 1

        if end < length:
            return end
        return end if eof else None


def _chunk_iter(buffer: bytearray, chunker: FastCDCChunker, eof: bool) -> Iterable[bytes]:
    """Yield chunks from the buffer and remove processed bytes in-place.

    ``eof`` indicates whether more data will be appended to the buffer.
    """
    while True:
        cut = chunker.find_cut(buffer, eof)
        if cut is None:
            break
        if cut == 0:
            break
        yield bytes(buffer[:cut])
        del buffer[:cut]
        if not buffer:
            break


def chunk_bytes(data: bytes, config: ChunkingConfig = ChunkingConfig()) -> list[bytes]:
    """Split bytes using FastCDC content-defined chunking."""
    if not data:
        return []
    chunker = FastCDCChunker(config)
    buffer = bytearray(data)
    return list(_chunk_iter(buffer, chunker, eof=True))


def chunk_file(path: Path, config: ChunkingConfig = ChunkingConfig(), read_size: int = 1024 * 1024) -> Iterable[bytes]:
    """Yield FastCDC chunks from a file without loading it all into memory."""
    chunker = FastCDCChunker(config)
    buffer = bytearray()
    with Path(path).open("rb") as handle:
        while True:
            block = handle.read(read_size)
            if not block:
                break
            buffer.extend(block)
            yield from _chunk_iter(buffer, chunker, eof=False)
        if buffer:
            yield from _chunk_iter(buffer, chunker, eof=True)
