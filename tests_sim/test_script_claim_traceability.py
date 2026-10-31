import unittest

from script_claim_traceability import (
    MIN_SCRIPT_CLAIM_COVERAGE,
    ScriptClaimTraceabilityError,
    enforce_script_claim_traceability,
)
from script_fallback import build_extractive_script, count_words, source_sentences


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



TOPIC = "O misterioso desaparecimento de Agatha Christie em 1926"
UNRELATED_SENTENCE = (
    "A autora publicou livros famosos e recebeu atenção dos leitores durante sua carreira."
)
TOPIC_SOURCE = " ".join([
    *([UNRELATED_SENTENCE] * 45),
    "Em dezembro de 1926, Agatha Christie desapareceu depois de deixar sua casa em Berkshire.",
    "Seu carro foi encontrado perto de Newlands Corner, em Surrey, e a polícia iniciou uma busca nacional.",
    "Investigadores, voluntários e jornais acompanharam a procura, enquanto diferentes pistas foram examinadas sem uma conclusão imediata.",
    "Onze dias depois, Agatha Christie foi localizada no Swan Hydropathic Hotel, em Harrogate, onde estava registrada como Teresa Neele.",
    "Christie nunca explicou publicamente todos os detalhes, e o episódio passou a ser conhecido como seu desaparecimento de 1926.",
    "A investigação recebeu ampla cobertura da imprensa britânica, mas nenhuma explicação definitiva foi oferecida na época.",
    "O caso permaneceu associado ao mistério sobre seu paradeiro durante os onze dias em que esteve ausente.",
])


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

    def test_topic_aware_fallback_searches_beyond_the_first_forty_sentences(self):
        result = build_extractive_script(
            TOPIC_SOURCE,
            topic=TOPIC,
            cta="Comente o que acha!",
        )

        self.assertTrue(105 <= count_words(result) <= 125)
        self.assertIn("Newlands Corner", result)
        self.assertIn("Teresa Neele", result)
        self.assertIn("desaparecimento de 1926", result)
        self.assertNotIn(UNRELATED_SENTENCE, result)

    def test_traceable_but_off_topic_script_is_replaced(self):
        result, diagnostic = enforce_script_claim_traceability(
            UNRELATED_SENTENCE,
            TOPIC_SOURCE,
            topic=TOPIC,
        )

        self.assertTrue(diagnostic["fallback_used"])
        self.assertEqual(diagnostic["fallback_reason"], "topic_mismatch")
        self.assertTrue(diagnostic["topic_relevant"])
        self.assertIn("Newlands Corner", result)
        self.assertIn("Teresa Neele", result)

    def test_topic_fallback_rejects_generic_bermuda_triangle_text_without_flight_19(self):
        generic_source = (
            "O Triângulo das Bermudas aparece em livros e relatos sobre o oceano. " * 14
        )

        result = build_extractive_script(
            generic_source,
            topic="O mistério do voo 19 e o Triângulo das Bermudas",
        )

        self.assertEqual(result, "")

    def test_topic_fallback_prefers_the_requested_flight_19_event(self):
        generic_source = (
            "O Triângulo das Bermudas aparece em livros e relatos sobre o oceano. " * 14
        )
        event_source = " ".join([
            "Em dezembro de 1945, cinco aviões da Marinha dos Estados Unidos, conhecidos como Voo 19, partiram da Flórida para um exercício de treinamento sobre o Atlântico.",
            "Durante a missão, os pilotos relataram dificuldades de navegação e incerteza sobre sua posição, enquanto as comunicações por rádio registravam tentativas de orientação.",
            "As aeronaves deveriam retornar à base, mas desapareceram durante o voo, e uma aeronave de busca enviada posteriormente também não voltou.",
            "O episódio passou a ser associado ao Triângulo das Bermudas, embora investigações tenham considerado fatores como condições meteorológicas, combustível e erros de navegação.",
            "Relatórios históricos descrevem o treinamento, as comunicações e as buscas realizadas pela Marinha, sem comprovar qualquer causa sobrenatural para os desaparecimentos.",
        ])

        result = build_extractive_script(
            generic_source + event_source,
            topic="O mistério do voo 19 e o Triângulo das Bermudas",
        )

        self.assertTrue(105 <= count_words(result) <= 125)
        self.assertIn("Voo 19", result)
        self.assertIn("1945", result)

    def test_topic_fallback_fails_closed_when_event_is_absent(self):
        with self.assertRaisesRegex(
            ScriptClaimTraceabilityError,
            "source_extract_topic_window_unavailable",
        ):
            enforce_script_claim_traceability(
                UNRELATED_SENTENCE,
                "A autora publicou livros famosos e recebeu atenção dos leitores durante sua carreira. " * 8,
                topic=TOPIC,
            )

    def test_inline_wikipedia_reference_sections_are_excluded_from_script_source(self):
        source = (
            TOPIC_SOURCE
            + " == Área do Triângulo == O artigo descreve a região. "
            + " == Ver também == "
            + ("Agatha Christie aparece em listas de livros e referências externas. " * 12)
            + " == Referências == Fonte bibliográfica sobre Agatha Christie."
        )

        sentences = source_sentences(source)
        cleaned = " ".join(sentences)

        self.assertIn("Newlands Corner", cleaned)
        self.assertIn("Teresa Neele", cleaned)
        self.assertNotIn("Área do Triângulo", cleaned)
        self.assertNotIn("Ver também", cleaned)
        self.assertNotIn("Referências", cleaned)
        self.assertNotIn("listas de livros", cleaned)
        self.assertNotIn("Fonte bibliográfica", cleaned)

    def test_required_coverage_remains_ninety_percent(self):
        self.assertEqual(MIN_SCRIPT_CLAIM_COVERAGE, 90.0)


if __name__ == "__main__":
    unittest.main()
