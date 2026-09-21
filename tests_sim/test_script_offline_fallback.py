import unittest

from script_fallback import (
    build_extractive_script,
    build_scene_queries,
    count_words,
)


class ScriptFallbackTests(unittest.TestCase):
    def _sentence(self, prefix: str, words: int) -> str:
        body = " ".join(f"{prefix}{i}" for i in range(words - 1))
        return f"{prefix.capitalize()} {body}."

    def test_build_extractive_script_hits_short_range_without_cutting_sentences(self):
        source = " ".join(
            [
                self._sentence("alpha", 28),
                self._sentence("beta", 30),
                self._sentence("gamma", 29),
                self._sentence("delta", 20),
                self._sentence("epsilon", 18),
            ]
        )
        script = build_extractive_script(source)
        self.assertTrue(script)
        self.assertGreaterEqual(count_words(script), 105)
        self.assertLessEqual(count_words(script), 125)
        self.assertIn("Alpha", script)
        self.assertIn("Gamma", script)
        self.assertTrue(script.endswith("Comente."))

    def test_fallback_returns_empty_when_no_complete_window_fits(self):
        source = self._sentence("gigante", 140)
        self.assertEqual(build_extractive_script(source), "")

    def test_scene_queries_match_requested_count(self):
        result = build_scene_queries("A Noite dos OVNIs no Brasil", 12)
        lines = [x for x in result.splitlines() if x.strip()]
        self.assertEqual(len(lines), 12)
        self.assertTrue(all("Noite" in line or "noite" in line for line in lines))

    def test_roteiro_uses_source_extractive_recovery_contract(self):
        text = open("roteiro.py", "r", encoding="utf-8").read()
        self.assertIn("SAP_SCRIPT_FALLBACK=SOURCE_EXTRACTIVE_OK", text)
        self.assertIn("SAP_SCRIPT_FACT_AUDIT=AI_EXHAUSTED", text)
        self.assertIn("SAP_SCRIPT_MODE=DEGRADED_SOURCE_EXTRACTIVE", text)
        self.assertNotIn("SAP_SCRIPT_TOPIC_INCOMPATIBLE=", text)


if __name__ == "__main__":
    unittest.main()
