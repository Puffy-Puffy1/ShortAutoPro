import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LocalRuntimeAuditScopeTests(unittest.TestCase):
    def test_ignored_local_python_does_not_pollute_repository_audit(self):
        probe = ROOT / "temp" / "audit_scope_probe.py"
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text("print('local ignored probe')\n", encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "tools/repo_audit.py"],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload.get("scope"), "tracked_git_files")
            self.assertEqual(payload.get("status"), "PASS")
            inactive = payload.get("inactive_code") or []
            self.assertNotIn("temp/audit_scope_probe.py", inactive)
        finally:
            probe.unlink(missing_ok=True)

    def test_professional_runtime_reports_are_ignored(self):
        paths = [
            "roteiros/pro_caption_client_example_001.json",
            "roteiros/pro_edit_plan_client_example_001.json",
            "roteiros/pro_edit_plan_pre_repair_client_example_001.json",
            "roteiros/pro_edit_runtime_client_example_001.json",
            "roteiros/supervisor_client_example_001.json",
            "roteiros/visual_shot_bridge_client_example_001.json",
        ]
        for path in paths:
            proc = subprocess.run(
                ["git", "check-ignore", "--no-index", "--quiet", path],
                cwd=ROOT,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, f"not ignored: {path}")


if __name__ == "__main__":
    unittest.main()
