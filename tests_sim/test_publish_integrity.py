import unittest

from publish_integrity_gate import audit


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


if __name__ == "__main__":
    unittest.main()
