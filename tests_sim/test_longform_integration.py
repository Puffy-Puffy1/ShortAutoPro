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

    def test_main_exposes_longform_under_the_canonical_entrypoint(self):
        with mock.patch.object(main, "source_config") as source, \\
             mock.patch.object(main, "setup_env") as setup, \\
             mock.patch.object(main, "run_group", return_value=mock.Mock(returncode=0)) as runner, \\
             mock.patch("sys.argv", [
                 "main.py", "longform", "run", "--topic", "História do Brasil",
                 "--minutes", "20", "--chapters", "5", "--profile", "true_crime",
             ]):
            self.assertEqual(main.cli(), 0)

        source.assert_called_once_with()
        setup.assert_called_once_with()
        command = runner.call_args.args[0]
        self.assertEqual(Path(command[1]).name, "longform_runtime.py")
        self.assertEqual(command[2:], [
            "run", "--topic", "História do Brasil", "--minutes", "20",
            "--profile", "true_crime", "--chapters", "5",
        ])


if __name__ == "__main__":
    unittest.main()
