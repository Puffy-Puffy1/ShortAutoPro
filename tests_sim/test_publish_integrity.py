import math
import unittest

from publish_integrity_gate import audit, numeric_tokens


PUBLISH_TEXT = """TÍTULO:
O mistério por trás do voo MH370 desaparecido

DESCRIÇÃO:
O desaparecimento do voo MH370 continua sendo um dos maiores mistérios da aviação. Qual é a sua teoria sobre o caso?

HASHTAGS:
#Shorts #MH370 #Aviação #Mistério #FatosReais

COMENTÁRIO FIXADO:
Qual é a sua teoria?
"""

PUBLISH_JSON = {
    "chosen_title": "O mistério por trás do voo MH370 desaparecido",
    "description": (
        "O desaparecimento do voo MH370 continua sendo um dos maiores "
        "mistérios da aviação. Qual é a sua teoria sobre o caso?"
    ),
    "hashtags": ["#Shorts", "#MH370", "#Aviação", "#Mistério", "#FatosReais"],
    "publish_score": 86,
}

SCRIPT = "O voo MH370 desapareceu durante uma viagem e gerou uma investigação internacional."
SOURCE = "A fonte factual descreve o voo MH370 e a investigação sobre o desaparecimento."
TOPIC = "Voo MH370"


class PublishIntegrityTests(unittest.TestCase):
    def test_valid_publish_contract_passes(self):
        result = audit(PUBLISH_TEXT, PUBLISH_JSON, SCRIPT, SOURCE, TOPIC)
        self.assertEqual(result["status"], "PASS", result["critical"])
        self.assertNotIn("370", result["new_numbers"])

    def test_missing_source_blocks(self):
        result = audit(PUBLISH_TEXT, PUBLISH_JSON, SCRIPT, "", TOPIC)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("source_missing_or_empty", result["critical"])

    def test_json_txt_title_mismatch_blocks(self):
        payload = dict(PUBLISH_JSON)
        payload["chosen_title"] = "Outro título completamente diferente"
        result = audit(PUBLISH_TEXT, payload, SCRIPT, SOURCE, TOPIC)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("publish_txt_json_title_mismatch", result["critical"])

    def test_low_publish_score_blocks(self):
        payload = dict(PUBLISH_JSON)
        payload["publish_score"] = 59
        result = audit(PUBLISH_TEXT, payload, SCRIPT, SOURCE, TOPIC)
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(
            any(x.startswith("publish_score_low=") for x in result["critical"])
        )

    def test_nonfinite_publish_score_blocks(self):
        payload = dict(PUBLISH_JSON)
        payload["publish_score"] = math.nan
        result = audit(PUBLISH_TEXT, payload, SCRIPT, SOURCE, TOPIC)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("publish_score_invalid", result["critical"])

    def test_credit_url_fragment_is_not_counted_as_hashtag(self):
        text = (
            PUBLISH_TEXT
            + "\nCRÉDITOS DE MÍDIA:\n"
            + "https://commons.wikimedia.org/wiki/File:Example.jpg#Licensing\n"
        )
        result = audit(text, PUBLISH_JSON, SCRIPT, SOURCE, TOPIC)
        self.assertEqual(result["status"], "PASS", result["critical"])
        self.assertEqual(len(result["hashtags"]), 5)

    def test_unsupported_alphanumeric_number_blocks(self):
        text = PUBLISH_TEXT.replace("#MH370", "#MH371")
        payload = dict(PUBLISH_JSON)
        payload["hashtags"] = ["#Shorts", "#MH371", "#Aviação", "#Mistério", "#FatosReais"]
        result = audit(text, payload, SCRIPT, SOURCE, TOPIC)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("unsupported_numbers=371", result["critical"])

    def test_written_and_numeric_thousands_are_equivalent(self):
        self.assertEqual(numeric_tokens("duzentos mil dólares"), numeric_tokens("200 mil dólares"))
        self.assertEqual(numeric_tokens("duzentos e cinquenta mil reais"), numeric_tokens("250 mil reais"))

    def test_equivalent_written_quantity_passes_publish_integrity(self):
        title = "Como D. B. Cooper sumiu com 200 mil dólares?"
        description = (
            "Em 1971, D. B. Cooper recebeu 200 mil dólares de resgate ao sequestrar "
            "um Boeing 727. O destino dele continua desconhecido. Qual é sua teoria?"
        )
        text = (
            "TÍTULO:\n" + title + "\n\nDESCRIÇÃO:\n" + description
            + "\n\nHASHTAGS:\n#Shorts #DBCooper #Aviação #Mistério #HistóriaReal\n"
        )
        payload = {
            "chosen_title": title,
            "description": description,
            "hashtags": ["#Shorts", "#DBCooper", "#Aviação", "#Mistério", "#HistóriaReal"],
            "publish_score": 90,
        }
        script = "Em 1971, D. B. Cooper recebeu duzentos mil dólares de resgate e sequestrou um Boeing 727."
        source = "A fonte descreve o resgate de duzentos mil dólares no caso D. B. Cooper."
        result = audit(text, payload, script, source, "D. B. Cooper")
        self.assertEqual(result["status"], "PASS", result["critical"])
        self.assertEqual(result["new_numbers"], [])

    def test_different_written_quantity_remains_blocked(self):
        self.assertEqual(numeric_tokens("duzentos mil dólares"), {"200000"})
        self.assertEqual(numeric_tokens("300 mil dólares"), {"300000"})

    def test_exact_decade_anchor_authorizes_common_shorthand(self):
        tokens = numeric_tokens("O caso começou na década de 1960 e continuou até 1974.")
        self.assertIn("1960", tokens)
        self.assertIn("60", tokens)
        self.assertIn("1974", tokens)

    def test_arbitrary_year_does_not_authorize_decade_shorthand(self):
        tokens = numeric_tokens("O caso começou em 1968.")
        self.assertIn("1968", tokens)
        self.assertNotIn("68", tokens)
        self.assertNotIn("60", tokens)


if __name__ == "__main__":
    unittest.main()
