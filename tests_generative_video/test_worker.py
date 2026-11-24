import tempfile
import unittest
from pathlib import Path

from generative_video_poc.state_store import ProjectStore
from generative_video_poc.worker import LocalQueueWorker, WorkerConfigError


def project_spec(prompt="A cinematic documentary scene"):
    return {
        "kind": "shorts",
        "target_duration_seconds": 10,
        "aspect_ratio": "9:16",
        "width": 360,
        "height": 640,
        "clip_seconds": 10,
        "prompt_template": prompt,
    }


class FakeBackend:
    def generate_clip(self, **kwargs):
        raise AssertionError("backend_call injection should be used")


class QueueWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = ProjectStore(self.root)
        self.store.create_project("worker-test", project_spec())

    def tearDown(self):
        self.temp.cleanup()

    def worker(self, call, **kwargs):
        return LocalQueueWorker(
            self.store, FakeBackend(), worker_id="test-worker",
            timeout_seconds=30, backend_call=call, **kwargs,
        )

    def test_worker_generates_and_commits_one_ffprobe_validated_clip(self):
        def generate(**kwargs):
            output = kwargs["output"]
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"fixture video bytes")
            self.assertEqual(kwargs["prompt"], "A cinematic documentary scene")
            self.assertEqual(kwargs["frames"], 120)
            return {
                "status": "GENERATED_AND_PROBED", "path": str(output),
                "duration_seconds": 10.0, "video_codec": "h264",
                "width": 360, "height": 640,
            }
        result = self.worker(generate).run_one("worker-test")
        self.assertEqual(result["status"], "CLIP_READY")
        self.assertEqual(result["progress"]["ready"], 1)
        self.assertEqual(self.store.get_project("worker-test")["status"], "COMPLETE")

    def test_missing_prompt_fails_before_claiming_work(self):
        self.store.create_project("no-prompt", project_spec(prompt=""))
        with self.assertRaises(WorkerConfigError):
            self.worker(lambda **kwargs: {}).run_one("no-prompt")
        self.assertEqual(self.store.get_project("no-prompt")["progress"]["pending"], 1)

    def test_invalid_dimensions_are_rejected_and_clip_is_retryable(self):
        def generate(**kwargs):
            output = kwargs["output"]
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"invalid dimensions")
            return {
                "status": "GENERATED_AND_PROBED", "path": str(output),
                "duration_seconds": 10.0, "video_codec": "h264",
                "width": 640, "height": 360,
            }
        result = self.worker(generate).run_one("worker-test")
        self.assertEqual(result["status"], "CLIP_FAILED")
        self.assertEqual(result["retry_status"], "PENDING")
        output = self.store.project_dir("worker-test") / "clips" / "clip_00001_attempt_01.mp4"
        self.assertFalse(output.exists())

    def test_drain_processes_all_clips_until_project_is_complete(self):
        self.store.create_project("worker-batch", {
            **project_spec(), "target_duration_seconds": 20,
        })
        calls = []
        def generate(**kwargs):
            calls.append(kwargs["output"])
            output = kwargs["output"]
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"fixture video bytes")
            return {
                "status": "GENERATED_AND_PROBED", "path": str(output),
                "duration_seconds": 10.0, "video_codec": "h264",
                "width": 360, "height": 640,
            }
        result = self.worker(generate).run_until_idle("worker-batch")
        self.assertEqual(result["status"], "PROJECT_COMPLETE")
        self.assertEqual(result["generated_clips"], 2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["progress"]["ready"], 2)

    def test_drain_stops_after_non_retryable_failure(self):
        self.store.create_project("worker-fail", project_spec())
        def generate(**kwargs):
            raise ValueError("invalid generator arguments")
        result = self.worker(generate).run_until_idle("worker-fail")
        self.assertEqual(result["status"], "PROJECT_FAILED")
        self.assertEqual(result["progress"]["failed"], 1)

    def test_prompt_placeholders_are_limited_to_clip_metadata(self):
        claim = {"clip_index": 3, "start_seconds": 20, "duration_seconds": 10}
        self.assertEqual(
            LocalQueueWorker._prompt("Scene {clip_index} from {start_seconds} for {duration_seconds}", claim),
            "Scene 3 from 20 for 10",
        )
        with self.assertRaises(WorkerConfigError):
            LocalQueueWorker._prompt("Run {shell}", claim)


if __name__ == "__main__":
    unittest.main()
