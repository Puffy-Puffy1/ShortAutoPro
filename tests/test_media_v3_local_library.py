import tempfile
import unittest
from pathlib import Path

from media_v3.library import LocalLibraryV3


class MediaV3LocalLibraryTests(unittest.TestCase):
    def test_store_and_search_revalidates_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source.jpg"
            source.write_bytes(b"\xff\xd8\xff" + b"x" * 4096)

            library = LocalLibraryV3(base)
            record = library.store(
                source,
                provider="fixture",
                asset_id="fixture-1",
                query="security sensor",
                description="security sensor motion detector",
                tags=["security", "sensor"],
                provenance={"source_url": "https://example.invalid/fixture"},
                license_name="fixture-license",
            )

            rows = library.search(
                "security sensor",
                must=["security sensor"],
                avoid=["wrong person"],
            )
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["provider"], "local_v3")
            self.assertEqual(rows[0]["sha256"], record["sha256"])

            cached = Path(rows[0]["local_path"])
            cached.write_bytes(b"corrupted")
            self.assertEqual(library.search("security sensor", must=["security sensor"]), [])

    def test_must_gate_is_not_bypassed_by_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source.jpg"
            source.write_bytes(b"\xff\xd8\xff" + b"x" * 4096)

            library = LocalLibraryV3(base)
            library.store(
                source,
                provider="fixture",
                asset_id="fixture-2",
                query="generic city",
                description="generic city skyline",
                tags=["city"],
                provenance={"source_url": "https://example.invalid/fixture"},
                license_name="fixture-license",
            )

            self.assertEqual(
                library.search("security sensor", must=["security sensor"]),
                [],
            )


if __name__ == "__main__":
    unittest.main()
