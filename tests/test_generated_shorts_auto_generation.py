import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import media_engine_v2


class AutomaticLocalShortsGenerationTests(unittest.TestCase):
    def test_builds_one_prompt_per_scene_and_runs_local_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "backend.json"
            config.write_text("{}", encoding="utf-8")
            manifest = root / "generated_manifest.json"
            manifest.write_text("{}", encoding="utf-8")
            settings = {"fps": 12, "seed": 7, "model": "fixture", "timeout_seconds": 60}
            class FakeStore:
                def __init__(self):
                    self.created = None
                def create_project(self, project_id, spec):
                    self.created = (project_id, spec)
                    return {"status": "CREATED"}
            fake_store = FakeStore()
            class FakeWorker:
                def __init__(self, store, backend, **kwargs):
                    self.store = store
                    self.settings = kwargs
                def run_until_idle(self, project_id):
                    return {"status": "PROJECT_COMPLETE", "project_id": project_id}
            with patch("generative_video_poc.state_store.ProjectStore", return_value=fake_store), \
                 patch("generative_video_poc.worker.load_backend_config", return_value=("backend", settings)), \
                 patch("generative_video_poc.worker.LocalQueueWorker", FakeWorker), \
                 patch("generative_video_poc.manifest.build_ready_manifest", return_value={"manifest_path": str(manifest)}) as export:
                result = media_engine_v2._generate_local_shorts_manifest(
                    "short_demo",
                    [
                        {"segment": "A forest expedition", "query": "forest", "must_have": ["forest"]},
                        {"segment": "A river crossing", "query": "river", "avoid": ["cartoon"]},
                    ],
                    config,
                )
            self.assertEqual(result, str(manifest))
            project_id, spec = fake_store.created
            self.assertTrue(project_id.startswith("short_short_demo_"))
            self.assertEqual(spec.kind, "shorts")
            self.assertEqual(spec.aspect_ratio, "9:16")
            self.assertEqual(len(spec.clip_prompts), 2)
            self.assertIn("forest", spec.clip_prompts[0])
            self.assertIn("Avoid showing: cartoon", spec.clip_prompts[1])
            export.assert_called_once_with(fake_store, project_id)

    def test_fails_closed_when_local_worker_does_not_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "backend.json"
            config.write_text("{}", encoding="utf-8")
            class FakeStore:
                def create_project(self, project_id, spec):
                    return {"status": "CREATED"}
            class FakeWorker:
                def __init__(self, *args, **kwargs):
                    pass
                def run_until_idle(self, project_id):
                    return {"status": "PROJECT_FAILED", "failure": {"error": "fixture"}}
            with patch("generative_video_poc.state_store.ProjectStore", FakeStore), \
                 patch("generative_video_poc.worker.load_backend_config", return_value=("backend", {
                     "fps": 12, "seed": 1, "model": "fixture", "timeout_seconds": 60,
                 })), patch("generative_video_poc.worker.LocalQueueWorker", FakeWorker), \
                 patch("generative_video_poc.manifest.build_ready_manifest") as export:
                with self.assertRaisesRegex(RuntimeError, "GENERATION_INCOMPLETE"):
                    media_engine_v2._generate_local_shorts_manifest(
                        "short_demo",
                        [{"segment": "A forest", "query": "forest"}],
                        config,
                    )
            export.assert_not_called()


if __name__ == "__main__":
    unittest.main()
