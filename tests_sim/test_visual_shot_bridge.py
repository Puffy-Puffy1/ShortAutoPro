import unittest
from unittest import mock

import visual_shot_bridge as bridge


class VisualShotBridgeTests(unittest.TestCase):
    def setUp(self):
        self.original_expected = bridge.EXPECTED
        bridge.EXPECTED = 6

    def tearDown(self):
        bridge.EXPECTED = self.original_expected

    def scene_map(self):
        return {
            "scenes": [
                {
                    "scene": i,
                    "segment": f"segment {i}",
                    "visual_mode": "environment" if i < 5 else "human_context",
                }
                for i in range(1, 7)
            ]
        }

    def test_persists_director_shot_suggestions(self):
        report = {
            "scenes": [
                {"scene": 1, "shot_type": "wide shot"},
                {"scene": 2, "shot_type": "wide shot"},
                {"scene": 3, "shot_type": "close up"},
                {"scene": 4, "shot_type": "detail"},
                {"scene": 5, "shot_type": "portrait"},
                {"scene": 6, "shot_type": "portrait"},
            ]
        }
        updated, changes = bridge.apply_shot_bridge(self.scene_map(), report)
        shots = [x["shot_type"] for x in updated["scenes"]]
        self.assertEqual(shots[0], "wide")
        self.assertEqual(shots[1], "medium")
        self.assertEqual(shots[2], "closeup")
        self.assertEqual(shots[-2:], ["portrait", "portrait"])
        self.assertEqual(len(changes), 6)
        self.assertTrue(updated["visual_shot_bridge"]["applied"])

    def test_missing_suggestions_use_deterministic_fallbacks(self):
        updated, _ = bridge.apply_shot_bridge(self.scene_map(), {"scenes": []})
        shots = [x["shot_type"] for x in updated["scenes"]]
        self.assertTrue(all(shots))
        self.assertGreaterEqual(len(set(shots)), 2)

    def test_does_not_rewrite_scene_content(self):
        scene_map = self.scene_map()
        before = [dict(x) for x in scene_map["scenes"]]
        updated, _ = bridge.apply_shot_bridge(scene_map, {"scenes": []})
        for old, new in zip(before, updated["scenes"]):
            self.assertEqual(old["segment"], new["segment"])
            self.assertEqual(old["visual_mode"], new["visual_mode"])


if __name__ == "__main__":
    unittest.main()
