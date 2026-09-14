import unittest

from visual_editorial_policy import apply_editorial_policy, editorial_energy, zoom_amplitude


class VisualEditorialPolicyTests(unittest.TestCase):
    def test_hook_is_strong_but_restrained(self):
        scene = {
            "visual_mode": "environment",
            "shot_type": "medium",
            "media_type": "photo",
            "pan": "center",
            "narrative_role": "hook",
        }
        out = apply_editorial_policy(scene, 1, 12)
        self.assertEqual(out["energy"], 4)
        self.assertEqual(out["rhythm_profile"], "hook_editorial")
        self.assertEqual(out["editorial_policy"], "humanized_v5")
        self.assertLessEqual(out["editorial_amplitude"], 0.026)
        self.assertEqual(out["pan"], "center")

    def test_document_detail_is_calm_and_centered(self):
        scene = {
            "visual_mode": "evidence",
            "shot_type": "detail",
            "media_type": "photo",
            "pan": "right",
            "narrative_role": "evidence",
        }
        out = apply_editorial_policy(scene, 5, 12, previous_pan="left")
        self.assertEqual(out["pan"], "center")
        self.assertEqual(out["rhythm_profile"], "documentary_hold")
        self.assertLessEqual(out["energy"], 2)
        self.assertLessEqual(out["editorial_amplitude"], 0.006)

    def test_regular_medium_photo_uses_stable_center_hold(self):
        scene = {
            "visual_mode": "environment",
            "shot_type": "medium",
            "media_type": "photo",
            "pan": "left",
        }
        out = apply_editorial_policy(scene, 3, 12, previous_pan="left")
        self.assertEqual(out["pan"], "center")

    def test_breath_scene_is_centered_and_low_energy(self):
        scene = {
            "visual_mode": "environment",
            "shot_type": "medium",
            "media_type": "photo",
            "pan": "right",
            "narrative_role": "context",
        }
        out = apply_editorial_policy(scene, 4, 12, previous_pan="left")
        self.assertEqual(out["pan"], "center")
        self.assertLessEqual(out["energy"], 2)
        self.assertEqual(out["rhythm_profile"], "editorial_breath")

    def test_wide_direction_changes_when_previous_pan_matches(self):
        scene = {
            "visual_mode": "environment",
            "shot_type": "wide",
            "media_type": "photo",
            "pan": "left",
        }
        out = apply_editorial_policy(scene, 5, 12, previous_pan="left")
        self.assertEqual(out["pan"], "right")

    def test_reveal_role_receives_emphasis_without_extreme_zoom(self):
        scene = {
            "visual_mode": "environment",
            "shot_type": "medium",
            "media_type": "photo",
            "pan": "center",
            "narrative_role": "reveal",
        }
        out = apply_editorial_policy(scene, 8, 12)
        self.assertGreaterEqual(out["energy"], 4)
        self.assertEqual(out["rhythm_profile"], "reveal_emphasis")
        self.assertLessEqual(out["editorial_amplitude"], 0.026)
        self.assertEqual(out["pan"], "center")

    def test_human_context_is_stable_and_centered(self):
        scene = {
            "visual_mode": "human_context",
            "shot_type": "medium",
            "media_type": "photo",
            "pan": "left",
        }
        out = apply_editorial_policy(scene, 6, 12)
        self.assertEqual(out["pan"], "center")
        self.assertEqual(out["rhythm_profile"], "portrait_hold")
        self.assertLessEqual(out["energy"], 3)
        self.assertLessEqual(out["editorial_amplitude"], 0.012)

    def test_final_scene_uses_quiet_closing_hold(self):
        scene = {
            "visual_mode": "evidence",
            "shot_type": "medium",
            "media_type": "photo",
            "pan": "right",
            "narrative_role": "payoff",
        }
        out = apply_editorial_policy(scene, 12, 12, previous_pan="left")
        self.assertEqual(out["energy"], 1)
        self.assertEqual(out["pan"], "center")
        self.assertEqual(out["rhythm_profile"], "closing_hold")
        self.assertLessEqual(out["editorial_amplitude"], 0.003)

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
        self.assertEqual(out["editorial_amplitude"], 0.0)

    def test_editorial_energy_varies_across_story_arc(self):
        values = [
            editorial_energy(i, 12, "environment", "medium", "photo")
            for i in range(1, 13)
        ]
        self.assertGreaterEqual(len(set(values)), 3)
        self.assertEqual(values[0], 4)
        self.assertEqual(values[-1], 2)
        self.assertLessEqual(max(values), 4)

    def test_narrative_role_changes_energy(self):
        calm = editorial_energy(8, 12, "environment", "medium", "photo", "reflection")
        reveal = editorial_energy(8, 12, "environment", "medium", "photo", "reveal")
        self.assertLess(calm, reveal)

    def test_wide_shot_motion_stays_bounded(self):
        self.assertLessEqual(
            zoom_amplitude(4, "environment", "wide", "reveal"),
            0.027,
        )


if __name__ == "__main__":
    unittest.main()
