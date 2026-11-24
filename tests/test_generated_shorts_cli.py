import sys
import unittest
from unittest.mock import patch

import main
import resume_short_runtime


class GeneratedShortsCliTests(unittest.TestCase):
    def test_resume_restores_saved_generated_manifest(self):
        import json
        import os
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "generated_manifest.json"
            manifest.write_text("{}", encoding="utf-8")
            state_dir = root / ".sap_state"
            state_dir.mkdir()
            (state_dir / "pipeline_demo.json").write_text(json.dumps({
                "generated_clips_manifest": str(manifest),
            }), encoding="utf-8")
            with patch.object(resume_short_runtime.canonical, "STATE_DIR", state_dir), \
                 patch.dict(os.environ, {}, clear=False):
                os.environ.pop("SAP_GENERATED_CLIPS_MANIFEST", None)
                restored = resume_short_runtime.restore_generated_manifest("demo")
                self.assertEqual(restored, str(manifest.resolve()))
                self.assertEqual(os.environ["SAP_GENERATED_CLIPS_MANIFEST"], str(manifest.resolve()))

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
