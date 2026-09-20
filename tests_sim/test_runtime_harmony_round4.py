import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RuntimeHarmonyRound4Tests(unittest.TestCase):
    def test_secondary_asset_download_has_wall_clock_deadline_and_guarded_probe(self):
        text = (ROOT / "multi_asset_director.py").read_text(encoding="utf-8")
        self.assertIn("SAP_MULTI_ASSET_DOWNLOAD_SECONDS", text)
        self.assertIn("time.monotonic()-started>MAX_DOWNLOAD_SECONDS", text)
        self.assertIn("probe=run_group(", text)
        self.assertNotIn("probe=subprocess.run(", text)

    def test_v6_retention_ass_write_is_atomic(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        self.assertIn("def atomic_text(", text)
        self.assertIn("atomic_text(ASS_RETENTION", text)
        self.assertNotIn("ASS_RETENTION.write_text(", text)

    def test_profiler_aggregates_streaming_and_serializes_threaded_appends(self):
        text = (ROOT / "production_profiler.py").read_text(encoding="utf-8")
        self.assertIn("_WRITE_LOCK = threading.Lock()", text)
        self.assertIn("with _WRITE_LOCK:", text)
        self.assertIn("def iter_rows(", text)
        self.assertIn("for row in iter_rows(short_id)", text)
        self.assertNotIn("rows = read(short_id)", text)
        self.assertNotIn("groups: dict[tuple[str, str], list[float]]", text)


if __name__ == "__main__":
    unittest.main()
