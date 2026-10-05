import unittest
from unittest.mock import patch

from media_must_verifier import requirement_matches, verified_must
from media_provider_router_v2 import MediaProviderRouterV2


class MediaMustVerifierRegressionTests(unittest.TestCase):
    def test_female_pilots_and_airplane_aliases_are_conservative(self):
        candidate = {
            "description": "group of women aviators posing beside an aircraft in 1930s",
        }
        self.assertTrue(requirement_matches("female pilots", candidate))
        self.assertTrue(requirement_matches("airplane", candidate))

    def test_unrelated_people_do_not_satisfy_female_pilots(self):
        candidate = {"description": "group of men posing beside an aircraft"}
        self.assertFalse(requirement_matches("female pilots", candidate))

    def test_query_variants_continue_after_generic_first_result(self):
        class Provider:
            name = "fake"
            def __init__(self):
                self.queries = []
            def search(self, query, must, avoid):
                self.queries.append(query)
                if query == "group of female pilots posing by aircraft 1930s":
                    return [{
                        "fonte": "fake", "id": "generic", "descricao": "aircraft",
                        "score": 10, "must_hits": 0, "avoid_hits": 0,
                    }]
                if query == "female pilots":
                    return [{
                        "fonte": "fake", "id": "verified", "descricao":
                            "group of female pilots beside an airplane",
                        "score": 40, "must_hits": 2, "avoid_hits": 0,
                    }]
                return []

        provider = Provider()
        router = MediaProviderRouterV2(providers=[provider])
        candidates = router.search(
            "group of female pilots posing by aircraft 1930s",
            ["female pilots", "airplane"],
            ["men only"],
        )
        ids = {str(x.get("id")) for x in candidates}
        self.assertIn("generic", ids)
        self.assertIn("verified", ids)
        self.assertGreaterEqual(len(provider.queries), 2)

    def test_verified_must_stays_fail_closed(self):
        good = {"description": "female pilots with an airplane"}
        bad = {"description": "female pilots in a modern office"}
        self.assertEqual(verified_must(good, {"must_have": ["female pilots", "airplane"]})["hits"], 2)
        self.assertLess(verified_must(bad, {"must_have": ["female pilots", "airplane"]})["hits"], 2)


if __name__ == "__main__":
    unittest.main()
