# FVM-CACEngine

Chunk-addressed Flutter SDK version manager prototype with four core systems:

- Manifest Generator
- Chunk Store
- Binary Diff/Patch Engine
- Version Switcher

## Design

- Uses content-addressed chunks and dynamic chunk boundaries (FastCDC-style).
- Hashes chunks with BLAKE3 (falls back to BLAKE2b when `blake3` is unavailable).
- Stores chunks in a shared compressed store (Zstandard when available).
- Upgrades by downloading only missing chunks, then atomically switching the active SDK.

## Run tests

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## CLI

```bash
python -m fvm_cacengine scan --sdk-root <sdk_dir> --store-root <chunk_store> --output <manifest.json>
python -m fvm_cacengine manifest --version <version> --sdk-root <sdk_dir> --store-root <chunk_store> --output <manifest.json>
python -m fvm_cacengine upgrade --local-manifest <old.json> --target-manifest <new.json> --server-store <server_store> --local-store <client_store> --active-sdk-dir <active_sdk_dir>
python -m fvm_cacengine switch --target-manifest <new.json> --local-store <client_store> --active-sdk-dir <active_sdk_dir>
```
