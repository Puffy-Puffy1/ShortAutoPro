import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RuntimeHarmonyRound3Tests(unittest.TestCase):
    def test_media_ffprobe_calls_use_process_guard(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("from subprocess_guard import run_group", text)
        self.assertNotIn("probe = subprocess.run(", text)
        self.assertGreaterEqual(text.count("probe = run_group("), 3)

    def test_v6_runtime_and_identity_writes_are_atomic(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        self.assertIn("def atomic_json(", text)
        self.assertIn("os.replace(tmp, path)", text)
        self.assertIn("atomic_json(RUNTIME, runtime)", text)
        self.assertIn("atomic_json(RENDER_IDENTITY, identity)", text)
        self.assertNotIn("RUNTIME.write_text(", text)
        self.assertNotIn("RENDER_IDENTITY.write_text(", text)

    def test_profiler_reads_jsonl_as_stream(self):
        text = (ROOT / "production_profiler.py").read_text(encoding="utf-8")
        self.assertIn('with path.open("r", encoding="utf-8", errors="ignore") as handle:', text)
        self.assertIn("for line in handle:", text)
        self.assertNotIn('path.read_text(encoding="utf-8", errors="ignore").splitlines()', text)


if __name__ == "__main__":
    unittest.main()
