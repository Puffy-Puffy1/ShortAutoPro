import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from generative_video_poc.brain import main


class BrainCliTests(unittest.TestCase):
    def test_create_list_show_and_claim_use_local_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "sap"
            spec_path = Path(temp) / "short.json"
            spec_path.write_text(json.dumps({
                "kind": "shorts", "target_duration_seconds": 20,
                "aspect_ratio": "9:16", "width": 360, "height": 640, "clip_seconds": 10,
            }), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["create", "cli-project", "--spec-file", str(spec_path),
                                       "--root", str(root)]), 0)
            created = json.loads(output.getvalue())
            self.assertEqual(created["progress"]["total"], 2)

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["list", "--root", str(root)]), 0)
            listed = json.loads(output.getvalue())
            self.assertEqual(listed[0]["project_id"], "cli-project")

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["show", "cli-project", "--root", str(root)]), 0)
            shown = json.loads(output.getvalue())
            self.assertEqual(shown["status"], "QUEUED")

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["claim", "--project-id", "cli-project",
                                       "--worker", "cli-test", "--root", str(root)]), 0)
            claim = json.loads(output.getvalue())
            self.assertEqual(claim["status"], "RUNNING")
            self.assertTrue(claim["lease_token"])
            self.assertIn("attempt_01", claim["output_path"])


if __name__ == "__main__":
    unittest.main()
