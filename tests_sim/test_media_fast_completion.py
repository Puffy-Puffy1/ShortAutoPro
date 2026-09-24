import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MediaFastCompletionContractTests(unittest.TestCase):
    def test_stage_defaults_are_mobile_bounded(self):
        text = (ROOT / "media_stage_runtime.py").read_text(encoding="utf-8")
        self.assertIn('SAP_MEDIA_STAGE_ROUNDS\", 2', text)
        self.assertIn('SAP_MEDIA_SCENE_BUDGET_SECONDS\", 18.0', text)
        self.assertIn('SAP_MEDIA_ROUND_TIMEOUT\", 60', text)
        self.assertNotIn('SAP_MEDIA_SCENE_BUDGET_SECONDS\", 75.0', text)
        self.assertIn('min(max(base, dynamic), 195)', text)

    def test_media_runtime_has_editorial_completion(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("create_editorial_reuse", text)
        self.assertIn("SAP_MEDIA_EDITORIAL_REUSE=COMPLETED", text)
        self.assertIn('\"EditorialReuse\": 0', text)

    def test_emergency_fallback_never_claims_evidence(self):
        text = (ROOT / "media_emergency_fallback.py").read_text(encoding="utf-8")
        self.assertIn('\"truth_claim\": \"NONE\"', text)
        self.assertIn("neutral generated editorial slate", text)
        self.assertIn("editorial derivative of accepted primary production media", text)

    def test_local_scene_fallback_does_not_invent_musts(self):
        text = (ROOT / "scene_director.py").read_text(encoding="utf-8")
        self.assertIn('\"must_have\": []', text)
        self.assertIn('\"must_policy\": \"NONE_LOCAL_FALLBACK\"', text)

    def test_visual_fallback_does_not_promote_arbitrary_words_to_must(self):
        text = (ROOT / "visual_director.py").read_text(encoding="utf-8")
        self.assertIn("Hard MUSTs are factual contracts", text)
        self.assertIn("must = []", text)

    def test_simplified_retry_default_is_disabled(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn('SAP_MEDIA_SIMPLIFIED_RETRY_MAX\", 0', text)


if __name__ == "__main__":
    unittest.main()
