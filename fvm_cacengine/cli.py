"""Command-line interface for chunk-based SDK operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .chunk_store import ChunkStore
from .manifest import ManifestGenerator
from .server_client import LocalClient
from .version_switcher import VersionSwitcher


def _load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def _save_json(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def cmd_scan(args: argparse.Namespace) -> int:
    generator = ManifestGenerator()
    chunk_store = ChunkStore(Path(args.store_root))
    manifest = generator.generate(args.version, Path(args.sdk_root), chunk_store)
    if args.output:
        _save_json(Path(args.output), manifest)
    else:
        print(json.dumps(manifest, indent=2))
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    generator = ManifestGenerator()
    chunk_store = ChunkStore(Path(args.store_root))
    manifest = generator.generate(args.version, Path(args.sdk_root), chunk_store)
    _save_json(Path(args.output), manifest)
    return 0


def cmd_upgrade(args: argparse.Namespace) -> int:
    local_manifest = _load_json(Path(args.local_manifest))
    target_manifest = _load_json(Path(args.target_manifest))
    server_chunks = ChunkStore(Path(args.server_store))
    client = LocalClient(Path(args.local_store))

    result = client.upgrade(
        active_sdk_dir=Path(args.active_sdk_dir),
        local_manifest=local_manifest,
        target_manifest=target_manifest,
        fetch_chunk=server_chunks.get_chunk,
        removed_files_map_path=Path(args.removed_map) if args.removed_map else None,
    )

    if args.write_manifest:
        _save_json(Path(args.write_manifest), target_manifest)
    print(json.dumps(result, indent=2))
    return 0


def cmd_switch(args: argparse.Namespace) -> int:
    target_manifest = _load_json(Path(args.target_manifest))
    previous_manifest = _load_json(Path(args.previous_manifest)) if args.previous_manifest else None
    switcher = VersionSwitcher(ChunkStore(Path(args.local_store)))
    switcher.switch(
        active_sdk_dir=Path(args.active_sdk_dir),
        target_manifest=target_manifest,
        previous_manifest=previous_manifest,
        removed_files_map_path=Path(args.removed_map) if args.removed_map else None,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fvm-cacengine")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan SDK and emit manifest")
    scan.add_argument("--sdk-root", required=True)
    scan.add_argument("--store-root", required=True)
    scan.add_argument("--version", default="local")
    scan.add_argument("--output")
    scan.set_defaults(func=cmd_scan)

    manifest = sub.add_parser("manifest", help="Generate versioned manifest")
    manifest.add_argument("--version", required=True)
    manifest.add_argument("--sdk-root", required=True)
    manifest.add_argument("--store-root", required=True)
    manifest.add_argument("--output", required=True)
    manifest.set_defaults(func=cmd_manifest)

    upgrade = sub.add_parser("upgrade", help="Upgrade active SDK using missing chunks only")
    upgrade.add_argument("--local-manifest", required=True)
    upgrade.add_argument("--target-manifest", required=True)
    upgrade.add_argument("--server-store", required=True)
    upgrade.add_argument("--local-store", required=True)
    upgrade.add_argument("--active-sdk-dir", required=True)
    upgrade.add_argument("--removed-map")
    upgrade.add_argument("--write-manifest")
    upgrade.set_defaults(func=cmd_upgrade)

    switch_cmd = sub.add_parser("switch", help="Switch active SDK to target manifest")
    switch_cmd.add_argument("--target-manifest", required=True)
    switch_cmd.add_argument("--local-store", required=True)
    switch_cmd.add_argument("--active-sdk-dir", required=True)
    switch_cmd.add_argument("--previous-manifest")
    switch_cmd.add_argument("--removed-map")
    switch_cmd.set_defaults(func=cmd_switch)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
