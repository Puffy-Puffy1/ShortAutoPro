#!/usr/bin/env python3
import unittest

from script_fallback import build_extractive_long_script, count_words, source_sentences


SOURCE_SENTENCES = [
    "O programa Apollo foi desenvolvido pela NASA durante a corrida espacial entre os Estados Unidos e a União Soviética.",
    "O programa Apollo recebeu prioridade nacional depois do discurso presidencial feito no início da década de 1960.",
    "O programa Apollo reuniu engenheiros, cientistas, pilotos e equipes de controle em diferentes centros de pesquisa.",
    "O programa Apollo utilizou os foguetes Saturno para transportar as naves e seus equipamentos até a órbita terrestre.",
    "O programa Apollo passou por missões de teste antes de tentar realizar um pouso tripulado na superfície lunar.",
    "O programa Apollo enfrentou riscos técnicos relacionados à navegação, aos sistemas de comunicação e ao suporte de vida.",
    "O programa Apollo 1 terminou em tragédia durante um teste em solo realizado antes do primeiro voo tripulado.",
    "O programa Apollo passou por mudanças de segurança depois da investigação sobre o acidente da missão Apollo 1.",
    "O programa Apollo 7 realizou um voo tripulado em órbita terrestre e avaliou os sistemas da espaçonave.",
    "O programa Apollo 8 levou astronautas até a órbita da Lua e permitiu observar regiões que não eram vistas diretamente da Terra.",
    "O programa Apollo 9 testou em órbita terrestre os principais procedimentos do módulo lunar.",
    "O programa Apollo 10 realizou um ensaio geral da descida e aproximou o módulo lunar da superfície.",
    "O programa Apollo 11 realizou o primeiro pouso tripulado na Lua em julho de 1969.",
    "O programa Apollo 12 pousou em outra região lunar e demonstrou maior precisão na escolha do local.",
    "O programa Apollo 13 sofreu uma falha grave durante a viagem e precisou adaptar seus procedimentos para retornar à Terra.",
    "O programa Apollo 14 voltou a realizar um pouso lunar depois da missão interrompida da Apollo 13.",
    "O programa Apollo 15 ampliou as atividades na superfície com o uso de um veículo explorador lunar.",
    "O programa Apollo 16 pesquisou formações geológicas nas terras altas da Lua.",
    "O programa Apollo 17 encerrou a sequência de pousos tripulados do programa em dezembro de 1972.",
    "O programa Apollo deixou equipamentos científicos na Lua que contribuíram para pesquisas posteriores sobre o ambiente lunar.",
    "O programa Apollo também produziu dados técnicos utilizados no desenvolvimento de projetos espaciais posteriores.",
    "O programa Apollo permanece como um dos principais marcos da exploração espacial tripulada no século vinte.",
]


class LongFormFallbackTests(unittest.TestCase):
    def test_builds_ordered_source_only_narration_without_repeating_sentences(self):
        source = " ".join(SOURCE_SENTENCES)
        script = build_extractive_long_script(
            source,
            min_words=200,
            max_words=260,
            target_words=230,
            topic="Apollo",
        )
        self.assertTrue(script)
        self.assertGreaterEqual(count_words(script), 200)
        self.assertLessEqual(count_words(script), 260)
        self.assertTrue(script.endswith("Comente o que achou!"))
        factual = script.removesuffix("Comente o que achou!").strip()
        chosen = source_sentences(factual)
        self.assertEqual(len(chosen), len(set(chosen)))
        self.assertTrue(all(sentence in SOURCE_SENTENCES for sentence in chosen))

    def test_refuses_to_invent_or_pad_when_source_is_too_short(self):
        source = " ".join(SOURCE_SENTENCES[:3])
        self.assertEqual(
            build_extractive_long_script(
                source, min_words=200, max_words=260, topic="Apollo"
            ),
            "",
        )

    def test_refuses_an_unrelated_source(self):
        source = " ".join(
            sentence.replace("Apollo", "Marte").replace("lunar", "marciano")
            for sentence in SOURCE_SENTENCES
        )
        self.assertEqual(
            build_extractive_long_script(
                source, min_words=200, max_words=260, topic="Apollo"
            ),
            "",
        )


if __name__ == "__main__":
    unittest.main()
