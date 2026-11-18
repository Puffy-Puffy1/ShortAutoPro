#!/usr/bin/env python3
import os
import unittest
from unittest.mock import patch

from studio_config import apply_studio_config, build_studio_config


class StudioConfigTests(unittest.TestCase):
    def test_short_profile_keeps_vertical_short_defaults(self):
        config = build_studio_config("short", 45, theme="ciência")
        self.assertEqual(config["orientation"], "portrait")
        self.assertEqual((config["width"], config["height"], config["fps"]), (1080, 1920, 30))
        self.assertEqual(config["scene_count"], 12)
        self.assertEqual((config["script_min_words"], config["script_max_words"]), (105, 125))

    def test_long_profiles_are_landscape_and_scale_scene_and_script_budget(self):
        ten = build_studio_config("long", 10, theme="história")
        twenty = build_studio_config("long", 20, theme="história")
        self.assertEqual(ten["orientation"], "landscape")
        self.assertEqual((ten["width"], ten["height"], ten["fps"]), (1280, 720, 24))
        self.assertEqual(ten["scene_count"], 30)
        self.assertEqual(twenty["scene_count"], 60)
        self.assertGreater(twenty["script_min_words"], ten["script_min_words"])
        self.assertGreater(twenty["script_max_output_tokens"], ten["script_max_output_tokens"])

    def test_unsupported_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            build_studio_config("long", 8)
        with self.assertRaises(ValueError):
            build_studio_config("short", 90)

    def test_topic_and_theme_are_mutually_exclusive(self):
        with self.assertRaises(ValueError):
            build_studio_config("short", 45, theme="ciência", exact_topic="Buraco negro")

    def test_free_mode_removes_cloud_key_after_config_is_loaded(self):
        config = build_studio_config("short", 30)
        with patch.dict(os.environ, {"GEMINI_API_KEY": "must-not-leak"}, clear=False):
            apply_studio_config(config)
            self.assertNotIn("GEMINI_API_KEY", os.environ)
            self.assertEqual(os.environ["SAP_FREE_MODE"], "1")
            self.assertEqual(os.environ["SAP_STUDIO_FORMAT"], "short")

    def test_explicit_cloud_mode_preserves_existing_key(self):
        config = build_studio_config("long", 10, cloud_ai=True)
        with patch.dict(os.environ, {"GEMINI_API_KEY": "provided"}, clear=False):
            apply_studio_config(config)
            self.assertEqual(os.environ["GEMINI_API_KEY"], "provided")
            self.assertEqual(os.environ["SAP_FREE_MODE"], "0")


if __name__ == "__main__":
    unittest.main()
