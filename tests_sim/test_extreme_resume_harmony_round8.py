import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExtremeResumeHarmonyRound8Tests(unittest.TestCase):
    def test_resume_render_probe_uses_guarded_output(self):
        text = (ROOT / "resume_short_runtime.py").read_text(encoding="utf-8")
        self.assertIn("check_output_group", text)
        self.assertNotIn("subprocess.check_output(", text)

    def test_resume_download_export_is_atomic_and_size_verified(self):
        text = (ROOT / "resume_short_runtime.py").read_text(encoding="utf-8")
        self.assertIn("shutil.copyfileobj(src, dst, length=1024 * 1024)", text)
        self.assertIn("os.fsync(dst.fileno())", text)
        self.assertIn('raise RuntimeError("exportação resume incompleta")', text)
        self.assertIn("os.replace(tmp, target)", text)
        self.assertNotIn("shutil.copy2(final, target)", text)

    def test_resume_latest_state_scan_tolerates_disappearing_files(self):
        text = (ROOT / "resume_short_runtime.py").read_text(encoding="utf-8")
        self.assertIn("except OSError:", text)
        self.assertIn("states.append((path.stat().st_mtime, path))", text)
        self.assertNotIn('key=lambda path: path.stat().st_mtime', text)


if __name__ == "__main__":
    unittest.main()
