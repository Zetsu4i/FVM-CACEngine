import tempfile
import unittest
from pathlib import Path

from fvm_cacengine.chunking import ChunkingConfig, chunk_bytes, chunk_file


class ChunkingTests(unittest.TestCase):
    def test_fastcdc_respects_bounds(self):
        config = ChunkingConfig(min_size=128, avg_size=256, max_size=512)
        data = b"a" * 10_000
        chunks = chunk_bytes(data, config)

        self.assertGreater(len(chunks), 1)
        for chunk in chunks[:-1]:
            self.assertGreaterEqual(len(chunk), config.min_size)
            self.assertLessEqual(len(chunk), config.max_size)
        self.assertLessEqual(len(chunks[-1]), config.max_size)

    def test_chunk_file_matches_chunk_bytes(self):
        config = ChunkingConfig(min_size=64, avg_size=128, max_size=256)
        data = b"abcdef" * 500
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.bin"
            path.write_bytes(data)
            from_bytes = chunk_bytes(data, config)
            from_file = list(chunk_file(path, config, read_size=128))
            self.assertEqual(from_bytes, from_file)


if __name__ == "__main__":
    unittest.main()
