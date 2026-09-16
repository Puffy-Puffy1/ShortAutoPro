import fcntl
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audio_finalizer
import main as canonical
import resume_short_runtime as resume
import retention_engine
import storage_manager
import vg4x_bridge
import visual_qa

ROOT = Path(__file__).resolve().parents[1]


class GlobalProductionLockTests(unittest.TestCase):
    def test_different_short_ids_cannot_run_concurrently(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_dir = Path(tmp) / ".locks"
            lock_path = lock_dir / "production.lock"
            with patch.object(canonical, "LOCK_DIR", lock_dir), patch.object(
                canonical, "PRODUCTION_LOCK_PATH", lock_path
            ):
                with canonical.RunLock("short_a"):
                    with self.assertRaises(RuntimeError):
                        with canonical.RunLock("short_b"):
                            pass
            self.assertTrue(lock_path.exists())

    def test_termux_bridge_uses_same_persistent_lock(self):
        text = (ROOT / "automation" / "termux_bridge.sh").read_text(encoding="utf-8")
        self.assertIn('PRODUCTION_LOCK="$PROJECT_DIR/.locks/production.lock"', text)
        self.assertIn("BRIDGE_SKIP=production_active", text)
        self.assertIn("flock -n 8", text)
        self.assertIn("python tools/repo_audit.py", text)


class ResumeStateSelectionTests(unittest.TestCase):
    def test_pipeline_state_filename_never_becomes_short_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            path = state_dir / "pipeline_real_short_123.json"
            path.write_text(
                json.dumps({"short_id": "real_short_123", "status": "FAILED"}),
                encoding="utf-8",
            )
            with patch.object(resume.evo, "STATE_DIR", state_dir):
                self.assertEqual(resume.latest_incomplete(), "real_short_123")

    def test_evolution_state_is_preferred_over_pipeline_shadow_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            evolution = state_dir / "wanted_short.json"
            evolution.write_text(
                json.dumps({"short_id": "wanted_short", "production_status": "FAILED"}),
                encoding="utf-8",
            )
            shadow = state_dir / "pipeline_other_short.json"
            shadow.write_text(
                json.dumps({"short_id": "other_short", "status": "FAILED"}),
                encoding="utf-8",
            )
            os.utime(shadow, (evolution.stat().st_atime + 10, evolution.stat().st_mtime + 10))
            with patch.object(resume.evo, "STATE_DIR", state_dir):
                self.assertEqual(resume.latest_incomplete(), "wanted_short")


class StorageSafetyTests(unittest.TestCase):
    def test_external_cleanup_is_blocked_while_production_lock_is_held(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            lock = base / ".locks" / "production.lock"
            lock.parent.mkdir(parents=True)
            handle = lock.open("a+")
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                with patch.object(storage_manager, "PRODUCTION_LOCK", lock), patch.object(
                    storage_manager, "SID", "different_short"
                ), patch.dict(os.environ, {}, clear=False):
                    os.environ.pop("SAP_PRODUCTION_LOCK_HELD", None)
                    with self.assertRaises(RuntimeError):
                        with storage_manager.CleanupGuard():
                            pass
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                handle.close()

    def test_malformed_storage_numeric_config_uses_safe_defaults(self):
        with patch.dict(
            os.environ,
            {"SHORT_STORAGE_KEEP_PROJECTS": "oops", "SAP_MIN_FREE_GB": "nan"},
            clear=False,
        ):
            self.assertEqual(storage_manager.env_int("SHORT_STORAGE_KEEP_PROJECTS", 3, 1, 20), 3)
            self.assertEqual(storage_manager.env_float("SAP_MIN_FREE_GB", 1.2, 0.25, 50.0), 1.2)


class CanonicalMediaFailClosedTests(unittest.TestCase):
    def test_canonical_adapter_import_failure_is_fatal(self):
        with patch.dict(sys.modules, {"media_runtime_adapter_v2": None}):
            with self.assertRaises(SystemExit) as ctx:
                vg4x_bridge._install_canonical({})
        self.assertEqual(ctx.exception.code, 70)


class ReleaseGateFailClosedTests(unittest.TestCase):
    def run_gate(self, base: Path, sid: str):
        env = os.environ.copy()
        env["SHORTAUTOPRO_BASE"] = str(base)
        env["SHORT_ID"] = sid
        return subprocess.run(
            [sys.executable, str(ROOT / "release_gate.py"), "--enforce"],
            env=env,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_missing_critical_reports_block_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "manifests").mkdir(parents=True)
            sid = "missing_reports"
            (base / "manifests" / f"{sid}_quality.json").write_text(
                json.dumps({"approved": True}), encoding="utf-8"
            )
            proc = self.run_gate(base, sid)
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            report = json.loads((base / "manifests" / f"{sid}_release.json").read_text(encoding="utf-8"))
            self.assertEqual(report["decision"], "BLOCK")
            self.assertTrue(report["missing_reports"])
            self.assertTrue(any(item.startswith("required_report_missing:") for item in report["critical"]))

    def test_complete_strong_reports_can_still_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sid = "complete_reports"
            r = base / "roteiros"
            m = base / "manifests"
            e = base / "reports" / "evolution"
            r.mkdir(parents=True)
            m.mkdir(parents=True)
            e.mkdir(parents=True)

            payloads = {
                r / f"retention_{sid}.json": {"retention_score": 94, "components": {"hook": 94, "language": 96, "payoff": 95}},
                r / f"visual_continuity_{sid}.json": {"visual_continuity_score": 92},
                r / f"visual_score_{sid}.json": {"visual_score": 93, "weak_scenes": []},
                e / f"visual_qa_{sid}.json": {"status": "PASS", "visual_qa_score": 96},
                e / f"final_audio_{sid}.json": {"status": "PASS", "after": {"lufs": -14.0, "true_peak_db": -1.7}, "target": {"lufs": -14.0, "true_peak_db": -1.5}},
                m / f"{sid}_professional.json": {"components": {"media": 94, "captions": 93, "technical": 98}},
                m / f"{sid}_quality.json": {"approved": True},
                r / f"media_quality_{sid}.json": {"status": "PASS", "critical": [], "score": 94},
                r / f"pro_caption_{sid}.json": {"score": 94},
                r / f"caption_layout_{sid}.json": {"status": "PASS", "score": 95},
                r / f"visual_director_{sid}.json": {"visual_director_score": 93},
            }
            for path, data in payloads.items():
                path.write_text(json.dumps(data), encoding="utf-8")

            proc = self.run_gate(base, sid)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            report = json.loads((m / f"{sid}_release.json").read_text(encoding="utf-8"))
            self.assertIn(report["decision"], {"PUBLISH", "ACCEPTABLE"})
            self.assertEqual(report["missing_reports"], [])
            self.assertEqual(report["critical"], [])


class ConfigHardeningTests(unittest.TestCase):
    def test_audio_numeric_config_is_bounded_and_nonfinite_safe(self):
        with patch.dict(os.environ, {"SAP_TEST_FLOAT": "nan"}, clear=False):
            self.assertEqual(audio_finalizer.env_float("SAP_TEST_FLOAT", -14.0, -30.0, -5.0), -14.0)
        with patch.dict(os.environ, {"SAP_TEST_FLOAT": "999"}, clear=False):
            self.assertEqual(audio_finalizer.env_float("SAP_TEST_FLOAT", -14.0, -30.0, -5.0), -5.0)

    def test_retention_threshold_is_bounded_and_nonfinite_safe(self):
        with patch.dict(os.environ, {"SAP_TEST_RETENTION": "nan"}, clear=False):
            self.assertEqual(retention_engine.env_float("SAP_TEST_RETENTION", 78.0, 60.0, 95.0), 78.0)
        with patch.dict(os.environ, {"SAP_TEST_RETENTION": "999"}, clear=False):
            self.assertEqual(retention_engine.env_float("SAP_TEST_RETENTION", 78.0, 60.0, 95.0), 95.0)

    def test_visual_scene_count_config_is_bounded_and_invalid_safe(self):
        with patch.dict(os.environ, {"SAP_TEST_SCENES": "oops"}, clear=False):
            self.assertEqual(visual_qa.safe_int("SAP_TEST_SCENES", 12, 6, 20), 12)
        with patch.dict(os.environ, {"SAP_TEST_SCENES": "99"}, clear=False):
            self.assertEqual(visual_qa.safe_int("SAP_TEST_SCENES", 12, 6, 20), 20)


if __name__ == "__main__":
    unittest.main()
