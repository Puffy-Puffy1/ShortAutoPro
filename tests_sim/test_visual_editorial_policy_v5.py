import unittest

from visual_editorial_policy import (
    apply_editorial_policy,
    editorial_pan,
    zoom_amplitude,
)


class VisualEditorialPolicyV5Tests(unittest.TestCase):
    def test_human_portrait_stays_centered(self):
        scene = {
            "visual_mode": "human_context",
            "shot_type": "portrait",
            "media_type": "photo",
            "pan": "left",
            "narrative_role": "context",
        }
        result = apply_editorial_policy(scene, 3, 12, previous_pan="right")
        self.assertEqual(result["editorial_policy"], "humanized_v5")
        self.assertEqual(result["pan"], "center")
        self.assertLessEqual(result["editorial_amplitude"], 0.018)

    def test_document_and_detail_frames_do_not_slide(self):
        self.assertEqual(
            editorial_pan(5, 12, "document", "detail", "right", "left", "evidence"),
            "center",
        )
        self.assertEqual(
            editorial_pan(6, 12, "object", "closeup", "left", "right", "reveal"),
            "center",
        )

    def test_medium_generic_context_prefers_stable_center(self):
        self.assertEqual(
            editorial_pan(5, 12, "environment", "medium", "left", "right", "context"),
            "center",
        )

    def test_wide_establishing_shot_can_drift(self):
        pan = editorial_pan(2, 12, "environment", "wide", "none", None, "context")
        self.assertIn(pan, {"left", "right"})

    def test_direction_changes_when_previous_wide_pan_matches(self):
        pan = editorial_pan(3, 12, "environment", "wide", "right", "right", "context")
        self.assertEqual(pan, "left")

    def test_zoom_amplitudes_remain_restrained(self):
        self.assertLessEqual(zoom_amplitude(4, "environment", "wide"), 0.027)
        self.assertLessEqual(zoom_amplitude(4, "human_context", "portrait"), 0.018)
        self.assertLessEqual(zoom_amplitude(4, "document", "detail", "evidence"), 0.016)

    def test_native_video_gets_no_artificial_motion(self):
        scene = {
            "visual_mode": "environment",
            "shot_type": "wide",
            "media_type": "video",
            "pan": "right",
        }
        result = apply_editorial_policy(scene, 2, 12, previous_pan="left")
        self.assertEqual(result["visual_energy"], 0)
        self.assertEqual(result["pan"], "none")
        self.assertEqual(result["editorial_amplitude"], 0.0)


if __name__ == "__main__":
    unittest.main()
