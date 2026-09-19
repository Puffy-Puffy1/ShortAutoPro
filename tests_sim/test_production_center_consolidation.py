import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import production_center
import production_doctor
import production_profiler


class ProductionCenterConsolidationTests(unittest.TestCase):
    def test_doctor_routes_media_incomplete_to_semantic_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "roteiros").mkdir(parents=True)
            (base / "reports" / "media").mkdir(parents=True)
            (base / "reports" / "performance").mkdir(parents=True)
            (base / "imagens" / "short_abc").mkdir(parents=True)
            (base / "manifests").mkdir(parents=True)
            (base / "videos").mkdir(parents=True)
            (base / ".sap_state").mkdir(parents=True)

            for name in (
                "scene_map_abc.json",
                "post_script_truth_abc.json",
                "visual_continuity_abc.json",
            ):
                (base / "roteiros" / name).write_text("{}", encoding="utf-8")

            missing = {"missing_scenes": [5, 6]}
            (base / "reports" / "media" / "acquisition_missing_abc.json").write_text(
                json.dumps(missing), encoding="utf-8"
            )

            with mock.patch.object(production_doctor, "BASE", base), \
                 mock.patch.object(production_doctor, "REPORT_DIR", base / "reports" / "production"), \
                 mock.patch.object(production_profiler, "REPORT_DIR", base / "reports" / "performance"):
                report = production_doctor.diagnose("abc")

            self.assertEqual(report["boundary"], "media")
            self.assertEqual(report["missing_scenes"], [5, 6])
            self.assertIn("resume_after_semantic_fix.py", report["next_action"])

    def test_latest_short_id_uses_newest_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            state = base / ".sap_state"
            state.mkdir(parents=True)
            a = state / "pipeline_old.json"
            b = state / "pipeline_new.json"
            a.write_text("{}", encoding="utf-8")
            b.write_text("{}", encoding="utf-8")
            os.utime(a, (1000, 1000))
            os.utime(b, (2000, 2000))
            with mock.patch.object(production_doctor, "BASE", base):
                self.assertEqual(production_doctor.latest_short_id(), "new")

    def test_main_exposes_production_router(self):
        text = Path("main.py").read_text(encoding="utf-8")
        self.assertIn('sub.add_parser("production")', text)
        self.assertIn('"production_center.py"', text)
        self.assertIn("argparse.REMAINDER", text)

    def test_center_has_consolidated_operational_commands(self):
        text = Path("production_center.py").read_text(encoding="utf-8")
        for command in ("latest", "status", "doctor", "profile", "resume", "batch", "watch"):
            self.assertIn(f'sub.add_parser("{command}")', text)
        self.assertIn("resume_after_semantic_fix.py", text)
        self.assertIn("resume_short_runtime.py", text)

    def test_doctor_reads_existing_artifacts_without_alternate_pipeline(self):
        text = Path("production_doctor.py").read_text(encoding="utf-8")
        self.assertIn("PRODUCTION DOCTOR", text)
        self.assertIn("acquisition_missing_", text)
        self.assertIn("production_profiler", text)
        self.assertNotIn("legacy", text.lower())

    def test_termux_menu_exposes_production_center(self):
        text = Path("control_center.sh").read_text(encoding="utf-8")
        self.assertIn("Production Center - Status", text)
        self.assertIn("Production Doctor", text)
        self.assertIn("Production Profiler", text)
        self.assertIn("Production Watch", text)

    def test_diagnostics_include_doctor(self):
        text = Path("diagnostico.sh").read_text(encoding="utf-8")
        self.assertIn('secao "PRODUCTION DOCTOR"', text)
        self.assertIn("production_doctor.py", text)


if __name__ == "__main__":
    unittest.main()
