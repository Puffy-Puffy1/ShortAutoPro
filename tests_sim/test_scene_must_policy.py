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

    def test_skeleton_normalizes_to_rib_cage_only_in_matching_visual_context(self):
        anchors, events = normalize_visual_musts(
            ["skeleton"],
            context="medical x ray showing human rib cage and skeletal structure",
        )
        self.assertEqual(anchors, ["rib cage"])
        self.assertEqual(
            events,
            [{
                "from": "skeleton",
                "to": "rib cage",
                "reason": "CONTEXTUAL_RIB_CAGE_ANCHOR",
            }],
        )

    def test_generic_skeleton_requirement_stays_unchanged_without_rib_cage_context(self):
        anchors, events = normalize_visual_musts(
            ["skeleton"],
            context="full human skeleton on a stand",
        )
        self.assertEqual(anchors, ["skeleton"])
        self.assertEqual(events, [])

    def test_soviet_train_collapses_to_visual_anchor_only_in_matching_context(self):
        anchors, events = normalize_visual_musts(
            ["soviet train"],
            context="vintage soviet train winter tracks Ural mountains",
        )
        self.assertEqual(anchors, ["train"])
        self.assertEqual(
            events,
            [{
                "from": "soviet train",
                "to": "train",
                "reason": "CONTEXTUAL_SOVIET_TRAIN_ANCHOR",
            }],
        )

    def test_soviet_train_requirement_remains_unchanged_without_context(self):
        anchors, events = normalize_visual_musts(
            ["soviet train"],
            context="snow-covered forest",
        )
        self.assertEqual(anchors, ["soviet train"])
        self.assertEqual(events, [])

    def test_ski_requirements_preserve_vintage_as_a_separate_evidence_anchor(self):
        anchors, events = normalize_visual_musts(
            ["vintage equipment", "skis"],
            context="vintage soviet skiing expedition equipment and wooden skis",
        )
        self.assertEqual(anchors, ["vintage", "ski equipment"])
        self.assertEqual(
            [(event["from"], event["to"], event["reason"]) for event in events],
            [
                ("vintage equipment", "vintage", "CONTEXTUAL_VINTAGE_SKI_CONTEXT"),
                ("skis", "ski equipment", "CONTEXTUAL_SKI_EQUIPMENT_ANCHOR"),
            ],
        )

    def test_ski_equipment_requirements_remain_unchanged_without_context(self):
        anchors, events = normalize_visual_musts(
            ["vintage equipment", "skis"],
            context="snow-covered Ural mountains",
        )
        self.assertEqual(anchors, ["vintage equipment", "skis"])
        self.assertEqual(events, [])

    def test_book_page_normalizes_to_page_in_printed_text_context(self):
        query = "vintage book page with Persian text printed"
        anchors, events = normalize_visual_musts(["book page"], context=query)
        self.assertEqual(anchors, ["page"])
        self.assertEqual(
            events,
            [{
                "from": "book page",
                "to": "page",
                "reason": "CONTEXTUAL_BOOK_PAGE_ANCHOR",
            }],
        )

    def test_book_page_requirement_stays_specific_without_printed_page_context(self):
        anchors, events = normalize_visual_musts(
            ["book page"],
            context="rare book with a leather cover in a museum",
        )
        self.assertEqual(anchors, ["book page"])
        self.assertEqual(events, [])

    def test_pilot_requirement_maps_to_microphone_for_equipment_only_query(self):
        query = "vintage aviation radio microphone and headset equipment"
        anchors, events = normalize_visual_musts(["pilot"], context=query)
        self.assertEqual(anchors, ["microphone"])
        self.assertEqual(
            events,
            [{
                "from": "pilot",
                "to": "microphone",
                "reason": "CONTEXTUAL_PILOT_EQUIPMENT_ANCHOR",
            }],
        )

    def test_visible_pilot_requirement_is_preserved_when_person_is_in_query(self):
        for query in (
            "pilot screaming inside cockpit wearing headset",
            "aviator standing beside vintage aircraft",
        ):
            anchors, events = normalize_visual_musts(["pilot"], context=query)
            self.assertEqual(anchors, ["pilot"], query)
            self.assertEqual(events, [], query)

    def test_winter_gear_becomes_preference_when_skiers_and_snow_are_required(self):
        anchors, events = normalize_visual_musts(
            ["skiers", "snow", "winter gear"],
            context=(
                "soviet winter mountain expedition snow landscape 1950s "
                "skiers snow winter gear"
            ),
        )
        self.assertEqual(anchors, ["skiers", "snow"])
        self.assertEqual(
            events,
            [{
                "from": "winter gear",
                "to": "preferred:winter gear",
                "reason": "UNSUPPORTED_VISUAL_DETAIL_PREFERENCE",
            }],
        )

    def test_winter_gear_stays_generic_without_ski_context(self):
        anchors, events = normalize_visual_musts(
            ["winter gear"],
            context="winter mountain expedition in cold weather",
        )
        self.assertEqual(anchors, ["winter gear"])
        self.assertEqual(events, [])

    def test_generic_text_collapses_with_document_only_in_archive_context(self):
        anchors, events = normalize_visual_musts(
            ["document", "text"],
            context="old soviet investigation report paper document with russian text",
        )
        self.assertEqual(anchors, ["document"])
        self.assertEqual(
            events,
            [{
                "from": "text",
                "to": "document",
                "reason": "CONTEXTUAL_DOCUMENT_TEXT_ANCHOR",
            }],
        )

    def test_document_and_text_stay_separate_without_archive_context(self):
        anchors, events = normalize_visual_musts(
            ["document", "text"],
            context="a person reading a book outdoors",
        )
        self.assertEqual(anchors, ["document", "text"])
        self.assertEqual(events, [])

    def test_tent_fabric_normalizes_to_torn_tent_only_when_damage_is_in_context(self):
        anchors, events = normalize_visual_musts(
            ["tent fabric", "snow"],
            context="torn winter tent fabric in snow",
        )
        self.assertEqual(anchors, ["torn tent", "snow"])
        self.assertEqual(
            events,
            [{
                "from": "tent fabric",
                "to": "torn tent",
                "reason": "CONTEXTUAL_TENT_ANCHOR",
            }],
        )

    def test_generic_tent_fabric_does_not_imply_a_tear(self):
        anchors, events = normalize_visual_musts(
            ["tent fabric"],
            context="camping tent fabric display at an outdoor shop",
        )
        self.assertEqual(anchors, ["tent fabric"])
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


    def test_dead_body_scene_adds_a_visible_person_anchor(self):
        anchors, events = normalize_visual_musts(
            ["beach", "sand", "ocean"],
            context="dead person body lying on empty beach sand 1948",
        )
        self.assertEqual(anchors, ["beach", "sand", "ocean", "person"])
        self.assertEqual(events[-1]["reason"], "CONTEXTUAL_VISIBLE_PERSON_ANCHOR")

    def test_found_body_scene_adds_person_when_query_context_includes_narration(self):
        anchors, events = normalize_visual_musts(
            ["ocean", "shoreline"],
            context="coastal Australian beach shore landscape ocean view; the body was found on the shore",
        )
        self.assertEqual(anchors, ["ocean", "shoreline", "person"])
        self.assertEqual(events[-1]["reason"], "CONTEXTUAL_VISIBLE_PERSON_ANCHOR")

    def test_removed_clothing_label_becomes_an_explicit_visual_anchor(self):
        anchors, events = normalize_visual_musts(
            ["clothing", "fabric"],
            context="clothing fabric label removed vintage trousers closeup",
        )
        self.assertEqual(anchors, ["clothing", "fabric", "label"])
        self.assertEqual(events[-1]["reason"], "CONTEXTUAL_CLOTHING_LABEL_ANCHOR")

    def test_encrypted_text_adds_a_code_anchor(self):
        anchors, events = normalize_visual_musts(
            ["paper", "handwriting"],
            context="mysterious handwritten code on old paper; encrypted text on a rare book cover",
        )
        self.assertEqual(anchors, ["paper", "handwriting", "code"])
        self.assertEqual(events[-1]["reason"], "CONTEXTUAL_ENCRYPTED_CODE_ANCHOR")

    def test_generic_beach_does_not_invent_a_human_subject(self):
        anchors, events = normalize_visual_musts(
            ["ocean", "shoreline"],
            context="coastal Australian beach shore landscape ocean view 1940s",
        )
        self.assertEqual(anchors, ["ocean", "shoreline"])
        self.assertEqual(events, [])

    def test_unsupported_wooden_house_detail_becomes_a_preference(self):
        anchors, events = normalize_visual_musts(
            ["town", "snow", "wooden houses"],
            context=(
                "old russian town in sverdlovsk oblast winter aerial view; "
                "cidade ao centro da província de Oblast de Sverdlovsk"
            ),
        )
        self.assertEqual(anchors, ["town", "snow"])
        self.assertEqual(events[-1]["reason"], "UNSUPPORTED_VISUAL_DETAIL_PREFERENCE")
        self.assertEqual(events[-1]["to"], "preferred:wooden houses")

    def test_wooden_houses_remain_a_must_when_scene_text_names_them(self):
        anchors, events = normalize_visual_musts(
            ["town", "snow", "wooden houses"],
            context="old Russian town with wooden houses in snow",
        )
        self.assertEqual(anchors, ["town", "snow", "wooden houses"])
        self.assertEqual(events, [])

    def test_ski_scene_keeps_people_and_snow_as_musts(self):
        anchors, events = normalize_visual_musts(
            ["skiers", "snow", "backpacks", "winter gear"],
            context="group of vintage skiers on snowy mountain expedition",
        )
        self.assertEqual(anchors, ["skiers", "snow"])
        self.assertEqual(
            [(event["from"], event["to"]) for event in events],
            [
                ("backpacks", "preferred:backpacks"),
                ("winter gear", "preferred:winter gear"),
            ],
        )
        self.assertTrue(all(
            event["reason"] == "UNSUPPORTED_VISUAL_DETAIL_PREFERENCE"
            for event in events
        ))

    def test_ski_equipment_can_remain_required_without_people_and_snow_context(self):
        anchors, events = normalize_visual_musts(
            ["ski equipment"],
            context="close-up of ski equipment in a shop",
        )
        self.assertEqual(anchors, ["ski equipment"])
        self.assertEqual(events, [])

    def test_vintage_paper_texture_becomes_preference_for_map_scenes(self):
        anchors, events = normalize_visual_musts(
            ["map", "vintage paper texture"],
            context="historic British countryside map 1926",
        )
        self.assertEqual(anchors, ["map"])
        self.assertEqual(events, [{
            "from": "vintage paper texture",
            "to": "preferred:vintage paper texture",
            "reason": "UNSUPPORTED_VISUAL_DETAIL_PREFERENCE",
        }])

    def test_vintage_paper_texture_remains_a_must_without_map_context(self):
        anchors, events = normalize_visual_musts(
            ["vintage paper texture"],
            context="close-up of an old document",
        )
        self.assertEqual(anchors, ["vintage paper texture"])
        self.assertEqual(events, [])

if __name__ == "__main__":
    unittest.main()




