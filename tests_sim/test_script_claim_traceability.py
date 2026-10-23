import unittest

from script_claim_traceability import (
    MIN_SCRIPT_CLAIM_COVERAGE,
    ScriptClaimTraceabilityError,
    enforce_script_claim_traceability,
)
from script_fallback import count_words


SOURCE = (
    "Em 1959, um grupo de nove esquiadores iniciou uma expedição de inverno nos montes Urais, na União Soviética. "
    "Todos os integrantes possuíam experiência em excursões de esqui e expedições em montanhas. "
    "O grupo viajou de trem para Ivdel e chegou à cidade em 25 de janeiro. "
    "Depois, eles tomaram um caminhão para Vizhai e começaram a marcha em direção ao monte Otorten. "
    "No dia seguinte, Yuri Yudin voltou devido a problemas de saúde. "
    "Diários e câmeras encontrados no acampamento ajudaram a rastrear a rota dos viajantes. "
    "Em 31 de janeiro, os integrantes chegaram à beira de um morro e prepararam-se para escalá-lo. "
    "As equipes de busca encontraram o acampamento abandonado em fevereiro. "
    "As investigações posteriores reuniram registros dos viajantes, das condições meteorológicas e dos locais de busca. "
    "A cronologia exata dos acontecimentos permaneceu incerta enquanto as equipes examinavam os vestígios."
)


class ScriptClaimTraceabilityTests(unittest.TestCase):
    def test_traceable_script_is_preserved(self):
        script = (
            "Todos os integrantes possuíam experiência em excursões de esqui e expedições em montanhas. "
            "O grupo viajou de trem para Ivdel e chegou à cidade em 25 de janeiro. "
            "Comente o que acha!"
        )

        result, diagnostic = enforce_script_claim_traceability(script, SOURCE)

        self.assertEqual(result, script)
        self.assertFalse(diagnostic["fallback_used"])
        self.assertGreaterEqual(diagnostic["coverage"], MIN_SCRIPT_CLAIM_COVERAGE)

    def test_low_coverage_script_uses_a_source_extract_that_passes_the_same_checker(self):
        script = (
            "A expedição terminou em circunstâncias inexplicáveis. "
            "Teorias divergentes continuam sem comprovação e especialistas discordam sobre o ocorrido. "
            "Comente o que acha!"
        )

        result, diagnostic = enforce_script_claim_traceability(script, SOURCE)

        self.assertTrue(diagnostic["fallback_used"])
        self.assertLess(diagnostic["original_coverage"], MIN_SCRIPT_CLAIM_COVERAGE)
        self.assertGreaterEqual(diagnostic["coverage"], MIN_SCRIPT_CLAIM_COVERAGE)
        self.assertEqual(diagnostic["unsupported_sentences"], 0)
        self.assertTrue(105 <= count_words(result) <= 125)
        self.assertIn("Comente o que acha!", result)
        self.assertNotEqual(result, script)

    def test_blocks_when_source_has_no_extractable_word_window(self):
        with self.assertRaisesRegex(
            ScriptClaimTraceabilityError,
            "source_extract_window_unavailable",
        ):
            enforce_script_claim_traceability(
                "Uma história misteriosa ainda levanta muitas perguntas. Comente o que acha!",
                "O grupo chegou ao acampamento ao anoitecer.",
            )

    def test_required_coverage_remains_ninety_percent(self):
        self.assertEqual(MIN_SCRIPT_CLAIM_COVERAGE, 90.0)


if __name__ == "__main__":
    unittest.main()
