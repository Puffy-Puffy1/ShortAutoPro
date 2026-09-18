import unittest
from pathlib import Path

import media_acquisition_recovery as recovery

ROOT = Path(__file__).resolve().parents[1]


class Stage6EarlyRecoveryTests(unittest.TestCase):
    def test_rescue_queries_include_scene_context(self):
        queries = recovery._rescue_queries(
            "escape route prison",
            ["dummy heads", "Alcatraz"],
            "Fuga de Alcatraz em junho de 1962",
            "The men left dummy heads in their cells before escaping.",
            "evidence",
        )
        joined = "\n".join(queries).lower()
        self.assertIn("dummy heads alcatraz", joined)
        self.assertIn("fuga de alcatraz", joined)
        self.assertTrue(any("the men left dummy" in q.lower() for q in queries))

    def test_midia_runs_early_recovery_before_evidence_selection(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        recovery_pos = text.index("SAP_MUST_EARLY_RECOVERY=START")
        evidence_pos = text.index("# MAIN WIKIMEDIA EVIDENCE 5.2")
        self.assertLess(recovery_pos, evidence_pos)
        self.assertIn("buscar_todos_candidatos(", text[recovery_pos:evidence_pos])
        self.assertIn("verified_must", text[recovery_pos:evidence_pos])

    def test_missing_scene_diagnostics_are_persisted(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("missing_scenes = []", text)
        self.assertIn("SAP_MEDIA_SCENE_MISSING", text)
        self.assertIn("SAP_MEDIA_MISSING_SCENES=", text)
        self.assertIn("acquisition_missing_", text)

    def test_strict_policy_not_relaxed(self):
        strict = (ROOT / "media_strict_must_guard.py").read_text(encoding="utf-8")
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("EXPLICIT_MUST_FAIL_CLOSED", strict)
        self.assertNotIn("SAP_STRICT_MUST_GUARD=DISABLED", text)


if __name__ == "__main__":
    unittest.main()
