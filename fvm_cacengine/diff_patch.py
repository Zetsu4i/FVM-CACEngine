"""Diff and reconstruction helpers based on chunk manifests."""

from __future__ import annotations

from pathlib import Path

from .chunk_store import ChunkStore


class BinaryDiffPatchEngine:
    @staticmethod
    def missing_chunks(local_manifest: dict, target_manifest: dict) -> list[str]:
        local_chunks = set()
        for meta in local_manifest.get("files", {}).values():
            local_chunks.update(meta.get("chunks", []))

        required = set()
        for meta in target_manifest.get("files", {}).values():
            required.update(meta.get("chunks", []))

        return sorted(required - local_chunks)

    @staticmethod
    def reconstruct_file(file_meta: dict, chunk_store: ChunkStore, output_path: Path) -> None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = b"".join(chunk_store.get_chunk(chunk_hash) for chunk_hash in file_meta["chunks"])
        output_path.write_bytes(payload)
