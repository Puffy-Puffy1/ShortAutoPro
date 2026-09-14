import unittest

from visual_editorial_policy import apply_editorial_policy, editorial_energy


class VisualEditorialPolicyTests(unittest.TestCase):
    def test_hook_is_strong_but_bounded(self):
        scene = {
            "visual_mode": "environment",
            "shot_type": "medium",
            "media_type": "photo",
            "pan": "center",
        }
        out = apply_editorial_policy(scene, 1, 12)
        self.assertEqual(out["energy"], 5)
        self.assertEqual(out["rhythm_profile"], "hook_editorial")
        self.assertLessEqual(out["editorial_amplitude"], 0.084)

    def test_document_detail_is_calm_and_centered(self):
        scene = {
            "visual_mode": "evidence",
            "shot_type": "detail",
            "media_type": "photo",
            "pan": "right",
        }
        out = apply_editorial_policy(scene, 5, 12, previous_pan="left")
        self.assertEqual(out["pan"], "center")
        self.assertEqual(out["rhythm_profile"], "documentary_hold")
        self.assertLessEqual(out["energy"], 3)

    def test_direction_changes_when_previous_pan_matches(self):
        scene = {
            "visual_mode": "environment",
            "shot_type": "medium",
            "media_type": "photo",
            "pan": "left",
        }
        out = apply_editorial_policy(scene, 3, 12, previous_pan="left")
        self.assertEqual(out["pan"], "right")

    def test_final_scene_uses_closing_hold(self):
        scene = {
            "visual_mode": "human_context",
            "shot_type": "medium",
            "media_type": "photo",
            "pan": "right",
        }
        out = apply_editorial_policy(scene, 12, 12, previous_pan="left")
        self.assertEqual(out["energy"], 2)
        self.assertEqual(out["pan"], "center")
        self.assertEqual(out["rhythm_profile"], "closing_hold")

    def test_native_video_is_not_artificially_animated(self):
        scene = {
            "visual_mode": "transport",
            "shot_type": "wide",
            "media_type": "video",
            "pan": "left",
        }
        out = apply_editorial_policy(scene, 4, 12)
        self.assertEqual(out["energy"], 0)
        self.assertEqual(out["visual_energy"], 0)
        self.assertEqual(out["pan"], "none")
        self.assertEqual(out["rhythm_profile"], "native_video")

    def test_editorial_energy_varies_across_story_arc(self):
        values = [
            editorial_energy(i, 12, "environment", "medium", "photo")
            for i in range(1, 13)
        ]
        self.assertGreaterEqual(len(set(values)), 3)
        self.assertEqual(values[0], 5)
        self.assertEqual(values[-1], 2)


if __name__ == "__main__":
    unittest.main()
