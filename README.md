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
