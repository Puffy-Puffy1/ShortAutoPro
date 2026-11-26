import unittest

from scene_coverage import scenes_cover_script


class SceneCoverageTests(unittest.TestCase):
    def setUp(self):
        self.script = "Apollo 11 chegou à Lua em 1969. Armstrong saiu do módulo lunar."

    def test_accepts_complete_ordered_scene_segments(self):
        scenes = [
            {"segment": "Apollo 11 chegou à Lua em 1969."},
            {"segment": "Armstrong saiu do módulo lunar."},
        ]
        self.assertTrue(scenes_cover_script(scenes, self.script))

    def test_rejects_duplicated_scene_and_missing_words(self):
        scenes = [
            {"segment": "Apollo 11 chegou à Lua em 1969."},
            {"segment": "Apollo 11 chegou à Lua em 1969."},
        ]
        self.assertFalse(scenes_cover_script(scenes, self.script))

    def test_rejects_reordered_scene_segments(self):
        scenes = [
            {"segment": "Armstrong saiu do módulo lunar."},
            {"segment": "Apollo 11 chegou à Lua em 1969."},
        ]
        self.assertFalse(scenes_cover_script(scenes, self.script))

    def test_rejects_invented_or_omitted_words(self):
        scenes = [
            {"segment": "Apollo 11 chegou à Lua em 1969."},
            {"segment": "Armstrong saiu do módulo lunar e acenou."},
        ]
        self.assertFalse(scenes_cover_script(scenes, self.script))

    def test_accepts_case_and_punctuation_differences(self):
        scenes = [
            {"segment": "APOLLO 11 chegou à Lua em 1969"},
            {"segment": "Armstrong saiu do módulo lunar"},
        ]
        self.assertTrue(scenes_cover_script(scenes, self.script))


if __name__ == "__main__":
    unittest.main()
