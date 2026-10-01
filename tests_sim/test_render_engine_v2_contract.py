import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import render_engine_v2 as engine


class RenderEngineV2ContractTests(unittest.TestCase):
    def test_state_machine_rejects_arbitrary_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = Path(tmp)
            (job / "state.json").write_text(json.dumps({"job_id":"x","status":"CREATED","history":[]}), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                engine.transition(job, "PASSED")

    def test_retry_preserves_job_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = Path(tmp)
            (job / "state.json").write_text(json.dumps({"job_id":"SID:render_001","status":"FAILED","history":[]}), encoding="utf-8")
            engine.transition(job, "RECOVERY_PENDING")
            engine.transition(job, "RETRYING")
            engine.transition(job, "RENDERING")
            state = json.loads((job / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["job_id"], "SID:render_001")

    def test_real_media_guard_rejects_placeholder_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sid = "guard"
            media = base / "imagens" / f"short_{sid}"
            media.mkdir(parents=True)
            (base / "roteiros").mkdir()
            (base / "audios").mkdir()
            (base / "videos").mkdir()
            (base / "manifests").mkdir()
            (media / "scene_01_placeholder.jpg").write_bytes(b"x" * 2048)
            scenes = [{"scene":1,"segment":"a","words":1}]
            (base / "roteiros" / f"scene_map_{sid}.json").write_text(json.dumps({"scenes":scenes}), encoding="utf-8")
            (base / "roteiros" / f"pro_edit_plan_{sid}.json").write_text(json.dumps({"scenes":[{"scene":1,"pace_multiplier":1}]}), encoding="utf-8")
            asset = media / "scene_01_placeholder.jpg"
            import hashlib
            (base / "manifests" / f"media_{sid}.json").write_text(json.dumps({
                "schema_version":"media-manifest-v2","short_id":sid,"immutable":True,"scene_count":1,
                "scenes":[{"scene_id":"1","scene_number":1,"query":"a","must_have":[],"avoid":[],
                           "asset":{"path":str(asset),"validated":True,
                                    "checksum_sha256":hashlib.sha256(asset.read_bytes()).hexdigest()}}]
            }), encoding="utf-8")
            (base / "audios" / f"short_{sid}.mp3").write_bytes(b"x")
            with mock.patch.object(engine, "BASE", base), mock.patch.object(engine, "audio_duration", return_value=1.0):
                with self.assertRaisesRegex(RuntimeError, "REAL_MEDIA_MISSING"):
                    engine.build_job(sid)

    def test_ffprobe_contract_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = Path(tmp)
            (job/"job.json").write_text(json.dumps({"short_id":"x","render_id":"render_001","duration_target":10}), encoding="utf-8")
            (job/"manifest.json").write_text(json.dumps({"short_id":"x","assets":[{"validation_status":"FROZEN_LOCAL"}]}), encoding="utf-8")
            output = job/"bad.mp4"
            output.write_bytes(b"x"*600000)
            fake = mock.Mock(returncode=0, stdout=json.dumps({"streams":[],"format":{"duration":"10"}}), stderr="")
            with mock.patch.object(engine, "run_cmd", return_value=fake):
                report=engine.ffprobe_validator(output,job)
            self.assertEqual(report["quality_gate"], "FAIL")
            self.assertIn("VIDEO_STREAM_MISSING", report["errors"])


if __name__ == "__main__":
    unittest.main()
