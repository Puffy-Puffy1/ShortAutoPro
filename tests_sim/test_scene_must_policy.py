import unittest

from scene_must_policy import normalize_visual_musts


class SceneMustPolicyTests(unittest.TestCase):
    def test_removes_known_nonessential_qualifiers_from_visual_anchors(self):
        anchors, events = normalize_visual_musts([
            "single engine aircraft",
            "dark horizon",
            "police car",
        ])
        self.assertEqual(anchors, ["aircraft", "horizon", "police car"])
        self.assertEqual(
            events,
            [
                {
                    "from": "single engine aircraft",
                    "to": "aircraft",
                    "reason": "NON_ATOMIC_VISUAL_QUALIFIER",
                },
                {
                    "from": "dark horizon",
                    "to": "horizon",
                    "reason": "NON_ATOMIC_VISUAL_QUALIFIER",
                },
            ],
        )

    def test_deduplicates_after_normalization(self):
        anchors, events = normalize_visual_musts([
            "single engine aircraft",
            "aircraft",
            "single-engine aircraft",
        ])
        self.assertEqual(anchors, ["aircraft"])
        self.assertEqual(len(events), 2)

    def test_preserves_unknown_compound_entities_and_empty_values(self):
        anchors, events = normalize_visual_musts([
            "",
            "female pilots",
            "cargo ship",
            "unfamiliar compound phrase",
        ])
        self.assertEqual(
            anchors,
            ["female pilots", "cargo ship", "unfamiliar compound phrase"],
        )
        self.assertEqual(events, [])

    def test_accepts_single_string_input(self):
        anchors, events = normalize_visual_musts("dark horizon")
        self.assertEqual(anchors, ["horizon"])
        self.assertEqual(events[0]["from"], "dark horizon")


if __name__ == "__main__":
    unittest.main()
