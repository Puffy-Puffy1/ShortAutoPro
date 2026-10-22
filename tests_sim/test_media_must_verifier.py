import unittest

from media_must_verifier import requirement_matches
from media_provider_router_v2 import _query_variants, query_relevance


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
        self.assertTrue(
            any("forensic medical report document snow-covered background" in item.casefold()
                for item in variants),
            variants,
        )

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


if __name__ == "__main__":
    unittest.main()
