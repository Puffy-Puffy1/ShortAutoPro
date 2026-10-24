import unittest

from media_must_verifier import requirement_matches
from media_provider_router_v2 import _query_variants, query_relevance


class MediaMustVerifierRibCageTests(unittest.TestCase):
    def test_rib_cage_requires_explicit_asset_metadata(self):
        self.assertTrue(
            requirement_matches(
                "rib cage",
                {"description": "medical x ray showing human rib cage and skeletal structure"},
            )
        )
        self.assertFalse(
            requirement_matches(
                "rib cage",
                {"description": "medical x ray showing the human spine and skull"},
            )
        )


class MediaMustVerifierSecuritySensorTests(unittest.TestCase):
    def test_security_sensor_accepts_verified_visual_equivalents(self):
        for evidence in (
            "close-up of a motion sensor on a security door",
            "alarm sensor installed on a building entrance",
            "door sensor security alarm hardware",
        ):
            self.assertTrue(
                requirement_matches("security sensor", {"description": evidence}),
                evidence,
            )

    def test_security_sensor_does_not_accept_generic_security_camera(self):
        self.assertFalse(
            requirement_matches(
                "security sensor",
                {"description": "security camera monitoring a building"},
            )
        )


class MediaMustVerifierCanvasRingTests(unittest.TestCase):
    def test_canvas_ring_must_accept_wrestling_ring_metadata(self):
        for evidence in (
            "professional wrestler in a wrestling ring",
            "boxing ring with two athletes",
            "professional wrestling ring during a match",
        ):
            self.assertTrue(
                requirement_matches("canvas ring", {"description": evidence}),
                evidence,
            )

    def test_canvas_ring_must_reject_generic_wrestler_without_ring_evidence(self):
        self.assertFalse(
            requirement_matches(
                "canvas ring",
                {"description": "professional wrestler portrait backstage"},
            )
        )


class MediaMustVerifierQuillPenTests(unittest.TestCase):
    def test_quill_pen_accepts_explicit_catalog_equivalents(self):
        for evidence in (
            "antique quill pen beside an inkwell",
            "feather quill pen on a writing desk",
            "writing quill and ink bottle",
            "quill with inkwell in a historical study",
        ):
            self.assertTrue(
                requirement_matches("quill pen", {"description": evidence}),
                evidence,
            )

    def test_quill_pen_rejects_a_generic_feather(self):
        self.assertFalse(
            requirement_matches(
                "quill pen",
                {"description": "feather on a wooden table beside a bottle"},
            )
        )

    def test_quill_search_variants_preserve_context(self):
        variants = _query_variants(
            "vintage quill pen and inkwell on old wooden desk",
            ["quill pen"],
        )
        self.assertLessEqual(len(variants), 8)
        self.assertTrue(
            any("feather quill" in item.casefold() for item in variants),
            variants,
        )


class MediaMustVerifierInteriorTests(unittest.TestCase):
    def test_interior_must_accepts_explicit_indoor_space_metadata(self):
        for evidence in (
            "hotel hallway with doors",
            "historic room interior",
            "lobby of an old building",
            "corridor inside a hotel",
        ):
            self.assertTrue(
                requirement_matches("interior", {"description": evidence}),
                evidence,
            )

    def test_interior_must_rejects_explicit_outdoor_metadata(self):
        self.assertFalse(
            requirement_matches(
                "interior",
                {"description": "hotel exterior street facade outdoors"},
            )
        )


class MediaMustVerifierForestTests(unittest.TestCase):
    def test_forest_must_accepts_explicit_woodland_equivalents(self):
        for evidence in (
            "Pine woodland covered in winter snow",
            "Coniferous forest in a mountain valley",
            "Boreal forest near a remote checkpoint",
            "Taiga landscape in winter",
        ):
            self.assertTrue(
                requirement_matches("forest", {"description": evidence}),
                evidence,
            )

    def test_forest_must_does_not_accept_unrelated_winter_scene(self):
        self.assertFalse(
            requirement_matches(
                "forest",
                {"description": "Soviet military checkpoint on an open snowy plain"},
            )
        )

    def test_forest_search_expands_without_changing_acceptance_rules(self):
        variants = _query_variants(
            "Soviet military checkpoint in winter forest",
            ["forest"],
        )
        self.assertLessEqual(len(variants), 8)
        self.assertTrue(
            any(any(alias in item.casefold() for alias in ("woodland", "pine forest", "taiga")) for item in variants),
            variants,
        )

    def test_must_aliases_preserve_the_original_scene_context(self):
        variants = _query_variants(
            "vintage forensic investigation equipment in winter snow field",
            ["snow"],
        )
        self.assertLessEqual(len(variants), 8)
        self.assertTrue(
            any(
                "vintage forensic investigation equipment" in item.casefold()
                and "snow-covered" in item.casefold()
                for item in variants
            ),
            variants,
        )
        self.assertEqual(variants[0], "vintage forensic investigation equipment in winter snow field")
        self.assertIn("snow", variants)
        self.assertIn("snowfall", variants)

    def test_darkness_must_accepts_explicit_night_metadata(self):
        for evidence in (
            "dark mountain slope at night",
            "nighttime landscape in low light",
        ):
            self.assertTrue(
                requirement_matches("darkness", {"description": evidence}),
                evidence,
            )

    def test_darkness_must_does_not_accept_unrelated_scene(self):
        self.assertFalse(
            requirement_matches(
                "darkness",
                {"description": "bright snowy mountain landscape in daylight"},
            )
        )

    def test_woodland_metadata_matches_forest_query_relevance(self):
        result = query_relevance(
            "Soviet military checkpoint in winter forest",
            {"title": "Winter woodland near a Soviet military checkpoint"},
        )
        self.assertTrue(result["ok"], result)


    def test_ski_catalog_singular_plural_matches_query_relevance(self):
        result = query_relevance(
            "skis poles",
            {"title": "ski pole"},
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(set(result["matched_terms"]), {"ski", "pole"})

    def test_ski_relevance_does_not_bypass_explicit_snow_must(self):
        candidate = {"title": "ski pole"}
        self.assertTrue(query_relevance("skis poles", candidate)["ok"])
        self.assertFalse(requirement_matches("snow", candidate))




class MediaMustVerifierMicrophoneTests(unittest.TestCase):
    def test_microphone_requires_explicit_microphone_evidence(self):
        for evidence in (
            "Aircraft radio microphone and control panel",
            "Pilot microphone inside a vintage cockpit",
            "Aviation communications microphone",
        ):
            self.assertTrue(
                requirement_matches("microphone", {"description": evidence}),
                evidence,
            )

    def test_radio_equipment_without_microphone_evidence_is_rejected(self):
        for evidence in (
            "Vintage aircraft radio and control panel",
            "Radio handset in a cockpit",
            "Aircraft transceiver mounted in the cockpit",
        ):
            self.assertFalse(
                requirement_matches("microphone", {"description": evidence}),
                evidence,
            )


class MediaMustVerifierSkiSnowSearchTests(unittest.TestCase):
    def test_ski_query_with_snow_must_adds_contextual_search_variants(self):
        query = "old wooden ski equipment discarded in deep snow"
        variants = _query_variants(query, ["snow"])
        self.assertEqual(variants[0], query)
        self.assertLessEqual(len(variants), 8)
        self.assertIn("wooden skis in snow", variants)
        self.assertIn("abandoned skis in snow", variants)
        self.assertIn("ski equipment in deep snow", variants)
        self.assertIn("snow", variants)

    def test_ski_musts_supply_context_when_the_query_omits_ski_words(self):
        query = "soviet winter mountain expedition snow landscape 1950s"
        variants = _query_variants(query, ["skiers", "snow", "ski equipment"])
        self.assertLessEqual(len(variants), 8)
        self.assertEqual(variants[0], query)
        self.assertIn("skiers", variants)
        self.assertIn("snow", variants)
        self.assertIn("ski equipment", variants)
        self.assertIn(
            "soviet winter mountain expedition snow landscape 1950s skiers ski equipment",
            variants,
        )
        self.assertIn("wooden skis in snow", variants)

    def test_ski_context_does_not_bypass_snow_metadata_requirement(self):
        self.assertTrue(
            requirement_matches(
                "snow",
                {"description": "old wooden skis abandoned in deep snow"},
            )
        )
        self.assertFalse(
            requirement_matches(
                "snow",
                {"description": "old wooden skis stored inside a museum"},
            )
        )




class MediaMustVerifierPencilTests(unittest.TestCase):
    def test_pencil_accepts_explicit_pencil_metadata(self):
        for evidence in ("graphite pencil on a map", "wooden pencil beside a chart", "mechanical pencil on paper"):
            self.assertTrue(requirement_matches("pencil", {"description": evidence}), evidence)

    def test_pencil_rejects_generic_pen_and_query_only_evidence(self):
        self.assertFalse(requirement_matches("pencil", {"description": "fountain pen on a map"}))
        self.assertFalse(requirement_matches("pencil", {"title": "navigation map", "query": "map pencil"}))

    def test_pencil_query_variants_include_specific_catalog_terms(self):
        variants = _query_variants("plotting course on aeronautical navigation map", ["map", "pencil"])
        self.assertLessEqual(len(variants), 8)
        self.assertTrue(any("pencil" in item.casefold() for item in variants), variants)


class MediaMustVerifierAviationNightSearchTests(unittest.TestCase):
    def test_airplane_ocean_night_scene_gets_contextual_catalog_variants(self):
        variants = _query_variants(
            "small airplane flying over dark ocean at night",
            ["airplane", "ocean", "night sky"],
        )
        self.assertLessEqual(len(variants), 8)
        self.assertEqual(variants[0], "small airplane flying over dark ocean at night")
        self.assertIn("airplane over ocean at night", variants)
        self.assertIn("aircraft over sea at night", variants)



class MediaMustVerifierTrainSnowSearchTests(unittest.TestCase):
    def test_train_and_snow_query_expansion_preserves_contextual_fallbacks(self):
        variants = _query_variants(
            "vintage train traveling through snow winter landscape",
            ["train", "snow"],
        )
        self.assertLessEqual(len(variants), 8)
        self.assertIn("train in snow", variants)
        self.assertIn("steam locomotive in snow", variants)



class MediaMustVerifierRussianWinterTownSearchTests(unittest.TestCase):
    def test_russian_winter_town_query_gets_two_contextual_searches(self):
        variants = _query_variants(
            "old russian town in sverdlovsk oblast winter aerial view",
            ["town", "snow", "wooden houses"],
        )
        self.assertLessEqual(len(variants), 8)
        self.assertEqual(
            variants[0],
            "old russian town in sverdlovsk oblast winter aerial view",
        )
        self.assertIn("old Russian town with wooden houses in snow", variants)
        self.assertIn("Sverdlovsk winter village wooden houses", variants)



class MediaMustVerifierTownPreferenceSearchTests(unittest.TestCase):
    def test_town_and_snow_search_expands_a_preferred_house_detail(self):
        variants = _query_variants(
            "old russian town in sverdlovsk oblast winter aerial view wooden houses",
            ["town", "snow"],
        )
        self.assertLessEqual(len(variants), 8)
        self.assertIn("old Russian town with wooden houses in snow", variants)
        self.assertIn("Sverdlovsk winter village wooden houses", variants)
