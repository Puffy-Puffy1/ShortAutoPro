import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

import media_acquisition_v3
import render_engine_v2
import render_plan_v2
from media_v3.providers import ProviderAdapter, ProviderRegistry, ProviderStatus


ROOT = Path(__file__).resolve().parents[1]


def fixture_png(seed: int) -> bytes:
    w = h = 64
    rows = []
    for y in range(h):
        rows.append(
            b"\x00"
            + b"".join(
                bytes(((x * 3 + seed) % 256, (y * 5 + seed) % 256, 160 + (seed % 80)))
                for x in range(w)
            )
        )
    raw = b"".join(rows)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


class FixtureProvider(ProviderAdapter):
    name = "fixture"

    def __init__(self, fixture_root: Path):
        self.root = Path(fixture_root)
        self.calls = 0

    def status(self):
        return ProviderStatus(True)

    def search(self, query, must=None, soft_must=None, avoid=None):
        self.calls += 1
        token = query.replace(" ", "_")[:24]
        return [{
            "provider": self.name,
            "kind": "image",
            "id": "asset-" + token,
            "url": "file://fixture",
            "local_path": str(self.root / "fixture.png"),
            "description": "deterministic fixture visual scene",
            "tags": "fixture visual",
        }]


def make_audio(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=0.7",
            "-c:a", "libmp3lame", "-b:a", "96k", str(path),
        ],
        check=True,
        timeout=60,
    )


def make_ass(path: Path, sid: str) -> None:
    path.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, TertiaryColour, "
        "BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, "
        "MarginV, AlphaLevel, Encoding\n"
        "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,1,2,0,2,30,30,60,0,1\n"
        "[Events]\n"
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
        f"Dialogue: 0,0:00:00.00,0:00:00.70,Default,,0,0,0,,V3 stress {sid}\n",
        encoding="utf-8",
    )


class MediaV3FullPipelineStressTests(unittest.TestCase):
    def _prepare_job(self, base: Path, sid: str, seed: int):
        for folder in ("roteiros", "audios", "videos", "manifests"):
            (base / folder).mkdir(parents=True, exist_ok=True)
        media = base / "imagens" / f"short_{sid}"
        media.mkdir(parents=True, exist_ok=True)
        scene = {
            "scene_id": "scene_01",
            "scene": 1,
            "segment": "fixture visual scene",
            "query": "fixture visual scene",
            "words": 2,
            "protected_zone": "center",
        }
        mutable_map = {"scenes": [scene]}
        (base / "roteiros" / f"scene_map_{sid}.json").write_text(
            json.dumps(mutable_map),
            encoding="utf-8",
        )
        # Test the real downstream contract: acquisition must consume a frozen SceneMap.
        frozen_map = {
            **mutable_map,
            "schema_version": "SCENE_MAP_FROZEN_1.0",
            "short_id": sid,
            "frozen_at": "2026-01-01T00:00:00+00:00",
            "source_path": str(base / "roteiros" / f"scene_map_{sid}.json"),
            "source_sha256": hashlib.sha256(
                json.dumps(mutable_map, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "mutable_upstream_closed": True,
        }
        (base / "manifests" / f"scene_map_{sid}.json").write_text(
            json.dumps(frozen_map),
            encoding="utf-8",
        )
        (base / "roteiros" / f"pro_edit_plan_{sid}.json").write_text(
            json.dumps({
                "schema_version": "render-plan-v2",
                "short_id": sid,
                "scenes": [{
                    "scene_id": "scene_01",
                    "scene": 1,
                    "pace_multiplier": 1.0,
                    "zoom_start": 1.0,
                    "zoom_end": 1.02,
                    "pan": "center",
                    "cut_style": "editorial_cut",
                    "transition_duration": 0,
                }],
            }),
            encoding="utf-8",
        )
        fixture = base / "fixtures" / f"{sid}.png"
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_bytes(fixture_png(seed))
        shutil.copy2(fixture, base / "fixtures" / "fixture.png")
        make_audio(base / "audios" / f"short_{sid}.mp3")
        make_ass(base / "videos" / f"short_{sid}.ass", sid)
        return fixture

    def _render(self, base: Path, sid: str):
        old_media_base = media_acquisition_v3.BASE
        old_render_base = render_engine_v2.BASE
        old_plan_base = render_plan_v2.BASE
        try:
            media_acquisition_v3.BASE = base
            render_engine_v2.BASE = base
            render_plan_v2.BASE = base
            provider = FixtureProvider(base / "fixtures")
            engine = media_acquisition_v3.MediaAcquisitionV3(
                base, ProviderRegistry([provider])
            )
            manifest = media_acquisition_v3.build_manifest(sid, engine)
            self.assertEqual(manifest["short_id"], sid)
            render_plan_v2.main(sid)
            with patch.dict(
                os.environ,
                {
                    "SHORTAUTOPRO_BASE": str(base),
                    "SAP_RENDER_V2_BACKEND": "ffmpeg",
                    "SAP_RENDER_V2_CRF": "28",
                    "HOME": str(base.parent),
                },
                clear=False,
            ), patch.object(
                render_engine_v2.sys,
                "argv",
                ["render_engine_v2.py", "--short-id", sid],
            ):
                self.assertEqual(render_engine_v2.main(), 0)
            final = base / "videos" / f"short_v6_{sid}.mp4"
            self.assertTrue(final.is_file())
            self.assertGreater(final.stat().st_size, 1000)
            report = json.loads(
                (base / "render_jobs" / sid / "render_001" / "render_report.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(report["short_id"], sid)
            self.assertEqual(report["quality_gate"], "PASS")
            return final
        finally:
            media_acquisition_v3.BASE = old_media_base
            render_engine_v2.BASE = old_render_base
            render_plan_v2.BASE = old_plan_base

    def test_1_2_5_10_consecutive_full_pipeline_jobs(self):
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            self.skipTest("ffmpeg/ffprobe unavailable")
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "ShortAutoPro"
            outputs = []
            ordinal = 0
            for count in (1, 2, 5, 10):
                for _ in range(count):
                    ordinal += 1
                    sid = f"V3FULL_{ordinal:02d}"
                    self._prepare_job(base, sid, ordinal)
                    outputs.append(self._render(base, sid))
            ids = [p.stem.replace("short_v6_", "") for p in outputs]
            self.assertEqual(len(ids), 18)
            self.assertEqual(len(set(ids)), 18)
            self.assertEqual(
                {p.parent.name for p in outputs},
                {f"videos"},
            )
            for sid in ids:
                manifest = json.loads(
                    (base / "manifests" / f"media_{sid}.json").read_text(encoding="utf-8")
                )
                state = json.loads(
                    (base / "render_jobs" / sid / "render_001" / "state.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(manifest["short_id"], sid)
                self.assertEqual(state["status"], "PASSED")

    def test_render_failure_does_not_corrupt_next_job(self):
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            self.skipTest("ffmpeg/ffprobe unavailable")
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "ShortAutoPro"
            self._prepare_job(base, "FAIL_RENDER_01", 1)
            self._prepare_job(base, "OK_RENDER_02", 2)
            media_acquisition_v3.BASE = base
            render_engine_v2.BASE = base
            render_plan_v2.BASE = base
            provider = FixtureProvider(base / "fixtures")
            engine = media_acquisition_v3.MediaAcquisitionV3(base, ProviderRegistry([provider]))
            media_acquisition_v3.build_manifest("FAIL_RENDER_01", engine)
            render_plan_v2.main("FAIL_RENDER_01")
            asset = next((base / "imagens" / "short_FAIL_RENDER_01").glob("scene_*.png"))
            asset.write_bytes(b"corrupt")
            with patch.dict(
                os.environ,
                {"SHORTAUTOPRO_BASE": str(base), "SAP_RENDER_V2_BACKEND": "ffmpeg"},
                clear=False,
            ), patch.object(
                render_engine_v2.sys,
                "argv",
                ["render_engine_v2.py", "--short-id", "FAIL_RENDER_01"],
            ):
                rc = render_engine_v2.main()
            self.assertNotEqual(rc, 0)
            self._render(base, "OK_RENDER_02")
            self.assertTrue((base / "videos" / "short_v6_OK_RENDER_02.mp4").is_file())


if __name__ == "__main__":
    unittest.main()
