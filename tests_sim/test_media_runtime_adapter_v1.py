import os
import unittest
from unittest import mock

import media_runtime_adapter_v1 as adapter
import visual_selection_engine_v4 as vse


class MediaRuntimeAdapterTests(unittest.TestCase):
    def setUp(self):
        adapter._PROVIDER_SKIP_PRINTED.clear()

    def test_normalizes_portuguese_candidate_fields_for_vse(self):
        candidate = {
            "fonte": "Pixabay",
            "tipo": "foto",
            "descricao": "police tape crime scene investigation",
            "score": 50.0,
            "must_hits": 1,
            "avoid_hits": 0,
        }
        adapter.normalize_candidate(
            candidate,
            query="police tape crime scene",
            must_have=["police tape"],
        )
        self.assertEqual(candidate["provider"], "Pixabay")
        self.assertEqual(candidate["media_type"], "photo")
        self.assertEqual(candidate["description"], candidate["descricao"])
        self.assertEqual(candidate["must_coverage"], 1.0)

        scored = vse.score_candidate(
            candidate,
            {
                "visual_query": "police tape crime scene investigation",
                "must_have": ["police tape"],
            },
            {"providers": [], "groups": [], "types": [], "keys": []},
        )
        self.assertGreaterEqual(scored.get("must", 0), 1)

    def test_contextual_rescue_is_only_valid_in_relaxed_retry(self):
        candidate = {
            "fonte": "Pixabay",
            "tipo": "foto",
            "descricao": "police crime investigation detective evidence",
            "score": 46.0,
            "must_hits": 0,
            "avoid_hits": 0,
            "id": "ctx-1",
            "url": "https://cdn.pixabay.com/example.jpg",
        }

        def search(busca, must_have, avoid, segmento="", visual_mode=""):
            return [dict(candidate)]

        def validator(candidato, total_must, relaxado=False):
            return int(candidato.get("must_hits", 0) or 0) > 0

        def metadata(_candidate):
            return True

        ns = {
            "buscar_todos_candidatos": search,
            "candidato_semanticamente_valido": validator,
            "metadata_confiavel": metadata,
            "PEXELS_KEY": "",
            "USAR_PEXELS": True,
        }

        with mock.patch.dict(os.environ, {}, clear=False):
            result = adapter.install(ns)
            pool = ns["buscar_todos_candidatos"](
                "police tape crime investigation",
                ["police tape"],
                [],
                visual_mode="evidence",
            )

        self.assertTrue(result["installed"])
        self.assertEqual(len(pool), 1)
        rescued = pool[0]
        self.assertTrue(rescued.get("_sap_contextual_rescue"))
        self.assertEqual(rescued.get("must_hits"), 0)
        self.assertFalse(ns["candidato_semanticamente_valido"](rescued, 1, relaxado=False))
        self.assertTrue(ns["candidato_semanticamente_valido"](rescued, 1, relaxado=True))
        self.assertFalse(ns["metadata_confiavel"](rescued))

    def test_literal_must_candidate_is_not_marked_as_contextual_rescue(self):
        candidate = {
            "fonte": "Pixabay",
            "tipo": "foto",
            "descricao": "police tape crime scene",
            "score": 80.0,
            "must_hits": 1,
            "avoid_hits": 0,
        }
        marked = adapter._mark_contextual_rescue(
            [candidate],
            "police tape crime investigation",
            ["police tape"],
            "evidence",
        )
        self.assertFalse(marked[0].get("_sap_contextual_rescue", False))

    def test_contextual_rescue_rejects_avoid_and_identity_risk(self):
        avoid_candidate = {
            "descricao": "police crime investigation",
            "score": 80,
            "must_hits": 0,
            "avoid_hits": 1,
        }
        ok, _, reason = adapter._contextual_metrics(
            avoid_candidate,
            "police tape",
            ["police tape"],
            "evidence",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "AVOID_HIT")

        identity_candidate = {
            "descricao": "generic portrait woman",
            "score": 80,
            "must_hits": 0,
            "avoid_hits": 0,
        }
        ok, _, reason = adapter._contextual_metrics(
            identity_candidate,
            "specific historical woman portrait",
            ["woman portrait"],
            "named person identity",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "IDENTITY_SENSITIVE")

    def test_missing_pexels_key_skips_provider_without_calling_original(self):
        called = {"value": False}

        def pexels_video(busca, must_have, avoid):
            called["value"] = True
            return [{"id": "should-not-run"}]

        ns = {
            "pexels_video": pexels_video,
            "PEXELS_KEY": "",
            "USAR_PEXELS": True,
        }
        adapter.install(ns)
        result = ns["pexels_video"]("museum", [], [])
        self.assertEqual(result, [])
        self.assertFalse(called["value"])

    def test_install_keeps_only_one_decision_authority(self):
        ns = {}
        with mock.patch.dict(os.environ, {}, clear=False):
            result = adapter.install(ns)
            self.assertEqual(os.environ["SAP_VISUAL_UNIFIED"], "1")
            self.assertEqual(os.environ["SAP_VSE42_BRIDGE"], "0")
            self.assertEqual(os.environ["SAP_VSE4_QUERY_EXPANSION"], "1")
            self.assertEqual(os.environ["SAP_VSE42_RESCUE"], "0")
            self.assertEqual(os.environ["SAP_VG4X"], "0")
            self.assertTrue(result["query_expansion"])


if __name__ == "__main__":
    unittest.main()
