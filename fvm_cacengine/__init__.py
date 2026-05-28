"""Core systems for a chunk-addressed Flutter SDK version manager."""

from .chunk_store import ChunkStore
from .diff_patch import BinaryDiffPatchEngine
from .manifest import ManifestGenerator
from .version_switcher import VersionSwitcher

__all__ = [
    "ChunkStore",
    "BinaryDiffPatchEngine",
    "ManifestGenerator",
    "VersionSwitcher",
]
