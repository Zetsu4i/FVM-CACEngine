"""Content-addressed compressed chunk store."""

from __future__ import annotations

from pathlib import Path

from .hashing import hash_bytes

try:
    import zstandard as _zstd
except ImportError:  # pragma: no cover - fallback when zstandard is unavailable
    _zstd = None
    import zlib as _zlib


class ChunkStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.chunks_dir = self.root / "chunks"
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        if _zstd is not None:
            self._compressor = _zstd.ZstdCompressor()
            self._decompressor = _zstd.ZstdDecompressor()
        else:
            self._compressor = None
            self._decompressor = None

    def _path_for_hash(self, chunk_hash: str) -> Path:
        return self.chunks_dir / chunk_hash[:2] / f"{chunk_hash}.bin"

    def put_chunk(self, data: bytes) -> str:
        chunk_hash = hash_bytes(data)
        chunk_path = self._path_for_hash(chunk_hash)
        if chunk_path.exists():
            return chunk_hash

        chunk_path.parent.mkdir(parents=True, exist_ok=True)
        if self._compressor is not None:
            payload = self._compressor.compress(data)
        else:
            payload = _zlib.compress(data)
        temp_path = chunk_path.with_suffix(".tmp")
        temp_path.write_bytes(payload)
        temp_path.replace(chunk_path)
        return chunk_hash

    def has_chunk(self, chunk_hash: str) -> bool:
        return self._path_for_hash(chunk_hash).exists()

    def get_chunk(self, chunk_hash: str) -> bytes:
        chunk_path = self._path_for_hash(chunk_hash)
        if not chunk_path.exists():
            raise FileNotFoundError(f"Chunk {chunk_hash} not found")
        payload = chunk_path.read_bytes()
        if self._decompressor is not None:
            return self._decompressor.decompress(payload)
        return _zlib.decompress(payload)
