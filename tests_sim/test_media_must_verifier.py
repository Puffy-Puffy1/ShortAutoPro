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
            any(item in variants for item in ("woodland", "pine forest", "taiga")),
            variants,
        )

    def test_woodland_metadata_matches_forest_query_relevance(self):
        result = query_relevance(
            "Soviet military checkpoint in winter forest",
            {"title": "Winter woodland near a Soviet military checkpoint"},
        )
        self.assertTrue(result["ok"], result)


if __name__ == "__main__":
    unittest.main()
