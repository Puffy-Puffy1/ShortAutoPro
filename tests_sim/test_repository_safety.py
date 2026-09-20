import pathlib
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class RepositorySafetyTests(unittest.TestCase):
    def tracked_files(self):
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]

    def test_secrets_and_local_config_are_not_tracked(self):
        tracked = self.tracked_files()
        forbidden_exact = {
            ".env",
            "config.env",
            "config.sh",
        }
        forbidden_suffixes = (".key", ".pem", ".token")
        offenders = [
            path for path in tracked
            if path in forbidden_exact
            or path.endswith(forbidden_suffixes)
            or path.startswith("secrets/")
            or path.startswith("credentials/")
        ]
        self.assertEqual(offenders, [], f"Sensitive/local files tracked: {offenders}")

    def test_heavy_models_are_not_tracked(self):
        tracked = self.tracked_files()
        heavy_suffixes = (".onnx", ".gguf", ".pt", ".pth", ".ckpt")
        offenders = [path for path in tracked if path.lower().endswith(heavy_suffixes)]
        self.assertEqual(offenders, [], f"Heavy model files tracked: {offenders}")

    def test_generated_runtime_artifacts_are_not_tracked(self):
        tracked = self.tracked_files()
        offenders = [
            path for path in tracked
            if path.startswith("roteiros/")
            or (path.startswith("manifests/20") and path.endswith(".json"))
            or path.startswith("credits/attribution_20")
            or path.startswith("credits/ledger_20")
            or path.startswith("credits/short_20")
        ]
        self.assertEqual(offenders, [], f"Generated runtime artifacts tracked: {offenders}")

    def test_legacy_architecture_artifacts_are_not_tracked(self):
        tracked = set(self.tracked_files())
        forbidden = {
            "docs/CONSOLIDATION_1_0.md",
            "docs/CONSOLIDATION_1_0_ACTIVE_GRAPH.json",
            "docs/CONSOLIDATION_1_0_VALIDATION.md",
            "docs/CONSOLIDATION_2_0.md",
            "manifests/visual_selection_engine_v2_certification.json",
            "tests_sim/test_consolidation_2_0.py",
            "tests_sim/test_professional_polish_v2.py",
            "tests_sim/test_termux_render_speed_v2.py",
            "tests_sim/test_v6_runtime.py",
            "tests_sim/test_v6_runtime_codecs.py",
        }
        offenders = sorted(tracked & forbidden)
        self.assertEqual(offenders, [], f"Legacy architecture artifacts tracked: {offenders}")

    def test_self_hosted_workflow_is_not_triggered_by_pull_requests(self):
        workflow = ROOT / ".github" / "workflows" / "shortautopro-remote.yml"
        text = workflow.read_text(encoding="utf-8").lower()
        self.assertIn("self-hosted", text)
        self.assertNotIn("pull_request:", text)
        self.assertNotIn("pull_request_target:", text)

    def test_remote_workflow_keeps_read_only_contents_permission(self):
        workflow = ROOT / ".github" / "workflows" / "shortautopro-remote.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", text)


if __name__ == "__main__":
    unittest.main()
