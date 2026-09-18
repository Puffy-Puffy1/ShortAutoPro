import json
import tempfile
import unittest
from pathlib import Path

import shortauto_intelligence_layer as intel


class IntelligenceLayerTests(unittest.TestCase):
    def test_claim_engine_and_lock_support_exact_fact(self):
        source = "Three men escaped Alcatraz in 1962. They made dummy heads from paper mache."
        script = "Three men escaped Alcatraz in 1962. They made dummy heads from paper mache."
        claims = intel.claim_engine(source)
        locked = intel.claim_lock(script, claims)
        self.assertEqual(len(claims), 2)
        self.assertEqual(locked["coverage"], 100.0)
        self.assertTrue(all(x["locked"] for x in locked["sentences"]))

    def test_story_architecture_contains_core_roles(self):
        script = "A mystery began. The men planned an escape. But one detail changed everything. The search intensified. A clue appeared. Nobody knows the final answer."
        result = intel.story_architecture(script)
        self.assertIn("hook", result["roles_present"])
        self.assertIn("setup", result["roles_present"])
        self.assertGreaterEqual(result["score"], 85)

    def test_temporal_intelligence_flags_backward_jump(self):
        rows = [
            {"segment": "In 1962 the escape happened.", "era": "1962"},
            {"segment": "In 1959 they arrived.", "era": "1959"},
        ]
        result = intel.temporal_intelligence("", rows)
        self.assertEqual(result["status"], "REVIEW")
        self.assertEqual(result["violations"][0]["scene"], 2)

    def test_geographic_consistency_blocks_other_known_location_in_query(self):
        rows = [
            {"location": "Adelaide", "query": "Adelaide beach archive", "segment": "A beach."},
            {"location": "Sydney", "query": "Adelaide harbor old photo", "segment": "Sydney."},
        ]
        result = intel.geographic_consistency(rows)
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["mismatches"][0]["scene"], 2)

    def test_visual_system_detects_repeated_shot_run(self):
        rows = [
            {"shot_type": "close_up", "segment": "a"},
            {"shot_type": "close_up", "segment": "b"},
            {"shot_type": "close_up", "segment": "c"},
        ]
        result = intel.visual_system(rows)
        self.assertEqual(result["status"], "REVIEW")
        self.assertTrue(result["repeated_shot_runs"])

    def test_semantic_visual_safety_blocks_avoid_term_in_query(self):
        rows = [{
            "segment": "Investigators examined the note.",
            "query": "gun note evidence table",
            "must_have": ["note"],
            "avoid": ["gun"],
        }]
        result = intel.semantic_visual_safety(rows)
        self.assertEqual(result["status"], "BLOCK")

    def test_historical_authenticity_penalizes_modern_term(self):
        rows = [{"era": "1948", "query": "1948 beach smartphone tourist", "segment": "The beach."}]
        result = intel.historical_authenticity(rows)
        self.assertEqual(result["status"], "REVIEW")
        self.assertLess(result["score"], 100)

    def test_source_reputation_grades_archives_above_unknown(self):
        self.assertEqual(intel.source_grade("Wikimedia archive"), "A")
        self.assertEqual(intel.source_grade("unknown-provider"), "D")

    def test_script_history_similarity_and_saturation(self):
        with tempfile.TemporaryDirectory() as td:
            old = intel.SCRIPT_HISTORY
            try:
                intel.SCRIPT_HISTORY = Path(td) / "history.json"
                one = intel.script_history_update("a", "same story about an escape from prison", "Alcatraz")
                two = intel.script_history_update("b", "same story about an escape from prison", "Alcatraz")
                self.assertEqual(one["max_similarity_last_100"], 0.0)
                self.assertGreaterEqual(two["max_similarity_last_100"], 0.9)
                self.assertEqual(two["topic_count_last_100"], 2)
            finally:
                intel.SCRIPT_HISTORY = old

    def test_hook_and_ending_labs_return_ranked_options(self):
        hooks = intel.hook_laboratory("A strange case began.", "Taman Shud")
        ending = intel.ending_laboratory("A strange case began. And the mystery remains?")
        self.assertGreaterEqual(len(hooks["variants"]), 5)
        self.assertIsNotNone(hooks["recommended"])
        self.assertIsNotNone(ending["recommended"])

    def test_explainable_qa_lists_deductions(self):
        payload = {
            "pre": {"claim_lock": {"coverage": 70}, "channel_memory": {"max_similarity_last_100": 0.9, "topic_saturation": "REVIEW"}},
            "scene": {
                "temporal": {"violations": [{"scene": 2}]},
                "geographic": {"mismatches": []},
                "visual": {"repeated_shot_runs": []},
                "semantic_visual_safety": {"status": "PASS"},
                "historical_authenticity": {"score": 100},
            },
            "media": {"important_low_reputation_scenes": []},
        }
        qa = intel.explainable_qa(payload)
        self.assertLess(qa["score"], 100)
        self.assertTrue(any("claim coverage" in x["reason"] for x in qa["deductions"]))

    def test_confidence_policy_blocks_critical(self):
        result = intel.confidence_policy({"score": 99}, ["geographic_mismatch"])
        self.assertEqual(result["decision"], "BLOCK")

    def test_failure_kb_is_idempotent_by_signature(self):
        with tempfile.TemporaryDirectory() as td:
            old = intel.FAILURE_KB
            try:
                intel.FAILURE_KB = Path(td) / "failures.json"
                intel.failure_knowledge_update("a", ["media failure"])
                intel.failure_knowledge_update("b", ["media failure"])
                rows = json.loads(intel.FAILURE_KB.read_text(encoding="utf-8"))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["occurrences"], 2)
            finally:
                intel.FAILURE_KB = old


if __name__ == "__main__":
    unittest.main()
