import unittest

from subtitle_style_policy import group_timed_words, validate_grouping


def timed(words):
    return [
        {"text": word, "start": index * 100, "end": (index + 1) * 100}
        for index, word in enumerate(words)
    ]


class SubtitleStylePolicyRegressionTests(unittest.TestCase):
    def test_rebalance_never_creates_five_word_group(self):
        # The first group ends in a dangling connector while the following
        # group is already at the 4-word policy maximum.
        words = ["eles", "fugiram", "para", "a", "ilha", "sob", "névoa", "fria"]
        groups = group_timed_words(timed(words))

        self.assertTrue(validate_grouping(groups, len(words)))
        self.assertEqual(
            [item["text"] for group in groups for item in group],
            words,
        )
        self.assertTrue(all(2 <= len(group) <= 4 for group in groups[:-1]))


if __name__ == "__main__":
    unittest.main()
