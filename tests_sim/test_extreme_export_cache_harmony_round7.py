import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExtremeExportCacheHarmonyRound7Tests(unittest.TestCase):
    def test_download_export_is_atomic_and_size_verified(self):
        text = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("shutil.copyfileobj(src, dst, length=1024 * 1024)", text)
        self.assertIn("os.fsync(dst.fileno())", text)
        self.assertIn("if copied_size != source_size:", text)
        self.assertIn("os.replace(tmp, candidate)", text)

    def test_subtitle_audit_mirror_is_atomic(self):
        text = (ROOT / "legenda_dinamica.py").read_text(encoding="utf-8")
        self.assertIn("audit_tmp =", text)
        self.assertIn("espelho ASS incompleto", text)
        self.assertIn("os.replace(audit_tmp, ASS_AUDIT)", text)
        self.assertNotIn("shutil.copyfile(ASS_FINAL, ASS_AUDIT)", text)

    def test_manifest_records_exact_video_identity(self):
        text = (ROOT / "production_manifest.py").read_text(encoding="utf-8")
        self.assertIn('"size_bytes": video_size', text)
        self.assertIn('"mtime_ns": video_mtime_ns', text)

    def test_quality_caches_require_video_identity_match(self):
        text = (ROOT / "professional_quality_gate.py").read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count('int(stat.st_mtime_ns)'), 2)
        self.assertGreaterEqual(text.count('int(stat.st_size)'), 2)
        self.assertIn('report.get("video_identity"', text)

    def test_audio_report_binds_measurement_to_video_identity(self):
        text = (ROOT / "audio_finalizer.py").read_text(encoding="utf-8")
        self.assertIn("def file_identity(", text)
        self.assertIn('"video_identity":file_identity(VIDEO)', text)
        self.assertIn('"version":"1.3"', text)


if __name__ == "__main__":
    unittest.main()
