import unittest

from visual_shot_policy import fallback_shot, normalize_shot_type, resolve_shot_type


class VisualShotPolicyTests(unittest.TestCase):
    def test_normalizes_common_director_labels(self):
        self.assertEqual(normalize_shot_type("wide shot"), "wide")
        self.assertEqual(normalize_shot_type("close-up"), "closeup")
        self.assertEqual(normalize_shot_type("macro"), "detail")
        self.assertEqual(normalize_shot_type("portrait"), "portrait")
        self.assertEqual(normalize_shot_type("security footage"), "")

    def test_candidate_has_priority_over_original(self):
        self.assertEqual(
            resolve_shot_type("wide shot", "medium", 2, "environment", "medium"),
            "wide",
        )

    def test_original_is_preserved_when_candidate_is_invalid(self):
        self.assertEqual(
            resolve_shot_type("generic", "close up", 3, "object", "wide"),
            "closeup",
        )

    def test_environment_fallback_varies_framing(self):
        first = fallback_shot(1, "environment", "")
        second = fallback_shot(2, "environment", first)
        self.assertEqual(first, "wide")
        self.assertEqual(second, "medium")

    def test_human_context_prefers_stable_portrait(self):
        self.assertEqual(fallback_shot(4, "human_context", "portrait"), "portrait")

    def test_documentary_fallback_uses_detail_and_medium(self):
        self.assertEqual(fallback_shot(1, "document", ""), "medium")
        self.assertEqual(fallback_shot(2, "evidence", "medium"), "detail")


if __name__ == "__main__":
    unittest.main()
