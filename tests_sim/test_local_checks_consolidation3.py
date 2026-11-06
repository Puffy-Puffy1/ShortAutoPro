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
            "PREFLIGHT CHECK 3.0.4",
            "main.py",
            "profile_run.sh",
            "media_engine_v2.py",
            "media_provider_v2.py",
            "media_provider_router_v2.py",
            "media_validator_v2.py",
            "media_must_verifier.py",
            "media_visual_verifier.py",
            "media_external_resilience.py",
            "media_quality_report.py",
            "render_plan_v2.py",
            "render_engine_v2.py",
            "retention_engine.py",
            "sound_design_engine.py",
            "audio_finalizer.py",
            "visual_qa.py",
            "release_gate.py",
            "storage_manager.py",
            "PRONTO PARA PRODUÇÃO 3.0",
        ):
            self.assertIn(token, text)
        for legacy in (
            "gerar_short.sh",
            "gerar_short_professional.sh",
            "professional_pipeline_runtime.py",
            "resume_short_professional_runtime.py",
            "v6_professional_runtime.py",
            "v6_runtime.py",
            "v6.py",
            "video.py",
            "limpar_storage.sh",
        ):
            self.assertIn(legacy, text)
        self.assertNotIn('"v6_runtime",\n', text)

    def test_health_targets_canonical_pipeline(self):
        text = self.read("health_check.sh")
        for token in (
            "HEALTH CHECK 3.0.4",
            "main.py",
            "media_engine_v2.py",
            "media_provider_v2.py",
            "media_provider_router_v2.py",
            "media_validator_v2.py",
            "media_must_verifier.py",
            "media_visual_verifier.py",
            "media_external_resilience.py",
            "media_quality_report.py",
            "render_plan_v2.py",
            "render_engine_v2.py",
            "visual_continuity_engine.py",
            "visual_score_engine.py",
            "retention_engine.py",
            "sound_design_engine.py",
            "SAUDÁVEL 3.0",
        ):
            self.assertIn(token, text)
        self.assertNotIn('"v6_runtime",\n', text)

    def test_operational_checks_do_not_require_legacy_media_runtime(self):
        legacy = (
            "media_stage_runtime.py",
            "midia.py",
            "media_runtime_adapter_v1.py",
            "media_runtime_adapter_v2.py",
            "vg4x_bridge.py",
            "visual_engine_unified.py",
            "visual_query_expansion_v4.py",
            "visual_selection_engine_v4.py",
        )
        for name in ("preflight_check.sh", "health_check.sh", "production_ready.sh"):
            text = self.read(name)
            for module in legacy:
                self.assertNotIn(module, text, f"{name} still requires {module}")
            for module in (
                "media_engine_v2.py",
                "media_provider_v2.py",
                "media_provider_router_v2.py",
                "media_validator_v2.py",
                "media_visual_verifier.py",
                "render_plan_v2.py",
                "render_engine_v2.py",
            ):
                self.assertIn(module, text, f"{name}: missing {module}")

    def test_production_ready_uses_canonical_v2_media_and_renderer(self):
        text = self.read("production_ready.sh")
        self.assertIn("READINESS GATE 3.0.4", text)
        for module in (
            "media_engine_v2.py",
            "media_provider_v2.py",
            "media_provider_router_v2.py",
            "media_validator_v2.py",
            "media_must_verifier.py",
            "media_visual_verifier.py",
            "media_external_resilience.py",
            "render_plan_v2.py",
            "render_engine_v2.py",
        ):
            self.assertIn(module, text)
        for legacy in (
            "media_stage_runtime.py",
            "midia.py",
            "media_master_gate.py",
            "video_professional.py",
            "v6_professional.py",
        ):
            self.assertNotIn(legacy, text)

    def test_repository_audit_checks_canonical_v2_provider_chain(self):
        text = self.read("tools/repo_audit.py")
        for module in (
            "media_engine_v2.py",
            "media_provider_v2.py",
            "media_provider_router_v2.py",
            "media_validator_v2.py",
            "media_visual_verifier.py",
            "media_external_resilience.py",
        ):
            self.assertIn(module, text)
        self.assertNotIn("MEDIA_ADAPTER_V1_REQUIRED_TOKENS", text)
        self.assertNotIn("MEDIA_ADAPTER_V2_REQUIRED_TOKENS", text)

    def test_diagnostics_reads_main_not_removed_entrypoint(self):
        text = self.read("diagnostico.sh")
        self.assertIn('"$BASE/main.py"', text)
        self.assertNotIn('"$BASE/gerar_short.sh"', text)
        self.assertIn("ÚLTIMOS RELEASE GATES", text)
        self.assertIn("tools/repo_audit.py", text)

    def test_release_check_matches_ci_contract(self):
        text = self.read("release_check.sh")
        self.assertIn("RELEASE CHECK 3.0", text)
        self.assertIn("Preflight 3.0.4", text)
        self.assertIn("Repository Audit 3.0.4", text)
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
