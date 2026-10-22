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

    def test_collapses_redundant_manuscript_descriptors_to_one_verifiable_object(self):
        anchors, events = normalize_visual_musts([
            "medieval manuscript",
            "aged parchment pages",
        ])
        self.assertEqual(anchors, ["manuscript"])
        self.assertEqual([event["to"] for event in events], ["manuscript", "manuscript"])
        self.assertTrue(all(event["reason"] == "NON_ATOMIC_VISUAL_QUALIFIER" for event in events))

    def test_book_and_parchment_anchors_collapse_only_in_manuscript_context(self):
        anchors, events = normalize_visual_musts(
            ["book", "parchment pages"],
            context="old illustrated manuscript open pages studio lighting",
        )
        self.assertEqual(anchors, ["manuscript"])
        self.assertEqual(
            [(event["from"], event["to"], event["reason"]) for event in events],
            [
                ("book", "manuscript", "CONTEXTUAL_MANUSCRIPT_ANCHOR"),
                ("parchment pages", "manuscript", "CONTEXTUAL_MANUSCRIPT_ANCHOR"),
            ],
        )

    def test_generic_book_requirements_remain_unchanged_without_manuscript_context(self):
        anchors, events = normalize_visual_musts(
            ["book", "parchment pages"],
            context="a person reading a book",
        )
        self.assertEqual(anchors, ["book", "parchment pages"])
        self.assertEqual(events, [])

    def test_ripped_tent_and_snow_anchors_normalize_only_with_visual_context(self):
        query = "vintage black and white photo of a torn tent in snowy mountains"
        anchors, events = normalize_visual_musts(
            ["ripped canvas", "snowy background"],
            context=query,
        )
        self.assertEqual(anchors, ["torn tent", "snow"])
        self.assertEqual(
            [(event["from"], event["to"], event["reason"]) for event in events],
            [
                ("ripped canvas", "torn tent", "CONTEXTUAL_TENT_ANCHOR"),
                ("snowy background", "snow", "CONTEXTUAL_SNOW_ANCHOR"),
            ],
        )

    def test_tent_and_snow_requirements_remain_unchanged_without_context(self):
        anchors, events = normalize_visual_musts(
            ["ripped canvas", "snowy background"],
            context="a building interior at night",
        )
        self.assertEqual(anchors, ["ripped canvas", "snowy background"])
        self.assertEqual(events, [])

    def test_water_collapses_to_ocean_only_when_query_names_ocean_or_sea(self):
        anchors, events = normalize_visual_musts(
            ["ocean", "water"],
            context="Bass Strait dark ocean aerial view at dusk",
        )
        self.assertEqual(anchors, ["ocean"])
        self.assertEqual(
            events,
            [{
                "from": "water",
                "to": "ocean",
                "reason": "CONTEXTUAL_OCEAN_ANCHOR",
            }],
        )

    def test_generic_water_requirement_remains_unchanged_outside_ocean_context(self):
        anchors, events = normalize_visual_musts(
            ["water"],
            context="indoor sink with running water",
        )
        self.assertEqual(anchors, ["water"])
        self.assertEqual(events, [])

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
