import unittest

from subtitle_alignment import align_word_timings, normalize_word


class SubtitleAlignmentTests(unittest.TestCase):
    def test_normalization_handles_accents_and_punctuation(self):
        self.assertEqual(normalize_word("Investigação!"), "investigacao")
        self.assertEqual(normalize_word("MH-370"), "mh370")

    def test_alignment_survives_whisper_insertion(self):
        original = ["o", "avião", "desapareceu", "sem", "deixar", "rastros"]
        whisper = [
            {"text": "o", "start": 0, "end": 120},
            {"text": "avião", "start": 120, "end": 300},
            {"text": "realmente", "start": 300, "end": 390},
            {"text": "desapareceu", "start": 390, "end": 650},
            {"text": "sem", "start": 650, "end": 760},
            {"text": "deixar", "start": 760, "end": 900},
            {"text": "rastros", "start": 900, "end": 1100},
        ]
        timed, method, ratio = align_word_timings(original, whisper, 0, 1100)
        self.assertEqual(len(timed), len(original))
        self.assertEqual(method, "CONTENT_ALIGNMENT")
        self.assertGreater(ratio, 0.70)
        self.assertLess(timed[1]["start"], timed[2]["start"])
        self.assertLess(timed[2]["start"], timed[3]["start"])
        self.assertEqual(timed[-1]["end"], 1100)

    def test_alignment_survives_missing_whisper_word(self):
        original = ["a", "equipe", "iniciou", "uma", "busca", "imediata"]
        whisper = [
            {"text": "a", "start": 0, "end": 100},
            {"text": "equipe", "start": 100, "end": 260},
            {"text": "iniciou", "start": 260, "end": 430},
            {"text": "busca", "start": 600, "end": 780},
            {"text": "imediata", "start": 780, "end": 1000},
        ]
        timed, method, ratio = align_word_timings(original, whisper, 0, 1000)
        self.assertEqual(method, "CONTENT_ALIGNMENT")
        self.assertGreater(ratio, 0.70)
        self.assertEqual(len(timed), 6)
        for previous, current in zip(timed, timed[1:]):
            self.assertLessEqual(previous["start"], current["start"])
            self.assertGreater(previous["end"], previous["start"])

    def test_low_similarity_uses_safe_positional_fallback(self):
        original = ["palavra", "completamente", "diferente", "aqui"]
        whisper = [
            {"text": "foo", "start": 0, "end": 200},
            {"text": "bar", "start": 200, "end": 400},
            {"text": "baz", "start": 400, "end": 600},
            {"text": "qux", "start": 600, "end": 800},
        ]
        timed, method, ratio = align_word_timings(original, whisper, 0, 800)
        self.assertEqual(method, "POSITIONAL_FALLBACK")
        self.assertEqual(len(timed), 4)
        self.assertLess(ratio, 0.20)
        self.assertEqual(timed[0]["start"], 0)
        self.assertEqual(timed[-1]["end"], 800)


if __name__ == "__main__":
    unittest.main()
