import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import visual_qa


class RenderedVisualDiversityTests(unittest.TestCase):
    def test_provider_provenance_falls_back_to_provider_suffixed_filename(self):
        self.assertEqual(
            visual_qa._provider_from_asset(
                Path("scene_01_wikimedia.jpg"), {}
            ),
            "Wikimedia",
        )
        self.assertEqual(
            visual_qa._provider_from_asset(
                Path("scene_02_pexels.png"), {}
            ),
            "Pexels",
        )
        self.assertEqual(
            visual_qa._provider_from_asset(
                Path("scene_03.jpg"), {}
            ),
            "",
        )
        self.assertEqual(
            visual_qa._provider_from_asset(
                Path("scene_04.jpg"), {"provider": "Pixabay"}
            ),
            "Pixabay",
        )

    def test_frame_mad_distinguishes_large_visual_change(self):
        black = bytes([0] * (24 * 24 * 3))
        white = bytes([255] * (24 * 24 * 3))
        self.assertEqual(visual_qa._frame_mad(black, black), 0.0)
        self.assertGreater(visual_qa._frame_mad(black, white), 0.95)

    def test_three_visual_clusters_across_twelve_scenes_is_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            runtime = base / "runtime.json"
            runtime.write_text(json.dumps({"durations": [3.0] * 12}), encoding="utf-8")
            video = base / "video.mp4"
            video.write_bytes(b"x")
            frames = []
            for value in ([20] * 4 + [120] * 4 + [230] * 4):
                frames.append(bytes([value] * (24 * 24 * 3)))
            with mock.patch.object(visual_qa, "RUNTIME", runtime), \
                 mock.patch.object(visual_qa, "_frame_sample", side_effect=frames):
                result = visual_qa.analyze_scene_diversity(video)
            self.assertTrue(result["available"])
            self.assertEqual(result["unique_visual_clusters"], 3)
            self.assertEqual(result["status"], "REVIEW")
            self.assertLess(result["change_ratio"], 0.55)

    def test_scene_durations_fall_back_to_frozen_render_timeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            runtime = base / "missing-runtime.json"
            timeline = base / "render_jobs" / "test_short" / "render_001" / "timeline.json"
            timeline.parent.mkdir(parents=True)
            timeline.write_text(
                json.dumps({"scenes": [{"duration": 2.5} for _ in range(12)]}),
                encoding="utf-8",
            )
            with mock.patch.object(visual_qa, "BASE", base), \
                 mock.patch.object(visual_qa, "SID", "test_short"), \
                 mock.patch.object(visual_qa, "RUNTIME", runtime):
                durations = visual_qa.scene_durations(12)
            self.assertEqual(durations, [2.5] * 12)

    def test_distinct_scene_samples_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            runtime = base / "runtime.json"
            runtime.write_text(json.dumps({"durations": [3.0] * 12}), encoding="utf-8")
            video = base / "video.mp4"
            video.write_bytes(b"x")
            frames = [bytes([min(255, i * 20)] * (24 * 24 * 3)) for i in range(12)]
            with mock.patch.object(visual_qa, "RUNTIME", runtime), \
                 mock.patch.object(visual_qa, "_frame_sample", side_effect=frames):
                result = visual_qa.analyze_scene_diversity(video)
            self.assertTrue(result["available"])
            self.assertGreaterEqual(result["unique_visual_clusters"], 7)
            self.assertEqual(result["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
