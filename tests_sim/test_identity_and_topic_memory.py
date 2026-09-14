import unittest

import source_identity
import topic_memory


class TopicMemoryTests(unittest.TestCase):
    def test_mh370_aliases_normalize_to_same_identity(self):
        variants = [
            "Malaysia Airlines Flight 370",
            "Voo MH-370",
            "O Voo 370 da Malaysia Airlines",
            "MH370",
        ]
        normalized = {topic_memory.normalizar(x) for x in variants}
        self.assertEqual(normalized, {"mh370"})

    def test_known_duplicate_is_detected(self):
        result = topic_memory.encontrar_duplicata(
            "O desaparecimento da tripulação do Mary Celeste",
            [{"topic": "Mary Celeste"}],
        )
        self.assertTrue(result["duplicate"])
        self.assertGreaterEqual(result["similarity"], 0.72)

    def test_year_alone_is_not_a_strong_identifier(self):
        score = topic_memory.similaridade(
            "Caso Valentich 1978",
            "Caso Valentich 1979",
        )
        self.assertLess(score, 0.72)

    def test_empty_values_are_safe(self):
        self.assertEqual(topic_memory.normalizar(None), "")
        self.assertEqual(topic_memory.similaridade("", "qualquer coisa"), 0.0)

    def test_missing_history_topics_are_ignored(self):
        result = topic_memory.encontrar_duplicata(
            "None",
            [{"topic": None}, None, {"topic": ""}],
        )
        self.assertEqual(
            result,
            {"duplicate": False, "topic": None, "similarity": 0.0},
        )


class SourceIdentityTests(unittest.TestCase):
    def test_alias_boundary_does_not_match_mh3700(self):
        self.assertNotIn("mh370", source_identity.detectar_aliases("MH3700"))

    def test_known_alias_title_match(self):
        result = source_identity.validar_identidade(
            "Caso Boy in the Box",
            "Joseph Augustus Zarelli",
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["reason"], "known_alias_match")

    def test_known_alias_conflict_is_rejected(self):
        result = source_identity.validar_identidade(
            "MH370",
            "TAM 3054",
        )
        self.assertFalse(result["valid"])
        self.assertIn(result["reason"], {"known_alias_conflict", "numeric_identity_conflict:topic=['370'],title=['3054']"})

    def test_numeric_identity_conflict_is_rejected(self):
        result = source_identity.validar_identidade(
            "Voo 447",
            "Voo 3054",
        )
        self.assertFalse(result["valid"])
        self.assertTrue(result.get("truth_lock"))
        self.assertEqual(result["topic_ids"], ["447"])
        self.assertEqual(result["title_ids"], ["3054"])

    def test_context_can_confirm_known_alias(self):
        result = source_identity.validar_identidade(
            "Frederick Valentich",
            "Australian pilot disappearance",
            "Frederick Valentich disappeared during a flight over Bass Strait.",
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["reason"], "known_alias_context_match")

    def test_empty_identity_is_rejected(self):
        result = source_identity.validar_identidade("", "Mary Celeste")
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "empty_identity")

    def test_missing_identity_is_rejected_as_empty(self):
        result = source_identity.validar_identidade(None, "Mary Celeste")
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "empty_identity")


if __name__ == "__main__":
    unittest.main()
