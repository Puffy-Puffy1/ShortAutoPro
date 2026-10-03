import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import media_engine_v2
import resume_short_runtime


class FinalV2HardeningTests(unittest.TestCase):
    def test_media_engine_rejects_duplicate_scene_ids(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            old = media_engine_v2.BASE
            media_engine_v2.BASE = base
            try:
                (base / "roteiros").mkdir(parents=True)
                sid = "DUP_001"
                (base / "roteiros" / f"scene_map_{sid}.json").write_text(
                    json.dumps({"scenes": [
                        {"scene_id": "same", "query": "ship"},
                        {"scene_id": "same", "query": "radio"},
                    ]}),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(RuntimeError, "duplicate_scene_id"):
                    media_engine_v2.load_scene_map(sid)
            finally:
                media_engine_v2.BASE = old

    def test_existing_sidecar_must_match_short_id_and_scene_number(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            old = media_engine_v2.BASE
            media_engine_v2.BASE = base
            try:
                sid = "SIDE_001"
                folder = base / "imagens" / f"short_{sid}"
                folder.mkdir(parents=True)
                asset = folder / "scene_01.jpg"
                # Minimal JPEG signature plus payload; validation is mocked because
                # this test targets the sidecar identity boundary.
                asset.write_bytes(b"\xff\xd8\xff" + b"x" * 2000)
                digest = hashlib.sha256(asset.read_bytes()).hexdigest()
                sidecar = {
                    "validated": True,
                    "checksum_sha256": digest,
                    "short_id": "OTHER_001",
                    "scene_number": 1,
                    "must_total": 0,
                }
                (folder / "scene_01.json").write_text(
                    json.dumps(sidecar), encoding="utf-8"
                )
                with patch.object(
                    media_engine_v2,
                    "validate_asset",
                    return_value={"sha256": digest, "probe": {"codec": "mjpeg"}},
                ):
                    self.assertIsNone(
                        media_engine_v2._existing_asset_record(folder, 1, {"must_have": []})
                    )
            finally:
                media_engine_v2.BASE = old

    def test_legacy_manifest_is_not_resume_trusted(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            old = resume_short_runtime.BASE
            resume_short_runtime.BASE = base
            try:
                sid = "LEGACY_001"
                (base / "roteiros").mkdir(parents=True)
                (base / "manifests").mkdir(parents=True)
                (base / "roteiros" / f"pro_edit_plan_{sid}.json").write_text(
                    json.dumps({
                        "schema_version": "render-plan-v2",
                        "short_id": sid,
                        "scenes": [{"scene_id": "1"}],
                    }),
                    encoding="utf-8",
                )
                (base / "manifests" / f"media_{sid}.json").write_text(
                    json.dumps({
                        "schema_version": "media-manifest-v2",
                        "short_id": sid,
                        "immutable": True,
                        "scene_count": 1,
                        "scenes": [{
                            "scene_id": "1",
                            "scene_number": 1,
                            "asset": {"validated": True, "checksum_sha256": "x"},
                        }],
                    }),
                    encoding="utf-8",
                )
                with patch.object(resume_short_runtime, "expected_scenes", return_value=1):
                    self.assertFalse(resume_short_runtime.consolidation_plan_ok(sid))
            finally:
                resume_short_runtime.BASE = old

    def test_main_rejects_legacy_renderer_route(self):
        from pathlib import Path
        main_text = Path("main.py").read_text(encoding="utf-8")
        self.assertIn("RENDER_ENGINE_LEGACY_DISABLED", main_text)
        self.assertNotIn('p.run("9L - PROFESSIONAL MULTI-BEAT ASSEMBLER"', main_text)
        self.assertNotIn('p.run("10L - FINAL RENDER V6 PROFESSIONAL"', main_text)


if __name__ == "__main__":
    unittest.main()
