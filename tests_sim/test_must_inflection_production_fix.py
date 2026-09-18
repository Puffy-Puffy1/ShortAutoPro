import unittest

import media_must_verifier as mustv
import media_acquisition_recovery as recovery


class MustInflectionProductionFixTests(unittest.TestCase):
    def test_regular_plural_requirement_matches_singular_asset_evidence(self):
        candidate = {
            "title": "Investigator reviewing paper evidence",
            "description": "An investigator examines a paper inside a prison case file.",
        }
        result = mustv.verified_must(
            candidate,
            {"must_have": ["investigators", "papers"]},
        )
        self.assertEqual(result["hits"], 2)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["missing"], [])

    def test_plural_asset_evidence_matches_singular_requirement(self):
        candidate = {
            "title": "Investigators reviewing papers",
            "description": "Investigators examine papers and records.",
        }
        result = mustv.verified_must(
            candidate,
            {"must_have": ["investigator", "paper"]},
        )
        self.assertEqual(result["hits"], 2)
        self.assertEqual(result["total"], 2)

    def test_irregular_plural_is_conservative(self):
        candidate = {"description": "Two men inside a prison cell"}
        result = mustv.verified_must(candidate, {"must_have": ["man", "prison"]})
        self.assertEqual(result["hits"], 2)

    def test_unrelated_concept_still_fails_closed(self):
        candidate = {
            "description": "Papers and documents on an empty office desk",
        }
        result = mustv.verified_must(
            candidate,
            {"must_have": ["investigators", "papers"]},
        )
        self.assertEqual(result["hits"], 1)
        self.assertEqual(result["total"], 2)
        self.assertIn("investigators", result["missing"])

    def test_query_echo_is_still_not_evidence(self):
        candidate = {
            "query": "investigators papers",
            "search_query": "investigators papers evidence",
            "description": "Empty prison corridor",
        }
        result = mustv.verified_must(
            candidate,
            {"must_have": ["investigators", "papers"]},
        )
        self.assertEqual(result["hits"], 0)

    def test_concept_alias_remains_strict_after_inflection(self):
        candidate = {
            "description": "Detective examining document records",
        }
        result = mustv.verified_must(
            candidate,
            {"must_have": ["investigators", "papers"]},
        )
        self.assertEqual(result["hits"], 2)

    def test_rescue_query_plan_is_stable_for_same_scene_contract(self):
        a = recovery._rescue_queries(
            "investigators",
            ["investigators", "papers"],
            "A Fuga de Alcatraz de 1962",
            "depois ajudou FBI.",
            "evidence",
        )
        b = recovery._rescue_queries(
            "papers",
            ["investigators", "papers"],
            "A Fuga de Alcatraz de 1962",
            "depois ajudou FBI.",
            "evidence",
        )
        self.assertEqual(a[:5], b[:5])


if __name__ == "__main__":
    unittest.main()
