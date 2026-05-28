"""SDK manifest generation."""

from __future__ import annotations

from pathlib import Path

from .chunk_store import ChunkStore
from .chunking import ChunkingConfig, chunk_bytes


class ManifestGenerator:
    def __init__(self, chunking: ChunkingConfig = ChunkingConfig()):
        self.chunking = chunking

    def generate(self, version: str, sdk_root: Path, chunk_store: ChunkStore) -> dict:
        sdk_root = Path(sdk_root)
        files: dict[str, dict] = {}

        for path in sorted(sdk_root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(sdk_root).as_posix()
            data = path.read_bytes()
            chunk_hashes = [chunk_store.put_chunk(chunk) for chunk in chunk_bytes(data, self.chunking)]
            files[rel] = {
                "size": len(data),
                "chunks": chunk_hashes,
            }

        return {
            "version": version,
            "hash_algorithm": "blake3",
            "chunking": {
                "strategy": "dynamic",
                "min_size": self.chunking.min_size,
                "avg_size": self.chunking.avg_size,
                "max_size": self.chunking.max_size,
            },
            "files": files,
        }
