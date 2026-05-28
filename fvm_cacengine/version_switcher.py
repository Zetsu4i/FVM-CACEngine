"""Atomic version switching using a shared chunk store."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .chunk_store import ChunkStore
from .diff_patch import BinaryDiffPatchEngine


class VersionSwitcher:
    def __init__(self, chunk_store: ChunkStore):
        self.chunk_store = chunk_store
        self._engine = BinaryDiffPatchEngine()

    def switch(
        self,
        active_sdk_dir: Path,
        target_manifest: dict,
        previous_manifest: dict | None = None,
        removed_files_map_path: Path | None = None,
    ) -> None:
        active_sdk_dir = Path(active_sdk_dir)
        temp_dir = active_sdk_dir.parent / f".{active_sdk_dir.name}.tmp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        for rel, file_meta in target_manifest.get("files", {}).items():
            self._engine.reconstruct_file(file_meta, self.chunk_store, temp_dir / rel)

        backup_dir = active_sdk_dir.parent / f".{active_sdk_dir.name}.bak"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)

        if active_sdk_dir.exists():
            active_sdk_dir.replace(backup_dir)
        temp_dir.replace(active_sdk_dir)
        if backup_dir.exists():
            shutil.rmtree(backup_dir)

        if removed_files_map_path is not None and previous_manifest is not None:
            removed_files = sorted(
                set(previous_manifest.get("files", {})) - set(target_manifest.get("files", {}))
            )
            removed_files_map_path = Path(removed_files_map_path)
            removed_files_map_path.parent.mkdir(parents=True, exist_ok=True)
            removed_files_map_path.write_text(
                json.dumps(
                    {
                        "from_version": previous_manifest.get("version"),
                        "to_version": target_manifest.get("version"),
                        "removed_files": removed_files,
                    },
                    indent=2,
                )
            )
