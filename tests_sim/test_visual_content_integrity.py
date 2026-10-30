import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import media_emergency_fallback as fallback
import render_preflight
import visual_qa
import visual_director


class VisualContentIntegrityTests(unittest.TestCase):
    def test_production_can_disable_neutral_editorial_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = fallback.create_editorial_reuse(
                root,
                1,
                allow_neutral=False,
            )
            self.assertIsNone(result)
            self.assertFalse((root / "scene_01.jpg").exists())

    def test_neutral_index_metadata_is_detectable_and_clearable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.mkdir(parents=True, exist_ok=True)
            (root / ".editorial_reuse_index.json").write_text(
                json.dumps({
                    "version": "2.1",
                    "scenes": {
                        "1": {
                            "source_scene": None,
                            "variant": 0,
                            "neutral_slate": True,
                        },
                        "2": {
                            "source_scene": 6,
                            "variant": 1,
                            "neutral_slate": False,
                        },
                    },
                }),
                encoding="utf-8",
            )
            self.assertEqual(fallback.neutral_slate_scene_numbers(root), {1})
            self.assertTrue(fallback.clear_editorial_scene(root, 1))
            self.assertEqual(fallback.neutral_slate_scene_numbers(root), set())
            self.assertIn(2, fallback.editorial_scene_numbers(root))

    def test_render_preflight_rejects_neutral_placeholder_even_when_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sid = "blank"
            for name in ("roteiros", "audios", "imagens", "videos", "temp"):
                (base / name).mkdir(parents=True, exist_ok=True)
            media = base / "imagens" / f"short_{sid}"
            media.mkdir(parents=True)
            scenes = [{"scene": i, "segment": f"cena {i}"} for i in range(1, 7)]
            (base / "roteiros" / f"scene_map_{sid}.json").write_text(
                json.dumps({"scenes": scenes}), encoding="utf-8"
            )
            (base / "roteiros" / f"pro_edit_plan_{sid}.json").write_text(
                json.dumps({"version": "PRO_EDIT_TEST", "scenes": scenes}),
                encoding="utf-8",
            )
            for i in range(1, 7):
                (media / f"scene_{i:02d}.jpg").write_bytes(b"x" * 2048)
            (media / ".editorial_reuse_index.json").write_text(
                json.dumps({
                    "version": "2.1",
                    "scenes": {
                        "1": {
                            "source_scene": None,
                            "variant": 0,
                            "neutral_slate": True,
                        }
                    },
                }),
                encoding="utf-8",
            )
            (base / "audios" / f"short_{sid}.mp3").write_bytes(b"a" * 6000)
            (base / "videos" / f"short_{sid}.ass").write_text(
                "[Events]\n"
                "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                "Dialogue: 0,0:00:00.00,0:00:12.00,Default,,0,0,0,,Texto\n",
                encoding="utf-8",
            )
            fake_usage = mock.Mock()
            fake_usage.free = 3 * 1024**3
            with (
                mock.patch.object(render_preflight, "BASE", base),
                mock.patch.object(render_preflight, "_probe_media", return_value=None),
                mock.patch.object(render_preflight, "_duration", return_value=12.0),
                mock.patch.object(render_preflight.shutil, "which", return_value="/usr/bin/fake"),
                mock.patch.object(render_preflight.shutil, "disk_usage", return_value=fake_usage),
                mock.patch.dict(os.environ, {"SHORT_QTD_CENAS": "6"}, clear=False),
            ):
                report = render_preflight.inspect(sid)
            self.assertEqual(report["status"], "FAILED", report)
            self.assertEqual(report["neutral_editorial_scenes"], [1])
            self.assertFalse(report["checks"]["assets"])
            self.assertFalse(report["checks"]["neutral_editorial_absent"])

    def test_blank_pixel_classifier_blocks_true_empty_frame(self):
        black = bytes([0] * (24 * 24 * 3))
        stats = visual_qa._frame_content_stats(black)
        self.assertTrue(stats["blank"])
        self.assertLessEqual(stats["mean"], 1.0)

    def test_map_context_queries_require_readable_high_contrast_cartography(self):
        original = {
            "scene": 4,
            "segment": "na antiga União Soviética",
            "query": "soviet union archival map",
            "visual_mode": "map_context",
            "must_have": ["landscape"],
        }
        enriched, _ = visual_director.safe_scene(
            original,
            {"query": "soviet union vintage archival map landscape"},
        )
        query = enriched["query"].casefold()
        for term in ("high", "contrast", "map", "light", "background", "clear", "readable", "labels"):
            self.assertIn(term, query)

    def test_dark_but_textured_pixels_are_not_blank(self):
        values = []
        for i in range(24 * 24):
            value = 4 if i % 2 == 0 else 45
            values.extend([value, value, value])
        stats = visual_qa._frame_content_stats(bytes(values))
        self.assertFalse(stats["blank"])
        self.assertGreater(stats["stddev"], 7.0)

    def test_rendered_content_detects_blank_opening_separately_from_later_scenes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            runtime = base / "runtime.json"
            runtime.write_text(
                json.dumps({"durations": [2.0] * 6}),
                encoding="utf-8",
            )
            video = base / "video.mp4"
            video.write_bytes(b"x")
            black = bytes([0] * (24 * 24 * 3))
            visible = bytes([90] * (24 * 24 * 3))
            samples = [black] + [visible] * 6
            with (
                mock.patch.object(visual_qa, "RUNTIME", runtime),
                mock.patch.object(visual_qa, "_frame_sample", side_effect=samples),
                mock.patch.dict(os.environ, {"SHORT_QTD_CENAS": "6"}, clear=False),
            ):
                result = visual_qa.analyze_rendered_content(video)
            self.assertTrue(result["available"])
            self.assertTrue(result["opening_blank"])
            self.assertEqual(result["blank_scenes"], [])

    def test_media_and_release_contracts_are_fail_closed(self):
        media_text = Path("media_master_gate.py").read_text(encoding="utf-8")
        release_text = Path("release_gate.py").read_text(encoding="utf-8")
        stage_text = Path("media_stage_runtime.py").read_text(encoding="utf-8")
        midia_text = Path("midia.py").read_text(encoding="utf-8")

        self.assertIn("neutral_editorial_scene_", media_text)
        self.assertIn("editorial_reuse_excess=", media_text)
        self.assertIn("visual_qa_missing", release_text)
        self.assertIn("media_quality_report_missing", release_text)
        self.assertIn("rendered_visual_content_not_verified", release_text)
        self.assertIn("allow_neutral=False", stage_text)
        self.assertIn('SAP_MEDIA_INROUND_EDITORIAL", "0"', midia_text)
        self.assertIn("QUALITY_PARTIAL_RESTORE", midia_text)

    def test_local_fallback_commit_is_not_unconditional_or_duplicated(self):
        text = Path("midia.py").read_text(encoding="utf-8")
        start = text.index("# FALLBACK LOCAL FINAL")
        end = text.index("# EMERGENCY EDITORIAL COMPLETION", start)
        block = text[start:end]
        self.assertEqual(block.count("_vse42_commit_safe(escolhido)"), 1)
        self.assertIn("destino_local", block)
        self.assertIn("sucesso = True", block)


if __name__ == "__main__":
    unittest.main()
