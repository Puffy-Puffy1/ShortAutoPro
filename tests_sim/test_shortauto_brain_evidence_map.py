import unittest

from shortauto_brain import build_evidence_map, fact_layer


SOURCE = (
    "O piloto relatou um OVNI perseguindo seu avião antes de desaparecer no ar."
)


class ShortAutoBrainEvidenceMapTests(unittest.TestCase):
    def test_visual_query_cannot_dilute_supported_narration(self):
        narration = "O piloto relatou um OVNI perseguindo seu avião"
        scene = {
            "segment": narration,
            "query": (
                "pilot reporting mysterious unidentified light chasing airplane "
                "in dark night sky with dramatic clouds, flight instruments, "
                "cockpit radar screens, military helicopters, coast guard vessels, "
                "waves, ocean, mountainous landscape, historical archival footage, "
                "black white film grain, cinematic documentary, low visibility, "
                "storm weather, long exposure and aerial perspective"
            ),
            "visual_query": "alien spacecraft, glowing objects, stars and nebula",
            "description": "Dramatic night aviation mystery illustration",
        }

        result = build_evidence_map([scene], fact_layer(SOURCE))

        self.assertEqual(result["coverage"], 100.0)
        self.assertEqual(result["unsupported_scenes"], [])
        self.assertEqual(result["scenes"][0]["scene_text"], narration)
        self.assertEqual(result["scenes"][0]["evidence_basis"], "narration_only")
        self.assertGreaterEqual(result["scenes"][0]["support_overlap"], 0.18)

    def test_visual_query_cannot_rescue_unsupported_narration(self):
        scene = {
            "segment": "A noite estava fria e silenciosa.",
            "query": SOURCE,
            "description": SOURCE,
        }

        result = build_evidence_map([scene], fact_layer(SOURCE))

        self.assertEqual(result["coverage"], 0.0)
        self.assertEqual(result["unsupported_scenes"], [1])
        self.assertEqual(
            result["scenes"][0]["scene_text"],
            "A noite estava fria e silenciosa.",
        )
        self.assertEqual(result["scenes"][0]["evidence_basis"], "narration_only")

    def test_existing_evidence_overlap_threshold_is_not_lowered(self):
        scene = {"segment": "Uma história misteriosa continua sem explicação."}

        result = build_evidence_map([scene], fact_layer(SOURCE))

        self.assertEqual(result["coverage"], 0.0)
        self.assertLess(result["scenes"][0]["support_overlap"], 0.18)


if __name__ == "__main__":
    unittest.main()
