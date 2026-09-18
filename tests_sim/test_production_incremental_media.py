import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProductionIncrementalMediaTests(unittest.TestCase):
    def test_stage6_preserves_previous_successes(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("SAP_MEDIA_INCREMENTAL=RESTORE", text)
        self.assertIn("SAP_MEDIA_INCREMENTAL=HIT", text)
        self.assertIn("resume_cached_media = {}", text)
        self.assertIn("MISSING_REPORT", text)

    def test_incremental_cache_requires_matching_current_scene_map(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("_report_matches", text)
        self.assertIn("_scene_map_not_newer", text)
        self.assertIn("_sap_probe_existing_media", text)
        self.assertIn("width * height >= 320 * 180", text)

    def test_only_missing_scenes_are_reacquired(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        hit = text.index("SAP_MEDIA_INCREMENTAL=HIT")
        providers = text.index("# TODAS AS FONTES COMPETEM", hit)
        self.assertLess(hit, providers)
        self.assertIn("continue", text[hit:providers])

    def test_full_media_stage_is_not_retried_externally(self):
        resume = (ROOT / "resume_after_semantic_fix.py").read_text(encoding="utf-8")
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('("6 - SMART MEDIA SELECTOR", "midia.py", (), 0)', resume)
        self.assertIn('p.run("6 - SMART MEDIA SELECTOR", "midia.py")', main)
        self.assertNotIn('p.run("6 - SMART MEDIA SELECTOR", "midia.py", retries=1)', main)

    def test_strict_must_policy_remains_fail_closed(self):
        strict = (ROOT / "media_strict_must_guard.py").read_text(encoding="utf-8")
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("EXPLICIT_MUST_FAIL_CLOSED", strict)
        self.assertIn("SAP_MUST_LATE_RECOVERY=START", text)
        self.assertNotIn("SAP_STRICT_MUST_GUARD=DISABLED", text)


if __name__ == "__main__":
    unittest.main()
