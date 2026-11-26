import unittest

import visual_director


class VisualDirectorSymbolicAssetTests(unittest.TestCase):
    def test_mission_emblem_is_replaced_for_astronaut_narration(self):
        original = {
            "scene": 4,
            "segment": "A missão Apollo 11 levava três astronautas Michael Collins.",
            "query": "documentary visual context scene",
            "must_have": [],
            "avoid": ["wrong person", "unrelated event"],
        }
        proposal = {
            "query": "NASA official mission patch Apollo 11",
            "must_have": ["apollo 11 emblem"],
            "avoid": ["wrong person", "unrelated event", "fictional patch"],
            "shot_type": "wide",
            "movement": "hold",
            "alt_queries": ["Apollo 11 mission patch close-up"],
        }

        enriched, report = visual_director.safe_scene(original, proposal)

        self.assertEqual(enriched["must_have"], ["astronaut"])
        self.assertEqual(
            enriched["query"],
            "Apollo 11 crew astronauts historical NASA archival portrait",
        )
        self.assertNotIn("patch", enriched["query"].casefold())
        self.assertNotIn("emblem", enriched["query"].casefold())
        self.assertFalse(any("patch" in query.casefold() for query in enriched["alt_queries"]))

    def test_symbolic_asset_remains_allowed_when_script_is_about_the_symbol(self):
        original = {
            "scene": 2,
            "segment": "O emblema oficial da Apollo 11 identificava a missão.",
            "query": "documentary visual context scene",
            "must_have": [],
            "avoid": [],
        }
        proposal = {
            "query": "Apollo 11 mission emblem historical photograph",
            "must_have": ["Apollo 11 emblem"],
            "avoid": [],
            "shot_type": "detail",
            "movement": "hold",
            "alt_queries": ["Apollo 11 official mission patch"],
        }

        enriched, _ = visual_director.safe_scene(original, proposal)

        self.assertIn("emblem", enriched["must_have"][0])
        self.assertIn("emblem", enriched["query"].casefold())


if __name__ == "__main__":
    unittest.main()
