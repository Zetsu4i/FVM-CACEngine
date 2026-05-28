import json
import tempfile
import unittest
from pathlib import Path

from fvm_cacengine.chunk_store import ChunkStore
from fvm_cacengine.chunking import ChunkingConfig
from fvm_cacengine.diff_patch import BinaryDiffPatchEngine
from fvm_cacengine.hashing import hash_algorithm
from fvm_cacengine.manifest import ManifestGenerator
from fvm_cacengine.server_client import LocalClient, MetadataServer


class CoreSystemsTests(unittest.TestCase):
    def test_manifest_generator_and_chunk_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sdk_root = tmp_path / "sdk"
            sdk_root.mkdir()
            (sdk_root / "bin").mkdir()
            (sdk_root / "bin" / "flutter").write_bytes(b"a" * 100 + b"b" * 100 + b"c" * 100)

            store = ChunkStore(tmp_path / "store")
            generator = ManifestGenerator(ChunkingConfig(min_size=32, avg_size=64, max_size=96))
            manifest = generator.generate("3.39.0", sdk_root, store)

            self.assertEqual(manifest["version"], "3.39.0")
            self.assertEqual(manifest["hash_algorithm"], hash_algorithm())
            chunks = manifest["files"]["bin/flutter"]["chunks"]
            self.assertGreater(len(chunks), 1)
            for chunk_hash in chunks:
                self.assertTrue(store.has_chunk(chunk_hash))

    def test_missing_chunks_and_reconstruct(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = ChunkStore(tmp_path / "store")
            old_chunks = [store.put_chunk(b"AAAA"), store.put_chunk(b"BBBB"), store.put_chunk(b"CCCC")]
            new_chunk = store.put_chunk(b"DDDD")

            local_manifest = {"version": "3.38.9", "files": {"file.bin": {"chunks": old_chunks}}}
            target_manifest = {
                "version": "3.39.0",
                "files": {"file.bin": {"chunks": [old_chunks[0], new_chunk, old_chunks[2]]}},
            }
            missing = BinaryDiffPatchEngine.missing_chunks(local_manifest, target_manifest)
            self.assertEqual(missing, [new_chunk])

            output = tmp_path / "out.bin"
            BinaryDiffPatchEngine.reconstruct_file(target_manifest["files"]["file.bin"], store, output)
            self.assertEqual(output.read_bytes(), b"AAAADDDDCCCC")

    def test_client_upgrade_downloads_missing_and_switches(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            server_root = tmp_path / "server"
            v1 = tmp_path / "v1"
            v2 = tmp_path / "v2"
            active = tmp_path / "active-sdk"
            removed_map = tmp_path / "removed" / "map.json"
            (v1 / "bin").mkdir(parents=True)
            (v2 / "bin").mkdir(parents=True)
            (v1 / "lib").mkdir(parents=True)
            (v2 / "lib").mkdir(parents=True)

            (v1 / "bin" / "flutter").write_bytes(b"AAAA" + b"BBBB" + b"CCCC")
            (v2 / "bin" / "flutter").write_bytes(b"AAAA" + b"DDDD" + b"CCCC")
            (v1 / "lib" / "obsolete.txt").write_text("remove me")
            (v2 / "lib" / "new.txt").write_text("new file")

            server = MetadataServer(server_root)
            server.manifest_generator = ManifestGenerator(
                ChunkingConfig(min_size=4, avg_size=4, max_size=4)
            )
            m1 = server.ingest_version("3.38.9", v1)
            m2 = server.ingest_version("3.39.0", v2)

            client = LocalClient(tmp_path / "client-store")
            for meta in m1["files"].values():
                for chunk_hash in meta["chunks"]:
                    client.chunk_store.put_chunk(server.get_chunk(chunk_hash))

            result = client.upgrade(
                active_sdk_dir=active,
                local_manifest=m1,
                target_manifest=m2,
                fetch_chunk=server.get_chunk,
                removed_files_map_path=removed_map,
            )

            v1_chunks = {chunk for meta in m1["files"].values() for chunk in meta["chunks"]}
            v2_chunks = {chunk for meta in m2["files"].values() for chunk in meta["chunks"]}
            expected_missing = len(v2_chunks - v1_chunks)

            self.assertEqual(result["downloaded_chunks"], expected_missing)
            self.assertLess(result["downloaded_chunks"], len(v2_chunks))
            self.assertEqual((active / "bin" / "flutter").read_bytes(), b"AAAADDDDCCCC")
            self.assertEqual((active / "lib" / "new.txt").read_text(), "new file")
            removed = json.loads(removed_map.read_text())
            self.assertIn("lib/obsolete.txt", removed["removed_files"])


if __name__ == "__main__":
    unittest.main()
