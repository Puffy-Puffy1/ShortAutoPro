import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from longform_runtime import make_ass, probe_video, render_generated_chapter, verify_generated_manifest


def _canonical(payload):
    value = dict(payload)
    value.pop("integrity_sha256", None)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class GeneratedManifestIntegrationTests(unittest.TestCase):
    def _write_manifest(self, root):
        project = root / "project_01"
        project.mkdir()
        clips = []
        for index in range(1, 3):
            media = project / f"clip_{index:04d}.mp4"
            media.write_bytes(f"validated video fixture {index}".encode())
            clips.append({
                "clip_index": index,
                "start_seconds": (index - 1) * 30,
                "duration_seconds": 30,
                "path": str(media),
                "sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
                "size_bytes": media.stat().st_size,
                "ffprobe": {
                    "status": "GENERATED_AND_PROBED", "video_codec": "h264",
                    "width": 1920, "height": 1080, "duration_seconds": 30,
                },
            })
        payload = {
            "schema_version": "shortautopro-generated-clips-v1",
            "project_id": "project_01",
            "clip_count": len(clips),
            "project": {
                "kind": "longform", "aspect_ratio": "16:9",
                "target_duration_seconds": 60, "clip_seconds": 30,
                "width": 1920, "height": 1080,
            },
            "clips": clips,
        }
        payload["integrity_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
        manifest = project / "generated_manifest.json"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        return manifest, Path(clips[0]["path"]), payload

    def test_accepts_valid_manifest_and_clip_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, _, payload = self._write_manifest(Path(tmp))
            result = verify_generated_manifest(manifest)
            self.assertEqual(result["project_id"], payload["project_id"])
            self.assertEqual(len(result["clips"]), 2)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/FFprobe required")
    def test_generated_clips_render_to_real_h264_aac_chapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project_01"
            project.mkdir()
            clips = []
            for index, color in enumerate(("red", "blue"), start=1):
                media = project / f"clip_{index:04d}.mp4"
                subprocess.run([
                    "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", f"color=c={color}:s=640x360:r=24:d=2",
                    "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(media),
                ], check=True, timeout=60)
                clips.append({
                    "clip_index": index, "start_seconds": (index - 1) * 2,
                    "duration_seconds": 2, "path": str(media),
                })
            audio = root / "speech.wav"
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                "-i", "sine=frequency=440:duration=4", "-c:a", "pcm_s16le", str(audio),
            ], check=True, timeout=60)
            ass = root / "captions.ass"
            make_ass(ass, "Generated clips integration test", 4)
            rendered = render_generated_chapter(
                root / "chapter_01", {"clips": clips}, 0, 4, audio, 4, ass,
            )
            probe = probe_video(rendered)
            self.assertEqual(probe["width"], 1920)
            self.assertEqual(probe["height"], 1080)
            self.assertEqual(probe["video_codec"], "h264")
            self.assertEqual(probe["audio_codec"], "aac")
            self.assertGreaterEqual(probe["duration"], 3.8)

    def test_rejects_incomplete_declared_timeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, _, payload = self._write_manifest(Path(tmp))
            payload["project"]["target_duration_seconds"] = 70
            payload["integrity_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "quantidade"):
                verify_generated_manifest(manifest)

    def test_rejects_ffprobe_resolution_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, _, payload = self._write_manifest(Path(tmp))
            payload["clips"][0]["ffprobe"]["width"] = 1280
            payload["integrity_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "resolução"):
                verify_generated_manifest(manifest)

    def test_rejects_manifest_integrity_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, _, payload = self._write_manifest(Path(tmp))
            payload["clips"][0]["prompt"] = "tampered"
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "integridade"):
                verify_generated_manifest(manifest)

    def test_rejects_clip_checksum_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, media, payload = self._write_manifest(Path(tmp))
            media.write_bytes(b"X" * media.stat().st_size)
            payload["integrity_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum"):
                verify_generated_manifest(manifest)

    def test_rejects_clip_path_outside_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, media, payload = self._write_manifest(Path(tmp))
            outside = Path(tmp) / "outside.mp4"
            outside.write_bytes(media.read_bytes())
            payload["clips"][0]["path"] = str(outside)
            payload["clips"][0]["sha256"] = hashlib.sha256(outside.read_bytes()).hexdigest()
            payload["integrity_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fora do workspace"):
                verify_generated_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
