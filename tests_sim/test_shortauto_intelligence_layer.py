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

    def test_claim_lock_combines_multiple_source_sentences_without_lowering_single_claim_threshold(self):
        source = (
            "Incidente do Passo Dyatlov foi um acontecimento que resultou na morte de nove "
            "esquiadores ao norte dos montes Urais, na antiga União Soviética, na noite de "
            "2 de fevereiro de 1959. Investigadores da época determinaram que os esquiadores "
            "rasgaram suas barracas de dentro para fora, fugindo a pé sob forte nevasca."
        )
        script = (
            "Nove esquiadores experientes fugiram de sua barraca rasgando-a por dentro, "
            "na noite de 2 de fevereiro de 1959, sob forte nevasca."
        )
        result = intel.claim_lock(script, intel.claim_engine(source))
        row = result["sentences"][0]
        self.assertLess(row["support"], intel.CLAIM_SINGLE_SUPPORT_THRESHOLD)
        self.assertGreaterEqual(row["aggregate_support"], intel.CLAIM_MULTI_SUPPORT_THRESHOLD)
        self.assertGreaterEqual(len(row["supporting_claim_ids"]), 2)
        self.assertTrue(row["locked"])
        self.assertEqual(result["coverage"], 100.0)

    def test_claim_engine_does_not_treat_source_section_headings_as_evidence(self):
        claims = intel.claim_engine(
            "=== Testes militares ===\nPesquisadores analisaram as evidências do incidente."
        )
        self.assertTrue(claims)
        self.assertFalse(any(claim["text"].startswith("===") for claim in claims))

    def test_claim_lock_excludes_explicit_rhetorical_prompt_and_call_to_action(self):
        source = "Os esquiadores acamparam nas montanhas durante o inverno."
        script = (
            "Os esquiadores acamparam nas montanhas durante o inverno. "
            "O que realmente aconteceu naquela noite gelada? "
            "Comente sua teoria e inscreva-se."
        )
        result = intel.claim_lock(script, intel.claim_engine(source))
        self.assertEqual(result["coverage"], 100.0)
        self.assertEqual(result["factual_sentence_count"], 1)
        self.assertEqual(result["editorial_prompt_count"], 2)
        self.assertEqual(result["unsupported"], [])
        self.assertTrue(all(row["coverage_exempt"] for row in result["sentences"][1:]))

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

    def test_geographic_consistency_allows_specific_and_component_region_names(self):
        rows = [
            {
                "location": "Northern Ural Mountains",
                "query": "archival winter camp in the Ural Mountains",
                "segment": "The camp was in the northern Ural range.",
            },
            {
                "location": "Ural Mountains",
                "query": "snowy mountain terrain",
                "segment": "The range was covered in snow.",
            },
            {
                "location": "Kholat Syakhl",
                "query": "Kholat Syakhl winter camp",
                "segment": "The camp site.",
            },
        ]
        result = intel.geographic_consistency(rows)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["mismatches"], [])

    def test_geographic_consistency_allows_country_parent_of_region(self):
        rows = [
            {
                "location": "Bass Strait",
                "query": "ocean search and rescue boat waves Australia",
                "segment": "Teams searched the sea.",
            },
            {
                "location": "Australia",
                "query": "airplane metal debris on beach sand coast",
                "segment": "A fragment was found.",
            },
        ]
        result = intel.geographic_consistency(rows)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["mismatches"], [])

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

    def test_semantic_visual_safety_matches_full_avoid_phrase(self):
        rows = [{
            "segment": "The pilot checked the cockpit instruments.",
            "query": "vintage airplane cockpit instrument panel gauges",
            "must_have": ["dashboard", "gauges"],
            "avoid": ["modern glass cockpit", "flying saucer"],
        }]
        result = intel.semantic_visual_safety(rows)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["violations"], [])

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
