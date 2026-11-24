import sys
import unittest
from unittest.mock import patch

import main


class GeneratedShortsCliTests(unittest.TestCase):
    def test_run_forwards_generated_clips_manifest(self):
        manifest = "/tmp/shorts_project/generated_manifest.json"
        with patch.object(sys, "argv", [
            "main.py", "run", "--generated-clips-manifest", manifest,
        ]), patch.object(main, "run_pipeline", return_value=0) as run:
            self.assertEqual(main.cli(), 0)
        run.assert_called_once_with(
            reuse_short_id=False,
            generated_clips_manifest=manifest,
        )


if __name__ == "__main__":
    unittest.main()
