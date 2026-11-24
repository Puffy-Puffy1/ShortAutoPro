import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import media_engine_v2


def _canonical(payload):
    value = dict(payload)
    value.pop("integrity_sha256", None)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


class GeneratedShortsManifestTests(unittest.TestCase):
    def _manifest(self, root):
        project = root / "shorts_project"
        project.mkdir()
        clips = []
        for index in range(1, 3):
            path = project / f"clip_{index:04d}.mp4"
            path.write_bytes(f"generated clip {index}".encode())
            clips.append({
                "clip_index": index,
                "start_seconds": (index - 1) * 10,
                "duration_seconds": 10,
                "prompt": f"Vertical documentary scene {index}",
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size_bytes": path.stat().st_size,
                "ffprobe": {
                    "status": "GENERATED_AND_PROBED",
                    "width": 720,
                    "height": 1280,
                    "duration_seconds": 10,
                    "video_codec": "h264",
                    "generation_host": "termux_local",
                    "model": "fixture-model",
                },
            })
        payload = {
            "schema_version": "shortautopro-generated-clips-v1",
            "project_id": "shorts_project",
            "project": {
                "kind": "shorts",
                "target_duration_seconds": 20,
                "aspect_ratio": "9:16",
                "width": 720,
                "height": 1280,
                "clip_seconds": 10,
            },
            "clip_count": 2,
            "clips": clips,
        }
        payload["integrity_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
        manifest = project / "generated_manifest.json"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        return manifest, payload

    def test_loads_complete_portrait_shorts_schedule(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, payload = self._manifest(Path(tmp))
            result = media_engine_v2._load_generated_shorts_manifest(manifest, 2)
            self.assertEqual(result["integrity_sha256"], payload["integrity_sha256"])
            self.assertEqual(len(result["clips"]), 2)

    def test_rejects_wrong_project_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, payload = self._manifest(Path(tmp))
            payload["project"]["kind"] = "longform"
            payload["integrity_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "expected_shorts"):
                media_engine_v2._load_generated_shorts_manifest(manifest, 2)

    def test_rejects_landscape_dimensions_for_shorts(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, payload = self._manifest(Path(tmp))
            payload["project"]["width"] = 1280
            payload["project"]["height"] = 720
            payload["integrity_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "DIMENSIONS_INVALID"):
                media_engine_v2._load_generated_shorts_manifest(manifest, 2)

    def test_rejects_scene_count_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, _ = self._manifest(Path(tmp))
            with self.assertRaisesRegex(RuntimeError, "SCENE_COUNT_MISMATCH"):
                media_engine_v2._load_generated_shorts_manifest(manifest, 3)

    def test_rejects_incomplete_timeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, payload = self._manifest(Path(tmp))
            payload["clips"][1]["start_seconds"] = 11
            payload["integrity_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "TIMELINE_INVALID"):
                media_engine_v2._load_generated_shorts_manifest(manifest, 2)

    def test_generated_scene_is_copied_and_pixel_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path, payload = self._manifest(root)
            payload["_manifest_path"] = str(manifest_path)
            media_dir = root / "media" / "short_demo"
            media_dir.mkdir(parents=True)
            scene = {
                "query": "documentary scene",
                "segment": "A documentary scene in a forest",
                "must_have": ["forest"],
                "avoid": ["cartoon"],
            }
            clip = payload["clips"][0]
            expected_sha = clip["sha256"]
            with patch.object(media_engine_v2, "validate_asset", return_value={
                "sha256": expected_sha,
                "probe": {"width": 720, "height": 1280, "duration": 10},
            }), patch.object(media_engine_v2, "_verify_scene_pixels", return_value={
                "status": "PASS", "method": "gemini_video_frame", "hits": 1,
            }) as visual:
                record = media_engine_v2.acquire_generated_scene(
                    "demo", 1, scene, media_dir, clip, payload, set(),
                )
            self.assertTrue((media_dir / "scene_01.mp4").is_file())
            self.assertEqual(record["asset_type"], "video")
            self.assertEqual(record["checksum_sha256"], expected_sha)
            self.assertEqual(record["verification_mode"], "gemini_visual_must")
            self.assertEqual(record["generated_clip_index"], 1)
            visual.assert_called_once()

    def test_build_manifest_uses_generated_clips_without_provider_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path, _ = self._manifest(root)
            scenes = [
                {"scene_id": "scene-1", "query": "forest documentary", "segment": "A forest", "must_have": ["forest"], "avoid": []},
                {"scene_id": "scene-2", "query": "river documentary", "segment": "A river", "must_have": ["river"], "avoid": []},
            ]
            probe = {"width": 720, "height": 1280, "duration": 10}
            def validate(path):
                return {"sha256": media_engine_v2.sha256(Path(path)), "probe": probe}
            with patch.object(media_engine_v2, "BASE", root), \
                 patch.object(media_engine_v2, "load_scene_map", return_value=scenes), \
                 patch.object(media_engine_v2, "validate_asset", side_effect=validate), \
                 patch.object(media_engine_v2, "_verify_scene_pixels", return_value={"status": "PASS", "method": "fixture"}), \
                 patch.object(media_engine_v2, "acquire_scene") as provider, \
                 patch.dict("os.environ", {"SAP_GENERATED_CLIPS_MANIFEST": str(manifest_path)}):
                result = media_engine_v2.build_manifest("demo")
            provider.assert_not_called()
            self.assertEqual(result["schema_version"], "media-manifest-v2")
            self.assertEqual(result["scene_count"], 2)
            self.assertTrue(all(row["asset"]["asset_type"] == "video" for row in result["scenes"]))
            self.assertTrue(all(row["asset"]["generated_manifest_sha256"] for row in result["scenes"]))
            self.assertEqual(
                result["integrity_sha256"],
                media_engine_v2._manifest_integrity(result),
            )

    def test_generated_asset_cache_is_not_reused_without_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media_dir = root / "short_demo"
            media_dir.mkdir()
            media = media_dir / "scene_01.mp4"
            media.write_bytes(b"video bytes")
            sidecar = media_dir / "scene_01.json"
            sidecar.write_text(json.dumps({
                "generated_manifest_sha256": "abc",
                "query_relevance": {"ok": True},
                "checksum_sha256": media_engine_v2.sha256(media),
            }), encoding="utf-8")
            self.assertIsNone(media_engine_v2._existing_asset_record(
                media_dir, 1, {"must_have": []},
            ))


if __name__ == "__main__":
    unittest.main()
