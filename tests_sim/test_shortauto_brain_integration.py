import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ShortAutoBrainIntegrationTests(unittest.TestCase):
    def test_release_gate_invokes_brain_without_replacing_existing_score(self):
        text = (ROOT / "release_gate.py").read_text(encoding="utf-8")
        self.assertIn("import shortauto_brain as brain", text)
        self.assertIn("brain.prepare(SID)", text)
        self.assertIn("brain.quality(SID,enforce=False)", text)
        self.assertIn('SAP_BRAIN_ENFORCE', text)
        self.assertIn('"shortauto_brain":brain', text)
        self.assertIn('"script_score":0.14', text)
        self.assertIn('"technical_score":0.15', text)

    def test_brain_enforcement_blocks_human_approval_and_review_decisions(self):
        from release_gate import brain_enforcement_issues

        self.assertEqual(
            brain_enforcement_issues(True, "PASS", "PASS", "HUMAN_APPROVAL_REQUIRED"),
            ["shortauto_brain_approval_required"],
        )
        self.assertEqual(
            brain_enforcement_issues(True, "PASS", "PASS", "HUMAN_REVIEW_REQUIRED"),
            ["shortauto_brain_approval_required"],
        )
        self.assertEqual(
            brain_enforcement_issues(True, "PASS", "PASS", "AUTO_RELEASE_ALLOWED"),
            [],
        )
        self.assertEqual(
            brain_enforcement_issues(False, "PASS", "PASS", "HUMAN_APPROVAL_REQUIRED"),
            [],
        )

    def test_brain_human_approval_is_reported_as_repair_action(self):
        from release_gate import brain_repair_actions

        self.assertEqual(
            brain_repair_actions("HUMAN_APPROVAL_REQUIRED"),
            ["obtain_shortauto_brain_human_approval"],
        )
        self.assertEqual(
            brain_repair_actions("HUMAN_REVIEW_REQUIRED"),
            ["obtain_shortauto_brain_human_approval"],
        )
        self.assertEqual(brain_repair_actions("AUTO_RELEASE_ALLOWED"), [])

    def test_control_center_exposes_brain_operations(self):
        text = (ROOT / "control_center.sh").read_text(encoding="utf-8")
        self.assertIn("SHORTAUTO PRO - CONTROL CENTER 4.0", text)
        self.assertIn('BRAIN="$BASE/shortauto_brain.py"', text)
        self.assertIn("Brain - preparar Evidence/Story/A-B", text)
        self.assertIn("Brain - Quality Budget", text)
        self.assertIn("Brain - Registrar analytics", text)

    def test_brain_runtime_outputs_are_ignored(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("reports/brain/", text)
        self.assertIn("reports/analytics/", text)

    def test_brain_is_one_consolidated_layer_not_parallel_pipeline(self):
        text = (ROOT / "shortauto_brain.py").read_text(encoding="utf-8")
        self.assertIn("does not replace certified production engines", text)
        self.assertNotIn("visual_selection_engine_v4", text)
        for capability in (
            '"fact_layer": True',
            '"evidence_map": True',
            '"story_graph": True',
            '"hook_ab": True',
            '"analytics_loop": True',
            '"editorial_memory": True',
            '"quality_budget": True',
            '"autonomy_levels": True',
            '"brain": True',
        ):
            self.assertIn(capability, text)


if __name__ == "__main__":
    unittest.main()
