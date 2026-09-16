import os
import unittest
from pathlib import Path
from unittest import mock

import visual_quality_policy_v1 as policy
import visual_selection_runtime_bridge_v42 as bridge


class VisualQualityPolicyV1Tests(unittest.TestCase):
    def setUp(self):
        for values in bridge._HISTORY.values():
            values.clear()

    def test_candidate_query_is_not_asset_evidence(self):
        candidate = {
            "query": "phone call mother airport",
            "search_query": "urgent phone call",
            "url": "https://www.pexels.com/video/12345/",
            "descricao": "https://www.pexels.com/video/12345/ John Smith",
        }
        text = policy.candidate_evidence_text(candidate).casefold()
        self.assertNotIn("phone call mother", text)
        self.assertNotIn("urgent phone call", text)
        self.assertIn("john smith", text)

    def test_phone_asset_beats_unrelated_ocean_stock(self):
        scene = {
            "segmento": "Lars ligou desesperado para a mãe pelo telefone.",
            "visual_query": "man urgent phone call mother",
        }
        ocean = {
            "provider": "Pixabay",
            "type": "photo",
            "id": "ocean",
            "descricao": "blue ocean water waves sea",
            "score": 120,
        }
        phone = {
            "provider": "Pixabay",
            "type": "photo",
            "id": "phone",
            "descricao": "man using smartphone making urgent phone call",
            "score": 60,
        }

        ocean_quality = policy.evaluate(ocean, scene)
        phone_quality = policy.evaluate(phone, scene)
        self.assertGreater(
            phone_quality["adjustment"],
            ocean_quality["adjustment"] + 80,
        )
        self.assertIn("GENERIC_SCENERY_FOR_ACTION", ocean_quality["reasons"])

    def test_generic_lifestyle_is_penalized_without_scene_anchor(self):
        scene = {
            "segmento": "Depois da briga, ele começou a agir de forma estranha no hotel.",
            "visual_query": "hotel corridor worried traveler",
        }
        lifestyle = {
            "provider": "Pexels",
            "descricao": "fashion model relaxing with hookah on sofa",
        }
        result = policy.evaluate(lifestyle, scene)
        self.assertIn("GENERIC_LIFESTYLE", result["reasons"])
        self.assertLess(result["adjustment"], -70)

    def test_near_duplicate_visual_is_penalized(self):
        history = {
            "semantic_signatures": ["aerial fog forest mountain"],
        }
        candidate = {
            "provider": "Pixabay",
            "descricao": "aerial fog forest mountain",
        }
        result = policy.evaluate(
            candidate,
            {"segmento": "Até hoje, o paradeiro segue desconhecido."},
            history,
        )
        self.assertIn("NEAR_DUPLICATE_STRONG", result["reasons"])
        self.assertLessEqual(result["adjustment"], -90)

    def test_documentary_evidence_and_resolution_receive_bonus(self):
        scene = {
            "segmento": "A câmera do aeroporto registrou seus últimos passos.",
            "visual_query": "airport security camera cctv",
        }
        candidate = {
            "provider": "Wikimedia",
            "descricao": "airport terminal security camera cctv",
            "evidence_class": "CASE_DIRECT",
            "width": 1920,
            "height": 1080,
        }
        result = policy.evaluate(candidate, scene)
        self.assertIn("CASE_DIRECT", result["reasons"])
        self.assertIn("RESOLUTION_1080P_PLUS", result["reasons"])
        self.assertGreater(result["adjustment"], 60)

    def test_legacy_bridge_policy_still_prefers_scene_relevant_asset_in_isolation(self):
        """Unit-test the retired bridge algorithm without re-enabling it in production."""
        context = {
            "segmento": "Lars ligou desesperado para a mãe pelo telefone.",
            "busca": "man urgent phone call mother",
        }
        ocean = {
            "provider": "Pixabay",
            "fonte": "Pixabay",
            "type": "photo",
            "tipo": "foto",
            "id": "ocean",
            "descricao": "blue ocean water waves sea",
            "score": 120,
            "must_hits": 0,
        }
        phone = {
            "provider": "Pixabay",
            "fonte": "Pixabay",
            "type": "photo",
            "tipo": "foto",
            "id": "phone",
            "descricao": "man using smartphone making urgent phone call",
            "score": 60,
            "must_hits": 0,
        }

        with mock.patch.dict(os.environ, {"SAP_VSE42_RUNTIME": "1"}, clear=False):
            ranked, meta = bridge.rerank_pool([ocean, phone], context)
        self.assertEqual(ranked[0]["id"], "phone")
        self.assertIn("top_visual_quality_adjustment", meta)

    def test_bridge_contract_keeps_semantic_history(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "visual_selection_runtime_bridge_v42.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"semantic_signatures": []', source)
        self.assertIn("evaluate_visual_quality", source)
        self.assertIn("top_visual_quality_adjustment", source)


if __name__ == "__main__":
    unittest.main()
