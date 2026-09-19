import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import subtitle_style_policy
import visual_quality_policy_v1 as visual_policy
import visual_selection_runtime_bridge_v42 as runtime_bridge


class VisualDirectionReleaseIntegrityTests(unittest.TestCase):
    def setUp(self):
        for key in runtime_bridge._HISTORY:
            runtime_bridge._HISTORY[key] = []

    def test_exact_repeated_candidate_gets_strong_penalty(self):
        candidate = {
            "provider": "Pixabay",
            "tipo": "foto",
            "id": "same",
            "description": "museum painting frame",
            "score": 100,
        }
        runtime_bridge.note_selected(candidate)
        with mock.patch.dict(os.environ, {"SAP_VSE42_RUNTIME": "1", "SAP_VISUAL_QUALITY_V1": "1"}, clear=False):
            pool, _ = runtime_bridge.rerank_pool([
            candidate,
            {
                "provider": "Pixabay",
                "tipo": "foto",
                "id": "other",
                "description": "museum gallery artwork",
                "score": 90,
            },
            ], {
                "segment": "museum gallery artwork",
                "visual_query": "museum art",
                "must_have": [],
            })
        self.assertNotEqual(pool[0].get("id"), "same")

    def test_video_gets_recovery_boost_after_photo_streak(self):
        runtime_bridge._HISTORY["types"] = ["photo", "photo", "photo"]
        runtime_bridge._HISTORY["providers"] = ["pixabay"] * 3
        runtime_bridge._HISTORY["groups"] = ["stock"] * 3
        runtime_bridge._HISTORY["keys"] = ["a", "b", "c"]
        runtime_bridge._HISTORY["semantic_signatures"] = []
        photo = {
            "provider": "Pixabay", "tipo": "foto", "id": "p",
            "description": "museum interior architecture", "score": 100,
        }
        video = {
            "provider": "Pixabay", "tipo": "video", "id": "v",
            "description": "museum interior architecture", "score": 100,
        }
        with mock.patch.dict(os.environ, {"SAP_VSE42_RUNTIME": "1", "SAP_VISUAL_QUALITY_V1": "1"}, clear=False):
            pool, _ = runtime_bridge.rerank_pool([photo, video], {
                "segment": "museum interior architecture",
                "visual_query": "museum interior architecture",
                "must_have": [],
            })
        self.assertEqual(pool[0].get("id"), "v")

    def test_concrete_scene_penalizes_generic_investigation_asset(self):
        scene = {
            "segment": "The investigators found a book with a handwritten phone number.",
            "visual_query": "old book handwritten phone number",
        }
        specific = {
            "provider": "Pixabay",
            "description": "old book paper handwritten telephone number",
        }
        generic = {
            "provider": "Pixabay",
            "description": "detective investigation office magnifying glass",
        }
        self.assertGreater(
            visual_policy.evaluate(specific, scene)["adjustment"],
            visual_policy.evaluate(generic, scene)["adjustment"],
        )
        self.assertIn(
            "CONCRETE_CONCEPT_MISMATCH",
            visual_policy.evaluate(generic, scene)["reasons"],
        )

    def test_caption_grouping_avoids_dangling_connector_when_possible(self):
        words = [
            {"text": "Testes"}, {"text": "indicaram"}, {"text": "que"},
            {"text": "ele"}, {"text": "seria"}, {"text": "o"},
            {"text": "homem"}, {"text": "procurado"},
        ]
        groups = subtitle_style_policy.group_timed_words(words)
        endings = {
            subtitle_style_policy._word_norm(group[-1]["text"])
            for group in groups[:-1] if group
        }
        self.assertFalse(endings & subtitle_style_policy.DANGLING_END_WORDS)
        self.assertEqual(
            [w for g in groups for w in g],
            words,
        )

    def test_professional_caption_mobile_size_is_larger(self):
        text = Path("professional_caption_director.py").read_text(encoding="utf-8")
        self.assertIn('"font_size": 69', text)
        self.assertIn('"margin_v": 330', text)
        self.assertIn('PRO_CAPTION_1.1', text)

    def test_caption_layout_uses_higher_baseline(self):
        text = Path("caption_layout_guard.py").read_text(encoding="utf-8")
        self.assertIn("margin=335", text)
        self.assertIn("margin=420", text)

    def test_v6_persists_topic_fingerprint(self):
        text = Path("v6_professional.py").read_text(encoding="utf-8")
        self.assertIn("SHORTAUTOPRO_RENDER_IDENTITY_V1", text)
        self.assertIn("topic_sha256", text)
        self.assertIn("V6 PROFESSIONAL RENDERER 2.3", text)

    def test_release_gate_blocks_topic_identity_mismatch(self):
        text = Path("release_gate.py").read_text(encoding="utf-8")
        self.assertIn("render_topic_identity_mismatch", text)
        self.assertIn("SAP_ARTIFACT_IDENTITY_ENFORCE", text)
        self.assertIn("RELEASE_GATE_1.4_ARTIFACT_IDENTITY", text)

    def test_manifest_requires_render_identity_match(self):
        text = Path("production_manifest.py").read_text(encoding="utf-8")
        self.assertIn('"render_identity_match": render_identity_match', text)
        self.assertIn('"artifact_identity": {', text)


if __name__ == "__main__":
    unittest.main()
