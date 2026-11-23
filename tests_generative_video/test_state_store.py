import concurrent.futures
import tempfile
import unittest
from pathlib import Path

from generative_video_poc.contracts import ProjectSpec
from generative_video_poc.state_store import LeaseError, ProjectConflict, ProjectStore


def spec(seconds=20):
    return ProjectSpec.from_dict({
        "kind": "shorts", "target_duration_seconds": seconds,
        "aspect_ratio": "9:16", "width": 360, "height": 640, "clip_seconds": 10,
    })


class ProjectStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = ProjectStore(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_create_is_idempotent_and_spec_is_immutable(self):
        first = self.store.create_project("sample-01", spec())
        second = self.store.create_project("sample-01", spec())
        self.assertEqual(first["progress"]["total"], 2)
        self.assertEqual(second["progress"]["pending"], 2)
        with self.assertRaises(ProjectConflict):
            self.store.create_project("sample-01", spec(30))

    def test_rejects_path_traversal_project_ids(self):
        with self.assertRaises(ValueError):
            self.store.create_project("../outside", spec())
        with self.assertRaises(ValueError):
            self.store.project_dir("a/b")

    def test_parallel_workers_claim_distinct_clips(self):
        self.store.create_project("parallel", spec(40))
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(self.store.claim_next_clip, f"worker-{i}", project_id="parallel")
                for i in range(2)
            ]
            claims = [future.result() for future in futures]
        self.assertEqual(len({claim["clip_index"] for claim in claims}), 2)
        self.assertEqual({claim["status"] for claim in claims}, {"RUNNING"})

    def test_lease_renewal_and_expiry_reject_stale_worker(self):
        self.store.create_project("lease", spec(10))
        claim = self.store.claim_next_clip("worker-a", project_id="lease", lease_seconds=10, now=100)
        self.assertEqual(
            self.store.renew_lease("lease", 1, "worker-a", claim["lease_token"],
                                   lease_seconds=30, now=105),
            135,
        )
        recovered = self.store.claim_next_clip("worker-b", project_id="lease", now=136)
        self.assertEqual(recovered["clip_index"], 1)
        self.assertEqual(recovered["attempts"], 2)
        with self.assertRaises(LeaseError):
            self.store.fail_clip("lease", 1, "worker-a", claim["lease_token"], "OLD_WORKER", now=137)

    def test_completion_requires_probe_metadata_and_project_local_file(self):
        self.store.create_project("complete", spec(10))
        claim = self.store.claim_next_clip("worker", project_id="complete", now=100)
        clip_dir = self.store.project_dir("complete") / "clips"
        clip_dir.mkdir(parents=True, exist_ok=True)
        output = clip_dir / "clip-001.mp4"
        output.write_bytes(b"fixture bytes used only by the unit test")
        valid = {"status": "GENERATED_AND_PROBED", "duration_seconds": 10, "video_codec": "h264"}
        with self.assertRaisesRegex(ValueError, "FFprobe-validated"):
            self.store.complete_clip("complete", 1, "worker", claim["lease_token"], output,
                                     {"status": "NOT_PROBED", "duration_seconds": 10}, now=101)
        outside = self.root / "outside.mp4"
        outside.write_bytes(b"fixture")
        with self.assertRaisesRegex(ValueError, "inside its project"):
            self.store.complete_clip("complete", 1, "worker", claim["lease_token"], outside, valid, now=101)
        result = self.store.complete_clip(
            "complete", 1, "worker", claim["lease_token"], output,
            {**valid, "width": 360, "height": 640}, now=101,
        )
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["progress"]["ready"], 1)

    def test_retry_limit_is_persisted_and_cannot_be_bypassed(self):
        self.store.create_project("retry", spec(10), max_attempts=2)
        claim = self.store.claim_next_clip("worker", project_id="retry", now=100)
        status = self.store.fail_clip("retry", 1, "worker", claim["lease_token"],
                                      "MODEL_OUT_OF_MEMORY", retryable=True, now=101)
        self.assertEqual(status, "PENDING")
        claim2 = self.store.claim_next_clip("worker", project_id="retry", now=102)
        status2 = self.store.fail_clip("retry", 1, "worker", claim2["lease_token"],
                                       "MODEL_OUT_OF_MEMORY", retryable=True, now=103)
        self.assertEqual(status2, "FAILED")
        self.assertIsNone(self.store.claim_next_clip("worker-2", project_id="retry", now=104))
        self.assertEqual(self.store.get_project("retry")["status"], "FAILED")

    def test_expired_lease_recovers_after_store_reopen(self):
        self.store.create_project("resume", spec(10))
        claim = self.store.claim_next_clip("old-worker", project_id="resume", lease_seconds=10, now=100)
        reopened = ProjectStore(self.root)
        resumed = reopened.claim_next_clip("new-worker", project_id="resume", now=111)
        self.assertEqual(resumed["clip_index"], claim["clip_index"])
        self.assertEqual(resumed["attempts"], 2)
        self.assertEqual(reopened.get_project("resume")["progress"]["running"], 1)

    def test_empty_queue_returns_none(self):
        self.store.create_project("empty", spec(10))
        self.assertIsNotNone(self.store.claim_next_clip("worker", project_id="empty", now=100))
        self.assertIsNone(self.store.claim_next_clip("worker-2", project_id="empty", now=101))


if __name__ == "__main__":
    unittest.main()
