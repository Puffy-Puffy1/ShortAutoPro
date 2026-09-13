import unittest

import evidence_guard


class EvidenceGuardTests(unittest.TestCase):
    def test_stock_sources_are_allowed_without_case_claim(self):
        result = evidence_guard.avaliar_evidencia(
            {"fonte": "Pexels", "titulo": "generic city"},
            "Mary Celeste",
            "The ship was found abandoned",
            ["ship"],
            "environment",
        )
        self.assertTrue(result["allowed"])
        self.assertEqual(result["class"], "STOCK")

    def test_direct_case_metadata_is_preferred(self):
        result = evidence_guard.avaliar_evidencia(
            {"fonte": "Wikimedia", "titulo": "Mary Celeste abandoned ship"},
            "Mary Celeste",
            "The Mary Celeste was found abandoned at sea",
            ["Mary Celeste", "ship"],
            "transport",
        )
        self.assertTrue(result["allowed"])
        self.assertEqual(result["class"], "CASE_DIRECT")
        self.assertGreater(result["bonus"], 0)

    def test_generic_person_cannot_impersonate_case_subject(self):
        result = evidence_guard.avaliar_evidencia(
            {"fonte": "Wikimedia", "titulo": "Portrait photograph of unknown man"},
            "Frederick Valentich",
            "Frederick Valentich disappeared during a flight",
            ["pilot"],
            "human_context",
        )
        self.assertFalse(result["allowed"])
        self.assertEqual(result["class"], "RISKY_IDENTITY")

    def test_generic_document_without_anchor_is_rejected(self):
        result = evidence_guard.avaliar_evidencia(
            {"fonte": "Wikimedia", "titulo": "Historical investigation report document"},
            "Elisa Lam",
            "The investigation continued at the hotel",
            ["document"],
            "document",
        )
        self.assertFalse(result["allowed"])
        self.assertEqual(result["class"], "GENERIC_DOCUMENT")

    def test_contextual_location_needs_real_narrative_anchor(self):
        result = evidence_guard.avaliar_evidencia(
            {"fonte": "Wikimedia", "titulo": "Cecil Hotel Los Angeles exterior"},
            "Elisa Lam",
            "Elisa Lam stayed at the Cecil Hotel in Los Angeles",
            ["Cecil Hotel"],
            "location",
        )
        self.assertTrue(result["allowed"])
        self.assertEqual(result["class"], "CONTEXTUAL")

    def test_query_field_is_not_used_as_false_identity_evidence(self):
        result = evidence_guard.avaliar_evidencia(
            {
                "fonte": "Wikimedia",
                "titulo": "Generic ocean photograph",
                "query": "Mary Celeste",
            },
            "Mary Celeste",
            "The vessel crossed the Atlantic",
            ["ocean"],
            "environment",
        )
        self.assertFalse(result["allowed"])
        self.assertNotEqual(result["class"], "CASE_DIRECT")


if __name__ == "__main__":
    unittest.main()
