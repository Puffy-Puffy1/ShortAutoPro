import unittest

import visual_risk_guard


class VisualRiskGuardTests(unittest.TestCase):
    def test_alien_does_not_match_inside_australian(self):
        self.assertFalse(visual_risk_guard.contem_termo("Australian pilot archive", "alien"))
        result, changes = visual_risk_guard.processar_mapa({
            "scenes": [{
                "scene": 1,
                "segment": "An Australian pilot disappeared.",
                "query": "Australian pilot archival photograph",
                "must_have": ["Australian pilot"],
                "avoid": [],
            }]
        })
        scene = result["scenes"][0]
        self.assertEqual(scene["query"], "Australian pilot archival photograph")
        self.assertEqual(scene["must_have"], ["australian pilot"])
        self.assertEqual(changes, [])

    def test_real_alien_term_is_contextualized(self):
        result, changes = visual_risk_guard.processar_mapa({
            "scenes": [{
                "scene": 2,
                "segment": "A witness reported an unknown object.",
                "query": "alien spacecraft above forest",
                "must_have": ["alien spacecraft"],
                "avoid": [],
            }]
        })
        scene = result["scenes"][0]
        self.assertNotIn("alien spacecraft", scene["query"].lower())
        self.assertTrue(changes)
        self.assertIn("detailed alien spacecraft", scene["avoid"])

    def test_possible_does_not_match_inside_impossible(self):
        self.assertFalse(visual_risk_guard.tem_contexto_incerto("An impossible route was reconstructed."))
        self.assertTrue(visual_risk_guard.tem_contexto_incerto("A possible route was reconstructed."))

    def test_duplicate_avoid_terms_are_normalized_once(self):
        result, _ = visual_risk_guard.processar_mapa({
            "scenes": [{
                "scene": 3,
                "segment": "Witnesses reported a mysterious light.",
                "query": "night sky",
                "must_have": [],
                "avoid": ["Flying Saucer", "flying saucer"],
            }]
        })
        avoid = result["scenes"][0]["avoid"]
        self.assertEqual(avoid.count("flying saucer"), 1)

    def test_invalid_scene_structure_fails_explicitly(self):
        with self.assertRaises(ValueError):
            visual_risk_guard.processar_mapa({"scenes": ["invalid"]})


if __name__ == "__main__":
    unittest.main()
