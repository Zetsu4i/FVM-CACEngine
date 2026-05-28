import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from fvm_cacengine.chunk_store import ChunkStore
from fvm_cacengine.cli import main
from fvm_cacengine.manifest import ManifestGenerator
from fvm_cacengine.server_client import MetadataServer


class CliTests(unittest.TestCase):
    def test_scan_and_manifest_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sdk = root / "sdk"
            (sdk / "bin").mkdir(parents=True)
            (sdk / "bin" / "flutter").write_text("flutter")

            scan_output = root / "scan.json"
            rc = main(
                [
                    "scan",
                    "--sdk-root",
                    str(sdk),
                    "--store-root",
                    str(root / "store"),
                    "--version",
                    "local",
                    "--output",
                    str(scan_output),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(scan_output.read_text())["version"], "local")

            manifest_output = root / "manifest.json"
            rc = main(
                [
                    "manifest",
                    "--version",
                    "3.39.0",
                    "--sdk-root",
                    str(sdk),
                    "--store-root",
                    str(root / "store"),
                    "--output",
                    str(manifest_output),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(manifest_output.read_text())["version"], "3.39.0")

    def test_upgrade_and_switch_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            v1 = root / "v1"
            v2 = root / "v2"
            (v1 / "bin").mkdir(parents=True)
            (v2 / "bin").mkdir(parents=True)
            (v1 / "bin" / "flutter").write_bytes(b"AAAABBBB")
            (v2 / "bin" / "flutter").write_bytes(b"AAAADDDD")

            server = MetadataServer(root / "server-store")
            m1 = server.ingest_version("3.38.9", v1)
            m2 = server.ingest_version("3.39.0", v2)
            m1_path = root / "m1.json"
            m2_path = root / "m2.json"
            m1_path.write_text(json.dumps(m1))
            m2_path.write_text(json.dumps(m2))

            local_store = ChunkStore(root / "local-store")
            for meta in m1["files"].values():
                for chunk_hash in meta["chunks"]:
                    local_store.put_chunk(server.get_chunk(chunk_hash))

            active_dir = root / "active"
            removed_map = root / "removed.json"
            current_manifest = root / "current.json"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = main(
                    [
                        "upgrade",
                        "--local-manifest",
                        str(m1_path),
                        "--target-manifest",
                        str(m2_path),
                        "--server-store",
                        str(root / "server-store"),
                        "--local-store",
                        str(root / "local-store"),
                        "--active-sdk-dir",
                        str(active_dir),
                        "--removed-map",
                        str(removed_map),
                        "--write-manifest",
                        str(current_manifest),
                    ]
                )
            self.assertEqual(rc, 0)
            result = json.loads(stdout.getvalue())
            self.assertGreaterEqual(result["downloaded_chunks"], 1)
            self.assertEqual((active_dir / "bin" / "flutter").read_bytes(), b"AAAADDDD")
            self.assertEqual(json.loads(current_manifest.read_text())["version"], "3.39.0")

            # Switch command reconstructs same target from local chunks.
            active_dir_2 = root / "active-2"
            rc = main(
                [
                    "switch",
                    "--target-manifest",
                    str(m2_path),
                    "--local-store",
                    str(root / "local-store"),
                    "--active-sdk-dir",
                    str(active_dir_2),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertEqual((active_dir_2 / "bin" / "flutter").read_bytes(), b"AAAADDDD")


if __name__ == "__main__":
    unittest.main()
