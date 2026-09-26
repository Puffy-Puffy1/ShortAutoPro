import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import batch_runtime as br


class FakeProc:
    def __init__(self, code=0, text=""):
        self.returncode = code
        self.stdout = text


class BatchRuntimeTests(unittest.TestCase):
    def sandbox(self):
        tmp = tempfile.TemporaryDirectory()
        base = Path(tmp.name)
        for name in ["queue", "reports/batch", "logs/lotes", ".sap_state", "roteiros", "imagens", "audios", "videos", "manifests"]:
            (base / name).mkdir(parents=True, exist_ok=True)
        for name in ["main.py", "release_artifact_guard.py", "config.sh"]:
            (base / name).write_text("# test\n", encoding="utf-8")
        patches = [
            mock.patch.object(br, "BASE", base),
            mock.patch.object(br, "QUEUE", base / "queue"),
            mock.patch.object(br, "STATE_FILE", base / "queue" / "batch_state.json"),
            mock.patch.object(br, "LOCK_FILE", base / "queue" / ".batch_runtime.lock"),
            mock.patch.object(br, "REPORT_DIR", base / "reports" / "batch"),
            mock.patch.object(br, "LOG_DIR", base / "logs" / "lotes"),
        ]
        for p in patches:
            p.start()
        self.addCleanup(tmp.cleanup)
        for p in reversed(patches):
            self.addCleanup(p.stop)
        return base

    def test_batch_10_has_unique_per_item_identity(self):
        self.sandbox()
        state = br.make_state(10)
        ids = [x["short_id"] for x in state["items"]]
        self.assertEqual(len(ids), 10)
        self.assertEqual(len(set(ids)), 10)
        self.assertEqual([x["index"] for x in state["items"]], list(range(1, 11)))

    def test_partial_item_uses_resume_same_short_id(self):
        base = self.sandbox()
        state = br.make_state(2)
        item = state["items"][1]
        sid = item["short_id"]
        (base / "roteiros" / f"scene_map_{sid}.json").write_text("{}", encoding="utf-8")
        with mock.patch.object(br, "release_ok", return_value=False):
            cmd, mode = br.command_for(item)
        self.assertEqual(mode, "resume")
        self.assertEqual(cmd[-2:], ["--short-id", sid])
        self.assertNotIn("--reuse-short-id", cmd)

    def test_clean_env_does_not_leak_previous_short_transients(self):
        self.sandbox()
        with mock.patch.dict(os.environ, {
            "SHORT_ID": "old", "SAP_REUSE_SHORT_ID": "1",
            "SHORT_TOPIC_EXACT": "old topic", "SHORT_ALLOW_REPEAT_TOPIC": "1",
            "KEEP_ME": "yes",
        }, clear=False):
            env = br.clean_env("new")
        self.assertEqual(env["SHORT_ID"], "new")
        self.assertEqual(env["KEEP_ME"], "yes")
        self.assertNotIn("SAP_REUSE_SHORT_ID", env)
        self.assertNotIn("SHORT_TOPIC_EXACT", env)
        self.assertNotIn("SHORT_ALLOW_REPEAT_TOPIC", env)

    def test_failure_in_middle_does_not_stop_later_items_and_recovers(self):
        self.sandbox()
        state = br.make_state(5)
        attempts = {}
        completed = set()

        def release(sid):
            return sid in completed

        def run(cmd, **kwargs):
            sid = kwargs["env"]["SHORT_ID"]
            idx = int(sid.rsplit("_", 1)[1])
            attempts[idx] = attempts.get(idx, 0) + 1
            if idx == 3 and attempts[idx] == 1:
                return FakeProc(1, "MEDIA_STAGE_RUNTIME=EXHAUSTED")
            completed.add(sid)
            return FakeProc(0, "ok")

        with (
            mock.patch.object(br, "release_ok", side_effect=release),
            mock.patch.object(br.subprocess, "run", side_effect=run),
            mock.patch.object(br.time, "sleep"),
            mock.patch.object(br, "last_stage", return_value="6"),
        ):
            rc = br.execute(state, max_attempts=3, recovery_rounds=2)

        self.assertEqual(rc, 0)
        self.assertEqual([x["status"] for x in state["items"]], ["completed"] * 5)
        self.assertEqual(attempts[3], 2)
        self.assertEqual(attempts[4], 1)
        self.assertEqual(attempts[5], 1)

    def test_two_failures_recover_independently(self):
        self.sandbox()
        state = br.make_state(10)
        completed = set()
        attempts = {}

        def release(sid):
            return sid in completed

        def run(cmd, **kwargs):
            sid = kwargs["env"]["SHORT_ID"]
            idx = int(sid.rsplit("_", 1)[1])
            attempts[idx] = attempts.get(idx, 0) + 1
            if idx == 2 and attempts[idx] == 1:
                return FakeProc(1, "provider timeout")
            if idx == 7 and attempts[idx] == 1:
                return FakeProc(1, "RENDER_INVALID")
            completed.add(sid)
            return FakeProc(0, "ok")

        with (
            mock.patch.object(br, "release_ok", side_effect=release),
            mock.patch.object(br.subprocess, "run", side_effect=run),
            mock.patch.object(br.time, "sleep"),
            mock.patch.object(br, "last_stage", return_value="6"),
        ):
            rc = br.execute(state, max_attempts=3, recovery_rounds=2)

        self.assertEqual(rc, 0)
        self.assertEqual(sum(x["status"] == "completed" for x in state["items"]), 10)
        self.assertEqual(attempts[2], 2)
        self.assertEqual(attempts[7], 2)

    def test_global_storage_failure_stops_batch(self):
        self.sandbox()
        state = br.make_state(5)
        with (
            mock.patch.object(br, "release_ok", return_value=False),
            mock.patch.object(br.subprocess, "run", return_value=FakeProc(1, "STORAGE_LOW")),
            mock.patch.object(br.time, "sleep"),
            mock.patch.object(br, "last_stage", return_value="preflight"),
        ):
            rc = br.execute(state, max_attempts=3, recovery_rounds=2)
        self.assertEqual(rc, 1)
        self.assertEqual(state["items"][0]["status"], "blocked_global")
        self.assertEqual(state["items"][1]["status"], "queued")

    def test_legacy_retry_state_migrates_failed_slot_not_completed_prefix(self):
        self.sandbox()
        data = {
            "version": "BATCH_STATE_2.0_CONTIGUOUS", "batch_id": "x",
            "total": 5, "current": 2, "successes": 2, "failures": 1,
            "status": "retry_pending",
        }
        out = br.migrate_legacy(data)
        self.assertEqual([x["status"] for x in out["items"]],
                         ["completed", "completed", "retry_pending", "queued", "queued"])
        self.assertEqual(out["items"][2]["short_id"], "x_03")

    def test_state_write_is_atomic_and_valid(self):
        self.sandbox()
        state = br.make_state(5)
        br.save_state(state)
        loaded = br.load_state()
        self.assertEqual(loaded["version"], br.VERSION)
        self.assertEqual(len(loaded["items"]), 5)

    def test_active_batch_lock_blocks_second_runner(self):
        self.sandbox()
        with br.BatchLock():
            with self.assertRaises(RuntimeError):
                with br.BatchLock():
                    pass

    def test_exact_release_short_id_controls_completion(self):
        self.sandbox()
        state = br.make_state(1)
        item = state["items"][0]
        requested = []
        def rel(sid):
            requested.append(sid)
            return True
        with mock.patch.object(br, "release_ok", side_effect=rel):
            failure = br.run_item(state, item)
        self.assertIsNone(failure)
        self.assertEqual(item["status"], "completed")
        self.assertTrue(requested)
        self.assertTrue(all(sid == item["short_id"] for sid in requested))


if __name__ == "__main__":
    unittest.main()
