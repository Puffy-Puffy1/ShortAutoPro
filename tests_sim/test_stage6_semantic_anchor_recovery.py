import unittest
from pathlib import Path

import media_acquisition_recovery as recovery
import media_must_priority as priority
import media_must_verifier as verifier


class Stage6SemanticAnchorRecoveryTests(unittest.TestCase):
    def test_single_stock_must_is_normalized(self):
        result = priority.prioritize(
            ["empty ornate golden picture frames"],
            query="empty ornate golden picture frames hanging on dark wall",
            visual_mode="object",
        )
        self.assertEqual(result["strict"], ["picture frames"])
        self.assertIn("empty ornate golden picture frames", result["context"])

    def test_known_object_alias_remains_canonical(self):
        result = priority.prioritize(
            ["empty golden frames"],
            visual_mode="object",
        )
        self.assertEqual(result["strict"], ["picture frame"])
        self.assertIn("empty golden frames", result["context"])

    def test_documentary_mode_removes_only_safe_visual_modifiers(self):
        result = priority.prioritize(
            ["historic old paper document", "Boston museum"],
            visual_mode="evidence",
        )
        self.assertEqual(result["strict"], ["paper document", "boston museum"])
        self.assertIn("historic old paper document", result["context"])

    def test_identity_tokens_are_not_removed(self):
        self.assertEqual(
            priority._conservative_stock_anchor(
                "Isabella Stewart Gardner museum",
                "location",
            ),
            "isabella stewart gardner museum",
        )
        self.assertEqual(
            priority._conservative_stock_anchor(
                "red telephone",
                "object",
            ),
            "red telephone",
        )

    def test_normalized_document_requirement_can_use_concept_evidence(self):
        candidate = {"description": "archival document from police records"}
        self.assertTrue(verifier.requirement_matches("paper document", candidate))

    def test_stock_rescue_default_budget_is_four(self):
        text = Path("media_acquisition_recovery.py").read_text(encoding="utf-8")
        self.assertIn('SAP_STOCK_RESCUE_MAX_QUERIES", "4"', text)
        self.assertIn('VERSION = "1.7"', text)

    def test_rescue_queries_stay_bounded(self):
        queries = recovery._rescue_queries(
            "empty ornate golden picture frames on wall",
            ["picture frames"],
            visual_mode="object",
        )
        self.assertLessEqual(len(queries), 5)
        self.assertTrue(any("picture frames" in q for q in queries))


if __name__ == "__main__":
    unittest.main()
