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
