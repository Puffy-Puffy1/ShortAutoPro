import json
import tempfile
import unittest
from pathlib import Path

import shortauto_asset_library as assets
import shortauto_director_ai as director
import shortauto_repair_engine as repair


class DirectorAIUnitTests(unittest.TestCase):
    def test_semantic_provenance_maps_supported_scene_without_rewrite(self):
        script = "Three men escaped Alcatraz in 1962. They used dummy heads made from paper mache."
        source = "Three inmates escaped Alcatraz in 1962. Dummy heads were made from paper mache."
        scenes = [
            {"segment": "Three men escaped Alcatraz in 1962."},
            {"segment": "They used dummy heads made from paper mache."},
        ]
        report = director.semantic_provenance(scenes, script, source)
        self.assertEqual(report["coverage"], 100.0)
        self.assertEqual(report["records"][0]["generated_text"], scenes[0]["segment"])
        self.assertTrue(all(x["supported"] for x in report["records"]))

    def test_visual_intent_preserves_scene_contract(self):
        scenes = [{
            "segment": "A file was found.",
            "narrative_role": "evidence",
            "emotion": "mystery",
            "shot_type": "document",
            "movement": "hold",
            "main_subject": "case file",
            "location": "archive",
            "era": "1962",
            "must_have": ["case file", "paper"],
            "avoid": ["modern laptop"],
            "query": "old case file paper archive",
        }]
        intent = director.visual_intents(scenes, "", "")[0]
        self.assertEqual(intent["scene_type"], "evidence")
        self.assertEqual(intent["camera"], "document")
        self.assertEqual(intent["must_have"], ["case file", "paper"])
        self.assertIn("modern laptop", intent["avoid"])

    def test_visual_memory_detects_same_signature_inside_video(self):
        intents = [
            {"scene": 1, "subject": "beach", "location": "Adelaide", "camera": "wide", "query": "empty beach"},
            {"scene": 2, "subject": "beach", "location": "Adelaide", "camera": "wide", "query": "empty beach"},
        ]
        memory = director.visual_memory(intents)
        self.assertEqual(memory["duplicate_pairs"], [[1, 2]])
        self.assertLess(memory["diversity_score"], 100)

    def test_scene_importance_and_first_frame_prefer_strong_opening(self):
        scenes = [
            {"segment": "A shocking clue appeared.", "narrative_role": "hook", "must_have": ["clue", "document"]},
            {"segment": "Context followed.", "narrative_role": "context", "must_have": []},
        ]
        importance = director.scene_importance(scenes)
        intents = [
            {"scene": 1, "camera": "detail", "subject": "clue", "must_have": ["clue", "document"]},
            {"scene": 2, "camera": "wide", "subject": "room", "must_have": []},
        ]
        frame = director.first_frame_plan(intents, importance)
        self.assertEqual(frame["recommended_scene"], 1)
        self.assertGreater(frame["first_frame_score"], 80)

    def test_knowledge_graph_connects_scene_entities(self):
        intents = [{
            "scene": 1, "subject": "Somerton Man", "location": "Adelaide",
            "period": "1948", "must_have": ["suitcase", "Rubaiyat"],
        }]
        graph = director.knowledge_graph(intents, "Somerton Man", "In 1948 the case began.")
        relations = {edge["relation"] for edge in graph["edges"]}
        self.assertIn("has_subject", relations)
        self.assertIn("has_location", relations)
        self.assertIn("requires", relations)


class AssetLibraryTests(unittest.TestCase):
    def test_library_requires_media_master_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = (assets.BASE, assets.R, assets.STATE, assets.REPORTS)
            try:
                assets.BASE = root
                assets.R = root / "roteiros"
                assets.STATE = root / ".sap_state" / "asset_library.json"
                assets.REPORTS = root / "reports" / "assets"
                assets.R.mkdir(parents=True)
                (assets.R / "media_quality_x.json").write_text(json.dumps({"status": "BLOCK"}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    assets.index_short("x")
            finally:
                assets.BASE, assets.R, assets.STATE, assets.REPORTS = old

    def test_asset_index_is_idempotent_per_short(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = (assets.BASE, assets.R, assets.STATE, assets.REPORTS)
            try:
                assets.BASE = root
                assets.R = root / "roteiros"
                assets.STATE = root / ".sap_state" / "asset_library.json"
                assets.REPORTS = root / "reports" / "assets"
                assets.R.mkdir(parents=True)
                media = {
                    "status": "PASS",
                    "assets": [{
                        "file": "scene_01.jpg", "path": "/tmp/scene_01.jpg",
                        "width": 1920, "height": 1080, "duration": 0,
                        "sha256": "abc123", "visual_hash": "0101",
                    }],
                }
                scene = {"scenes": [{
                    "scene": 1, "must_have": ["document"], "location": "archive",
                    "era": "1962", "shot_type": "detail",
                }]}
                (assets.R / "media_quality_x.json").write_text(json.dumps(media), encoding="utf-8")
                (assets.R / "scene_map_x.json").write_text(json.dumps(scene), encoding="utf-8")
                assets.index_short("x")
                assets.index_short("x")
                library = json.loads(assets.STATE.read_text(encoding="utf-8"))
                self.assertEqual(library["assets"][0]["used_count"], 1)
                self.assertEqual(library["assets"][0]["short_ids"], ["x"])
            finally:
                assets.BASE, assets.R, assets.STATE, assets.REPORTS = old


class RepairEngineTests(unittest.TestCase):
    def test_plan_is_evidence_driven_and_keeps_safety_policy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = (repair.BASE, repair.R, repair.M, repair.E, repair.OUT)
            try:
                repair.BASE = root
                repair.R = root / "roteiros"
                repair.M = root / "manifests"
                repair.E = root / "reports" / "evolution"
                repair.OUT = root / "reports" / "repair"
                repair.R.mkdir(parents=True)
                repair.M.mkdir(parents=True)
                repair.E.mkdir(parents=True)
                (repair.R / "media_quality_x.json").write_text(
                    json.dumps({"status": "BLOCK", "critical": ["media_count=4"]}), encoding="utf-8"
                )
                (repair.R / "retention_x.json").write_text(
                    json.dumps({"retention_score": 72, "threshold": 78}), encoding="utf-8"
                )
                plan = repair.plan("x")
                ids = {item["id"] for item in plan["actions"]}
                self.assertIn("media_reacquire", ids)
                self.assertIn("retention_repair", ids)
                self.assertTrue(plan["policy"]["strict_must_can_never_be_relaxed"])
                self.assertTrue(plan["policy"]["semantic_text_can_never_be_rewritten"])
            finally:
                repair.BASE, repair.R, repair.M, repair.E, repair.OUT = old


if __name__ == "__main__":
    unittest.main()
