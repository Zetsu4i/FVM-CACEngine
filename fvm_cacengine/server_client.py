"""Reference server/client orchestration for chunk-based SDK upgrades."""

from __future__ import annotations

from pathlib import Path

from .chunk_store import ChunkStore
from .diff_patch import BinaryDiffPatchEngine
from .manifest import ManifestGenerator
from .version_switcher import VersionSwitcher


class MetadataServer:
    def __init__(self, storage_root: Path):
        self.storage_root = Path(storage_root)
        self.chunk_store = ChunkStore(self.storage_root)
        self.manifest_generator = ManifestGenerator()
        self.manifests: dict[str, dict] = {}

    def ingest_version(self, version: str, sdk_root: Path) -> dict:
        manifest = self.manifest_generator.generate(version, sdk_root, self.chunk_store)
        self.manifests[version] = manifest
        return manifest

    def get_manifest(self, version: str) -> dict:
        return self.manifests[version]

    def get_chunk(self, chunk_hash: str) -> bytes:
        return self.chunk_store.get_chunk(chunk_hash)


class LocalClient:
    def __init__(self, local_store: Path):
        self.chunk_store = ChunkStore(local_store)
        self.switcher = VersionSwitcher(self.chunk_store)
        self.engine = BinaryDiffPatchEngine()

    def upgrade(
        self,
        active_sdk_dir: Path,
        local_manifest: dict,
        target_manifest: dict,
        fetch_chunk,
        removed_files_map_path: Path | None = None,
    ) -> dict:
        missing = self.engine.missing_chunks(local_manifest, target_manifest)
        for chunk_hash in missing:
            self.chunk_store.put_chunk(fetch_chunk(chunk_hash))

        self.switcher.switch(
            active_sdk_dir=active_sdk_dir,
            target_manifest=target_manifest,
            previous_manifest=local_manifest,
            removed_files_map_path=removed_files_map_path,
        )
        return {"downloaded_chunks": len(missing)}
