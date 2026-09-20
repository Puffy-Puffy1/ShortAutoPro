import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RuntimeHarmonyTests(unittest.TestCase):
    def test_heavy_runtime_modules_share_process_guard(self):
        modules = (
            "script_runtime.py",
            "audio.py",
            "legenda_dinamica.py",
            "video_professional.py",
            "v6_professional.py",
            "audio_finalizer.py",
            "visual_qa.py",
            "professional_quality_gate.py",
        )
        for name in modules:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("from subprocess_guard import run_group", text, name)
            self.assertIn("run_group(", text, name)
            self.assertNotIn("subprocess.run(", text, name)

    def test_main_auxiliary_commands_are_bounded(self):
        text = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("def run_control(command: list[str]) -> int:", text)
        self.assertIn("SAP_CONTROL_COMMAND_TIMEOUT", text)
        self.assertIn("comando auxiliar excedeu", text)
        self.assertNotIn("return subprocess.call(", text)

    def test_doctor_surfaces_slowest_pipeline_stage(self):
        text = (ROOT / "production_doctor.py").read_text(encoding="utf-8")
        self.assertIn('"PIPELINE_STAGE_SLOW"', text)
        self.assertIn('row.get("category") == "pipeline_stage"', text)
        self.assertIn("slow_total >= 120", text)


if __name__ == "__main__":
    unittest.main()
