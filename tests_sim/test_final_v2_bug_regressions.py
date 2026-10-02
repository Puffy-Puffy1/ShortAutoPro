import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import media_engine_v2
import render_plan_v2
import resume_short_runtime


class FinalV2BugRegressionTests(unittest.TestCase):
    def test_query_relaxed_requires_at_least_one_must_hit(self):
        candidate = {
            "fonte": "Mock", "id": "zero", "must_hits": 0,
            "avoid_hits": 0, "score": 80, "url": "x"
        }
        with patch.object(media_engine_v2.PROVIDER, "search", side_effect=[[candidate], [candidate]]),              patch.object(media_engine_v2.PROVIDER, "prepare", return_value=[]):
            with tempfile.TemporaryDirectory() as td:
                with self.assertRaisesRegex(RuntimeError, "MEDIA"):
                    media_engine_v2.acquire_scene(
                        "MUST_001", 1,
                        {"query": "ship radio", "must_have": ["ship", "radio"], "avoid": []},
                        Path(td),
                    )

    def test_render_plan_rejects_path_traversal_short_id(self):
        with self.assertRaisesRegex(RuntimeError, "short_id"):
            render_plan_v2.validate_short_id("../evil")

    def test_render_plan_rejects_duplicate_scene_ids(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            render_plan_v2.BASE = base
            sid = "PLAN_001"
            (base / "roteiros").mkdir()
            (base / "roteiros" / f"scene_map_{sid}.json").write_text(
                json.dumps({"scenes": [{"scene_id": "same"}, {"scene_id": "same"}]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "scene_id"):
                render_plan_v2.main(sid)

    def test_resume_rejects_tampered_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            resume_short_runtime.BASE = base
            sid = "RESUME_001"
            (base / "roteiros").mkdir()
            (base / "manifests").mkdir()
            (base / "imagens" / f"short_{sid}").mkdir(parents=True)
            (base / "roteiros" / f"pro_edit_plan_{sid}.json").write_text(
                json.dumps({
                    "schema_version": "render-plan-v2",
                    "short_id": sid,
                    "scenes": [{"scene_id": "1"}],
                }),
                encoding="utf-8",
            )
            asset = base / "imagens" / f"short_{sid}" / "scene_01.jpg"
            asset.write_bytes(b"x" * 2000)
            manifest = {
                "schema_version": "media-manifest-v2",
                "short_id": sid,
                "immutable": True,
                "scene_count": 1,
                "scenes": [{
                    "scene_id": "1",
                    "scene_number": 1,
                    "asset": {
                        "validated": True,
                        "path": str(asset),
                        "checksum_sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
                    },
                }],
            }
            unsigned = dict(manifest)
            manifest["integrity_sha256"] = hashlib.sha256(
                json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            manifest["scenes"][0]["asset"]["checksum_sha256"] = "tampered"
            (base / "manifests" / f"media_{sid}.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            with patch.object(resume_short_runtime, "expected_scenes", return_value=1):
                self.assertFalse(resume_short_runtime.consolidation_plan_ok(sid))


if __name__ == "__main__":
    unittest.main()
