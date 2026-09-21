import unittest

from visual_continuity_engine import (
    choose_repair_scene,
    quality_band,
    selected_pair,
)


def _scene(subject="subject", location="room", era="2020", segment="event", shot="medium"):
    return {
        "scene": 1,
        "main_subject": subject,
        "location": location,
        "era": era,
        "segment": segment,
        "shot_type": shot,
    }


def _vi(description, provider="Wikimedia"):
    return {
        "winner": {
            "descricao": description,
            "fonte": provider,
            "semantic": 90,
        }
    }


def _score(value):
    return {"visual_score": value}


def _asset(sha, visual_hash):
    return {"sha256": sha, "visual_hash": visual_hash}


class Stage6ContinuityContractTests(unittest.TestCase):
    def test_quality_bands_match_production_contract(self):
        self.assertEqual(quality_band(0), "FAIL")
        self.assertEqual(quality_band(49.9), "FAIL")
        self.assertEqual(quality_band(50), "REVIEW")
        self.assertEqual(quality_band(64.9), "REVIEW")
        self.assertEqual(quality_band(65), "ACCEPTABLE")
        self.assertEqual(quality_band(80), "GOOD")
        self.assertEqual(quality_band(90), "EXCELLENT")

    def test_selected_continuity_penalizes_adjacent_duplicate(self):
        prev = _scene()
        cur = _scene(segment="event continues", shot="close_up")
        unique_score, _, unique_issues = selected_pair(
            prev,
            cur,
            _vi("subject in room during event"),
            _vi("subject in room during event continues"),
            _score(90),
            _score(90),
            _asset("a", "0" * 256),
            _asset("b", "01" * 128),
            set(),
            1,
            2,
        )
        duplicate_score, _, duplicate_issues = selected_pair(
            prev,
            cur,
            _vi("subject in room during event"),
            _vi("subject in room during event continues"),
            _score(90),
            _score(90),
            _asset("same", "0" * 256),
            _asset("same", "0" * 256),
            set(),
            1,
            2,
        )
        self.assertNotIn("exact_adjacent_duplicate", unique_issues)
        self.assertIn("exact_adjacent_duplicate", duplicate_issues)
        self.assertLess(duplicate_score, unique_score)

    def test_repair_choice_is_surgical_and_prefers_weaker_scene(self):
        chosen = choose_repair_scene(
            4,
            5,
            _score(60),
            _score(88),
            ["selected_sequence_disconnect"],
        )
        self.assertEqual(chosen, 4)

        duplicate_chosen = choose_repair_scene(
            4,
            5,
            _score(60),
            _score(88),
            ["exact_adjacent_duplicate"],
        )
        self.assertEqual(duplicate_chosen, 5)


if __name__ == "__main__":
    unittest.main()
