import unittest

from publish_pack import normalize_hashtag, validate_payload


class PublishPackTests(unittest.TestCase):
    def setUp(self):
        self.topic = "Voo MH370"
        self.hook = "O avião desapareceu e deixou perguntas sem resposta."
        self.script = (
            "O voo MH370 desapareceu durante uma viagem e gerou uma investigação "
            "internacional sobre o destino do avião e das pessoas a bordo."
        )

    def valid_payload(self):
        return {
            "titles": [
                "O mistério por trás do voo MH370 desaparecido",
                "MH370: o que aconteceu com o avião perdido?",
                "O desaparecimento do MH370 ainda intriga investigadores",
            ],
            "description": (
                "O desaparecimento do voo MH370 continua sendo um dos maiores "
                "mistérios da aviação. Qual é a sua teoria sobre o caso?"
            ),
            "hashtags": [
                "#Shorts",
                "#MH370",
                "#Aviação",
                "#Mistério",
                "#FatosReais",
            ],
            "pinned_comment": "Qual é a sua teoria sobre o desaparecimento do MH370?",
        }

    def test_valid_payload_passes(self):
        pack = validate_payload(
            self.valid_payload(), self.topic, self.hook, self.script
        )
        self.assertEqual(len(pack["titles"]), 3)
        self.assertEqual(len(pack["hashtags"]), 5)
        self.assertGreaterEqual(pack["publish_score"], 60)

    def test_duplicate_hashtags_fail_closed(self):
        payload = self.valid_payload()
        payload["hashtags"] = [
            "#Shorts",
            "#MH370",
            "#mh370",
            "#Mistério",
            "#FatosReais",
        ]
        with self.assertRaises(ValueError):
            validate_payload(payload, self.topic, self.hook, self.script)

    def test_low_quality_titles_fail_closed(self):
        payload = self.valid_payload()
        payload["titles"] = [
            "100% COMPROVADO!!! Você não vai acreditar nisso",
            "PROVA DEFINITIVA!!! Isso vai te chocar agora",
            "A VERDADE ABSOLUTA!!! Chocante demais mesmo",
        ]
        with self.assertRaises(ValueError):
            validate_payload(payload, self.topic, self.hook, self.script)

    def test_hashtag_normalizer_rejects_punctuation(self):
        self.assertEqual(normalize_hashtag(" #MH370 "), "#MH370")
        self.assertEqual(normalize_hashtag("#foo/bar"), "")


if __name__ == "__main__":
    unittest.main()
