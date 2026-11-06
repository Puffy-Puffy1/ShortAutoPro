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
            self.assertEqual(payload.get("classification"), "static_reference_graph")
            production = payload.get("production_code") or []
            test_only = payload.get("test_only_code") or []
            inactive = payload.get("inactive_code") or []
            self.assertIn("main.py", production)
            for compatibility_module in (
                "media_stage_runtime.py",
                "midia.py",
                "media_runtime_adapter_v1.py",
                "media_runtime_adapter_v2.py",
                "vg4x_bridge.py",
            ):
                self.assertNotIn(compatibility_module, production)
                self.assertIn(compatibility_module, test_only)
            self.assertEqual(payload.get("production_code_count"), len(production))
            self.assertEqual(payload.get("test_only_code_count"), len(test_only))
            self.assertEqual(payload.get("inactive_code_count"), len(inactive))
            self.assertNotIn("temp/audit_scope_probe.py", inactive)
        finally:
            probe.unlink(missing_ok=True)

    def test_python_graph_ignores_blacklist_literals_but_tracks_called_scripts(self):
        import tempfile
        from tools.map_active_graph import refs_from_python

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "caller.py"
            source.write_text(
                'FORBIDDEN = ("media_stage_runtime.py",)\\n'
                'p.run("Media stage", "media_engine_v2.py")\\n',
                encoding="utf-8",
            )
            refs = refs_from_python(
                source,
                {
                    "media_stage_runtime.py",
                    "media_engine_v2.py",
                },
                {},
            )

        self.assertIn("media_engine_v2.py", refs)
        self.assertNotIn("media_stage_runtime.py", refs)

    def test_python_graph_indexes_call_literals_once_per_file(self):
        import tempfile
        from unittest.mock import patch
        import tools.map_active_graph as graph

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "caller.py"
            source.write_text(
                'p.run("first", "media_engine_v2.py")\n'
                'p.run("second", "render_engine_v2.py")\n',
                encoding="utf-8",
            )
            with patch.object(
                graph,
                "refs_from_text",
                wraps=graph.refs_from_text,
            ) as indexed:
                refs = graph.refs_from_python(
                    source,
                    {"media_engine_v2.py", "render_engine_v2.py"},
                    {},
                )

        self.assertEqual(indexed.call_count, 1)
        self.assertEqual(refs, {"media_engine_v2.py", "render_engine_v2.py"})

    def test_static_graph_separates_production_and_test_only_code(self):
        from tools.map_active_graph import classify_reachability

        graph = {
            "main.py": {"pipeline.py"},
            "pipeline.py": set(),
            "tests_sim/test_legacy.py": {"legacy_compat.py"},
            "legacy_compat.py": set(),
            "unused.py": set(),
        }
        result = classify_reachability(
            graph=graph,
            code_paths=[
                "main.py",
                "pipeline.py",
                "tests_sim/test_legacy.py",
                "legacy_compat.py",
                "unused.py",
            ],
            production_seeds={"main.py"},
            test_seeds={"tests_sim/test_legacy.py"},
        )

        self.assertEqual(result["production_code"], ["main.py", "pipeline.py"])
        self.assertEqual(
            result["test_only_code"],
            ["legacy_compat.py", "tests_sim/test_legacy.py"],
        )
        self.assertEqual(result["inactive_code"], ["unused.py"])

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
