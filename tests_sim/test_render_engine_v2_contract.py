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
            scenes = [{"scene_id":"1","scene":1,"segment":"a","words":1}]
            frozen_scene_map = {
                "schema_version":"SCENE_MAP_FROZEN_1.0","short_id":sid,
                "mutable_upstream_closed":True,"scenes":scenes
            }
            (base / "manifests" / f"scene_map_{sid}.json").write_text(json.dumps(frozen_scene_map), encoding="utf-8")
            asset = media / "scene_01_placeholder.jpg"
            import hashlib
            asset_sha = hashlib.sha256(asset.read_bytes()).hexdigest()
            manifest = {
                "schema_version":"media-manifest-v2","short_id":sid,"immutable":True,"scene_count":1,
                "scenes":[{"scene_id":"1","scene_number":1,"query":"a","must_have":[],"avoid":[],
                           "asset":{"path":str(asset),"validated":True,"checksum_sha256":asset_sha}}]
            }
            manifest["integrity_sha256"] = engine._manifest_integrity(manifest)
            (base / "manifests" / f"media_{sid}.json").write_text(json.dumps(manifest), encoding="utf-8")
            plan = {
                "schema_version":"render-plan-v2","short_id":sid,"immutable":True,
                "scenes":[{"scene_id":"1","pace_multiplier":1}]
            }
            plan["integrity_sha256"] = engine._manifest_integrity(plan)
            (base / "roteiros" / f"pro_edit_plan_{sid}.json").write_text(json.dumps(plan), encoding="utf-8")
            (base / "audios" / f"short_{sid}.mp3").write_bytes(b"x")
            (base / "videos" / f"short_{sid}.ass").write_text(
                "[Script Info]\\nScriptType: v4.00+\\n[V4+ Styles]\\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\\nStyle: Default,Arial,40,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,1,2,0,2,10,10,10,1\\n[Events]\\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\\nDialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,test\\n",
                encoding="utf-8"
            )
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
