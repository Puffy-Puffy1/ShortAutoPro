import unittest

from subtitle_style_policy import (
    choose_group_size,
    group_timed_words,
    highlight_text,
    style_header,
    validate_grouping,
)


class SubtitleStylePolicyTests(unittest.TestCase):
    def _timed(self, words):
        return [
            {"text": word, "start": index * 100, "end": index * 100 + 90}
            for index, word in enumerate(words)
        ]

    def test_short_phrase_can_use_four_words(self):
        words = ["ele", "voltou", "para", "casa"]
        self.assertEqual(choose_group_size(words, 0), 4)

    def test_long_names_reduce_group_density(self):
        words = ["Alexander", "Krzysztofowicz", "chegou", "ontem"]
        self.assertEqual(choose_group_size(words, 0), 2)

    def test_grouping_preserves_every_word(self):
        source = self._timed(
            ["O", "caso", "mudou", "quando", "novas", "provas", "foram", "encontradas"]
        )
        groups = group_timed_words(source)
        flattened = [item["text"] for group in groups for item in group]
        self.assertEqual(flattened, [item["text"] for item in source])
        self.assertTrue(validate_grouping(groups, len(source)))

    def test_header_uses_documentary_safe_zone_and_restrained_style(self):
        header = style_header()
        self.assertIn("Style: Dynamic,DejaVu Sans,66", header)
        self.assertIn(",110,110,285,1", header)
        self.assertIn("Outline,Shadow", header)

    def test_highlight_is_soft_and_content_preserving(self):
        group = self._timed(["prova", "mudou", "o", "caso"])
        text = highlight_text(group, 1, lambda value: value)
        self.assertIn("mudou", text)
        self.assertIn("prova", text)
        self.assertIn("&H00D9E7FF&", text)


if __name__ == "__main__":
    unittest.main()
