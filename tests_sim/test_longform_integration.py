import unittest
from unittest import mock
from pathlib import Path

import main
from longform_runtime import validate_run_id, resume


class LongFormIntegrationTests(unittest.TestCase):
    def test_run_id_accepts_generated_identifiers(self):
        self.assertEqual(validate_run_id("20261124_120000_topic_name"), "20261124_120000_topic_name")
        self.assertEqual(validate_run_id("manual-run_01"), "manual-run_01")

    def test_run_id_rejects_path_traversal_and_invalid_names(self):
        for value in ("../outside", "folder/run", "..", "", "/tmp/file", "a" * 81):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_run_id(value)

    def test_resume_rejects_unsafe_id_before_reading_files(self):
        with self.assertRaises(ValueError):
            resume("../outside")

    def _run_cli(self, argv, returncode=0):
        runner_result = mock.Mock(returncode=returncode)
        with mock.patch.object(main, "source_config") as source, \
             mock.patch.object(main, "setup_env") as setup, \
             mock.patch.object(main, "run_group", return_value=runner_result) as runner, \
             mock.patch("sys.argv", argv):
            result = main.cli()
        source.assert_called_once_with()
        setup.assert_called_once_with()
        command = runner.call_args.args[0]
        self.assertEqual(Path(command[1]).name, "longform_runtime.py")
        self.assertEqual(runner.call_args.kwargs["env"], __import__("os").environ.copy())
        return result, command

    def test_main_exposes_longform_run_under_canonical_entrypoint(self):
        result, command = self._run_cli([
            "main.py", "longform", "run", "--topic", "História do Brasil",
            "--minutes", "20", "--chapters", "5", "--profile", "true_crime",
        ])
        self.assertEqual(result, 0)
        self.assertEqual(command[2:], [
            "run", "--topic", "História do Brasil", "--minutes", "20",
            "--profile", "true_crime", "--chapters", "5",
        ])

    def test_main_dispatches_resume_and_status_with_run_id(self):
        for action in ("resume", "status"):
            with self.subTest(action=action):
                result, command = self._run_cli([
                    "main.py", "longform", action, "--run-id", "run_2026_01",
                ])
                self.assertEqual(result, 0)
                self.assertEqual(command[2:], [action, "--run-id", "run_2026_01"])

    def test_main_forwards_optional_generated_manifest(self):
        manifest = "/tmp/generated/project_01/generated_manifest.json"
        result, command = self._run_cli([
            "main.py", "longform", "run", "--topic", "Tema", "--generated-manifest", manifest,
        ])
        self.assertEqual(result, 0)
        self.assertIn("--generated-manifest", command)
        self.assertEqual(command[command.index("--generated-manifest") + 1], manifest)

    def test_main_returns_timeout_exit_code(self):
        with mock.patch.object(main, "source_config"), \
             mock.patch.object(main, "setup_env"), \
             mock.patch.object(main, "run_group", side_effect=__import__("subprocess").TimeoutExpired("longform", 10)), \
             mock.patch("sys.argv", ["main.py", "longform", "run", "--topic", "Teste"]):
            self.assertEqual(main.cli(), 124)


if __name__ == "__main__":
    unittest.main()
