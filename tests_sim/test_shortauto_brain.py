import json
import tempfile
import unittest
from pathlib import Path

import shortauto_brain as brain


class ShortAutoBrainTests(unittest.TestCase):
    def test_fact_layer_is_closed_source_sentences(self):
        facts = brain.fact_layer("Fact one happened in 1962. Fact two names three men.")
        self.assertEqual(len(facts), 2)
        self.assertEqual(facts[0]["fact_id"], "fact_001")
        self.assertIn("1962", facts[0]["text"])

    def test_evidence_map_links_scene_to_best_fact(self):
        facts = brain.fact_layer("They made dummy heads from paper mache. Three men escaped Alcatraz in 1962.")
        scenes = [{"text": "dummy heads made from paper mache"}, {"text": "three men escaped Alcatraz in 1962"}]
        report = brain.build_evidence_map(scenes, facts)
        self.assertEqual(report["coverage"], 100.0)
        self.assertEqual(report["scenes"][0]["fact_id"], "fact_001")
        self.assertEqual(report["scenes"][1]["fact_id"], "fact_002")

    def test_story_graph_requires_opening_and_payoff_shape(self):
        scenes = [{"narrative_role": "hook"}, {"narrative_role": "context"}, {"narrative_role": "reveal"}, {"narrative_role": "conclusion"}]
        graph = brain.infer_story_graph(scenes)
        self.assertTrue(graph["arc_ok"])
        self.assertGreater(graph["scenes"][0]["retention_target"], graph["scenes"][1]["retention_target"])

    def test_hook_ab_uses_existing_factual_candidates(self):
        plan = brain.hook_plan({"hooks": [
            {"text": "A", "curiosity": 9, "clarity": 8, "factuality": 10, "retention": 9},
            {"text": "B", "curiosity": 7, "clarity": 9, "factuality": 10, "retention": 8},
        ]})
        self.assertTrue(plan["ab_ready"])
        self.assertEqual(plan["recommended"], "A")
        self.assertEqual(plan["variants"][0]["text"], "A")

    def test_quality_budget_blocks_repetition_and_weak_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = {
                "retention": root / "r.json", "media": root / "m.json", "caption": root / "c.json", "visual": root / "v.json"
            }
            paths["retention"].write_text(json.dumps({"retention_score": 90}), encoding="utf-8")
            paths["media"].write_text(json.dumps({"critical": []}), encoding="utf-8")
            paths["caption"].write_text(json.dumps({"score": 95}), encoding="utf-8")
            paths["visual"].write_text(json.dumps({"score": 90}), encoding="utf-8")
            budget = brain.quality_budget(paths, {"coverage": 70}, {"repetition_ratio": 0.3})
            self.assertEqual(budget["status"], "BLOCK")
            self.assertFalse(budget["checks"]["evidence_coverage"])
            self.assertFalse(budget["checks"]["visual_repetition"])

    def test_cross_video_hash_history_detects_exact_reuse(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = (brain.BASE, brain.REPORTS)
            try:
                brain.BASE = root
                brain.REPORTS = root / "reports" / "brain"
                a = root / "imagens" / "short_a"; b = root / "imagens" / "short_b"
                a.mkdir(parents=True); b.mkdir(parents=True)
                (a / "scene_01.jpg").write_bytes(b"same-media")
                (b / "scene_01.jpg").write_bytes(b"same-media")
                first = brain.repetition_report("a")
                second = brain.repetition_report("b")
                self.assertEqual(first["reused_assets"], 0)
                self.assertEqual(second["reused_assets"], 1)
            finally:
                brain.BASE, brain.REPORTS = old

    def test_analytics_loop_learns_best_hook_variant(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = (brain.ANALYTICS, brain.CHANNEL)
            try:
                brain.ANALYTICS = root
                brain.CHANNEL = "test"
                path = root / "test.jsonl"; root.mkdir(parents=True)
                rows = [
                    {"hook_variant": "A", "percent_viewed": 80},
                    {"hook_variant": "A", "percent_viewed": 90},
                    {"hook_variant": "B", "percent_viewed": 60},
                ]
                path.write_text("\n".join(json.dumps(x) for x in rows) + "\n", encoding="utf-8")
                summary = brain.analytics_summary()
                self.assertIn("best_hook_variant=A", summary["insights"])
            finally:
                brain.ANALYTICS, brain.CHANNEL = old


if __name__ == "__main__":
    unittest.main()
