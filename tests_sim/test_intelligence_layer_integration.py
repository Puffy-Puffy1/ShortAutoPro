import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class IntelligenceIntegrationTests(unittest.TestCase):
    def test_main_has_all_four_intelligence_checkpoints_in_order(self):
        text = (ROOT / "main.py").read_text(encoding="utf-8")
        pre = text.index("INTELLIGENCE PRE: STORY + CLAIM LOCK")
        scene = text.index("INTELLIGENCE SCENE: ENTITY/TIME/GEO/VISUAL ROLES")
        media = text.index("INTELLIGENCE MEDIA: SOURCE/CACHE/AGING")
        final = text.index("INTELLIGENCE FINAL: EXPLAINABLE QA + CONFIDENCE")
        self.assertLess(pre, scene)
        self.assertLess(scene, media)
        self.assertLess(media, final)

    def test_intelligence_layer_never_imports_or_rewrites_visual_selector(self):
        text = (ROOT / "shortauto_intelligence_layer.py").read_text(encoding="utf-8")
        self.assertNotIn("import visual_selection_engine_v4", text)
        self.assertNotIn("from visual_selection_engine_v4", text)

    def test_release_gate_reads_intelligence_but_keeps_existing_weights(self):
        text = (ROOT / "release_gate.py").read_text(encoding="utf-8")
        self.assertIn('reports"/"intelligence"', text)
        self.assertIn("SAP_INTELLIGENCE_ENFORCE", text)
        self.assertIn('"script_score":0.14', text)
        self.assertIn('"technical_score":0.15', text)
        self.assertIn('"shortauto_intelligence":intelligence', text)

    def test_production_manifest_attaches_intelligence_reports(self):
        text = (ROOT / "production_manifest.py").read_text(encoding="utf-8")
        self.assertIn('INTELLIGENCE_DIR', text)
        self.assertIn('"explainable_qa"', text)
        self.assertIn('"confidence_automation"', text)
        self.assertIn('"module_versions"', text)

    def test_health_and_control_center_expose_intelligence(self):
        health = (ROOT / "health_check.sh").read_text(encoding="utf-8")
        control = (ROOT / "control_center.sh").read_text(encoding="utf-8")
        self.assertIn("shortauto_intelligence_layer.py", health)
        self.assertIn('"shortauto_intelligence_layer"', health)
        self.assertIn("26) Intelligence - PRE", control)
        self.assertIn("30) Intelligence - Status completo", control)

    def test_intelligence_runtime_is_ignored(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("reports/intelligence/", text)

    def test_layer_covers_requested_reliability_contracts(self):
        text = (ROOT / "shortauto_intelligence_layer.py").read_text(encoding="utf-8")
        required = (
            "claim_engine", "claim_lock", "story_architecture",
            "entity_consistency", "temporal_intelligence",
            "geographic_consistency", "scene_purpose",
            "information_density", "semantic_visual_safety",
            "historical_authenticity", "media_intelligence",
            "smart_cache_and_aging", "script_history_update",
            "hook_laboratory", "ending_laboratory",
            "special_scene_planning", "editing_grammar",
            "render_budget", "explainable_qa",
            "confidence_policy", "failure_knowledge_update",
            "module_versions",
        )
        for name in required:
            self.assertIn(f"def {name}", text)


if __name__ == "__main__":
    unittest.main()
