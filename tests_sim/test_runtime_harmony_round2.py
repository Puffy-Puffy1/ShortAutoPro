import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RuntimeHarmonyRound2Tests(unittest.TestCase):
    def test_guarded_check_output_helper_exists(self):
        text = (ROOT / "subprocess_guard.py").read_text(encoding="utf-8")
        self.assertIn("def check_output_group(", text)
        self.assertIn("stdout=subprocess.PIPE", text)
        self.assertIn("check=True", text)

    def test_ffprobe_helpers_use_guarded_output(self):
        for name in ("audio.py", "video_professional.py", "v6_professional.py"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("check_output_group", text, name)
            self.assertNotIn("subprocess.check_output(", text, name)

    def test_manifest_and_main_do_not_use_direct_run_for_guarded_calls(self):
        manifest = (ROOT / "production_manifest.py").read_text(encoding="utf-8")
        self.assertIn("run_group(", manifest)
        self.assertNotIn("subprocess.run(", manifest)
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("proc = run_group(", main)

    def test_visual_qa_caches_ffmpeg_filter_capabilities(self):
        text = (ROOT / "visual_qa.py").read_text(encoding="utf-8")
        self.assertIn("_FILTERS_CACHE", text)
        self.assertIn("def available_filters()", text)
        self.assertNotIn("subprocess.check_output(", text)

    def test_gemini_429_respects_retry_after(self):
        runtime = (ROOT / "gemini_runtime.py").read_text(encoding="utf-8")
        self.assertIn("Retry-After", runtime)
        self.assertIn("min(wait, 12)", runtime)
        for name in ("topic_engine.py", "publish_pack.py", "hook_engine.py"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("gemini_runtime", text, name)


if __name__ == "__main__":
    unittest.main()
