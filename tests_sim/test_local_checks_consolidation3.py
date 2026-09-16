import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LocalChecksConsolidation3Tests(unittest.TestCase):
    def read(self, name: str) -> str:
        return (ROOT / name).read_text(encoding="utf-8")

    def test_preflight_targets_canonical_pipeline(self):
        text = self.read("preflight_check.sh")
        for token in (
            "PREFLIGHT CHECK 3.0",
            "main.py",
            "profile_run.sh",
            "media_runtime_adapter_v1.py",
            "vg4x_bridge.py",
            "visual_engine_unified.py",
            "visual_query_expansion_v4.py",
            "video_professional.py",
            "v6_professional.py",
            "retention_engine.py",
            "sound_design_engine.py",
            "audio_finalizer.py",
            "visual_qa.py",
            "release_gate.py",
            "storage_manager.py",
            "PRONTO PARA PRODUÇÃO 3.0",
        ):
            self.assertIn(token, text)
        self.assertIn("LEGADOS=(gerar_short.sh video.py v6.py v6_runtime.py limpar_storage.sh)", text)
        self.assertNotIn('"v6_runtime",\n', text)

    def test_health_targets_canonical_pipeline(self):
        text = self.read("health_check.sh")
        for token in (
            "HEALTH CHECK 3.0",
            "main.py",
            "media_runtime_adapter_v1.py",
            "vg4x_bridge.py",
            "visual_engine_unified.py",
            "visual_query_expansion_v4.py",
            "video_professional.py",
            "v6_professional.py",
            "visual_continuity_engine.py",
            "visual_score_engine.py",
            "retention_engine.py",
            "sound_design_engine.py",
            "SAUDÁVEL 3.0",
        ):
            self.assertIn(token, text)
        self.assertNotIn('"v6_runtime",\n', text)

    def test_diagnostics_reads_main_not_removed_entrypoint(self):
        text = self.read("diagnostico.sh")
        self.assertIn('"$BASE/main.py"', text)
        self.assertNotIn('"$BASE/gerar_short.sh"', text)
        self.assertIn("ÚLTIMOS RELEASE GATES", text)
        self.assertIn("tools/repo_audit.py", text)

    def test_release_check_matches_ci_contract(self):
        text = self.read("release_check.sh")
        self.assertIn("RELEASE CHECK 3.0", text)
        self.assertIn("Preflight 3.0", text)
        self.assertIn("Repository Audit 3.0", text)
        self.assertIn("blackdetect", text)
        self.assertIn("cropdetect", text)
        self.assertNotIn("Preflight V6", text)

    def test_finalize_is_only_a_canonical_resume_wrapper(self):
        text = self.read("finalize_short.sh")
        self.assertIn('exec python "$BASE/main.py" resume --short-id "$SHORT_ID"', text)
        self.assertNotIn("STATUS: QUALITY PASS", text)
        self.assertNotIn('run_py "QUALITY GATE"', text)

    def test_all_local_shell_checks_parse(self):
        for name in (
            "preflight_check.sh",
            "health_check.sh",
            "diagnostico.sh",
            "release_check.sh",
            "finalize_short.sh",
        ):
            proc = subprocess.run(["bash", "-n", str(ROOT / name)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"{name}: {proc.stderr}")


if __name__ == "__main__":
    unittest.main()
