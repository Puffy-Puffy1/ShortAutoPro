import os
import tempfile
import unittest
from pathlib import Path

import media_runtime_adapter_v2 as adapter
from visual_query_planner_v4 import detect_concepts, expansion_queries


class MediaRuntimeAdapterV2Tests(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    @staticmethod
    def _namespace(candidate):
        def buscar_todos_candidatos(busca, must_have=None, avoid=None, visual_mode=""):
            del busca, must_have, avoid, visual_mode
            return [dict(candidate)]

        return {
            "buscar_todos_candidatos": buscar_todos_candidatos,
            "candidato_semanticamente_valido": lambda c, total_must, relaxado=False: bool(
                relaxado and int(c.get("must_hits", 0) or 0) > 0
            ),
            "metadata_confiavel": lambda c: int(c.get("must_hits", 0) or 0) > 0,
            "ordenar_failover_5_2": lambda candidates, total_must, route, previous="": [],
            "fallback_preserva_5_2": lambda candidate, reference: False,
            "baixar_candidato_5_2": lambda candidate, scene, label: (False, None),
            "buscar_local": lambda prefer_video: None,
            "_vse42_enabled": lambda: True,
            "_vse42_finalize_pool": lambda pool, chosen, local_context=None: [chosen] + list(pool),
            "_vse42_note_success": lambda candidate: candidate,
            "_vse42_commit_media": lambda path: [path],
            "VI6_MODE": "ACTIVE",
        }

    def test_neutral_missing_must_penalty_can_rescue_safe_context(self):
        candidate = {
            "provider": "pixabay",
            "media_type": "photo",
            "description": "old corroded utensil improvised digging object inside prison cell",
            "score": 21.1,
            "must_hits": 0,
            "avoid_hits": 0,
        }
        ns = self._namespace(candidate)
        report = adapter.install(ns)

        result = ns["buscar_todos_candidatos"](
            "vintage metal spoon used as prison tool close up",
            ["rusty metal spoon", "primitive tool"],
            [],
            "stock_first",
        )
        self.assertTrue(report["neutral_contextual_rescue"])
        self.assertEqual(len(result), 1)
        rescued = result[0]
        self.assertEqual(rescued["must_hits"], 0, "rescue must never fabricate MUST coverage")
        self.assertEqual(rescued["_sap_verified_must_hits"], 0)
        self.assertTrue(rescued["_sap_contextual_rescue"])
        self.assertAlmostEqual(rescued["_sap_contextual_neutral_score"], 61.1, places=1)
        self.assertGreaterEqual(rescued["_sap_contextual_score"], 0.25)
        self.assertFalse(ns["candidato_semanticamente_valido"](rescued, 2, relaxado=False))
        self.assertTrue(ns["candidato_semanticamente_valido"](rescued, 2, relaxado=True))
        self.assertFalse(ns["metadata_confiavel"](rescued))

    def test_marked_rescue_reaches_failover_when_strict_pool_is_empty(self):
        candidate = {
            "provider": "pixabay",
            "media_type": "photo",
            "description": "vintage metal spoon corroded utensil prison cell",
            "score": 21.1,
            "must_hits": 0,
            "avoid_hits": 0,
            "id": "spoon",
            "url": "https://example.invalid/spoon.jpg",
        }
        ns = self._namespace(candidate)
        adapter.install(ns)
        found = ns["buscar_todos_candidatos"](
            "vintage metal spoon used as prison tool close up",
            ["rusty metal spoon", "primitive tool"],
            [],
            "stock_first",
        )
        self.assertTrue(found[0].get("_sap_contextual_rescue"))
        pool = ns["ordenar_failover_5_2"](
            found,
            2,
            {"route": "stock_first"},
            "",
        )
        self.assertEqual(len(pool), 1)
        self.assertIs(pool[0], found[0])
        self.assertEqual(pool[0]["must_hits"], 0)

    def test_avoid_hit_still_blocks_contextual_rescue(self):
        candidate = {
            "provider": "pixabay",
            "media_type": "photo",
            "description": "old corroded utensil improvised digging object inside prison cell",
            "score": 21.1,
            "must_hits": 0,
            "avoid_hits": 1,
        }
        ns = self._namespace(candidate)
        adapter.install(ns)
        result = ns["buscar_todos_candidatos"](
            "vintage metal spoon used as prison tool close up",
            ["rusty metal spoon", "primitive tool"],
            [],
            "stock_first",
        )
        self.assertFalse(result[0].get("_sap_contextual_rescue", False))

    def test_unified_safe_winner_is_not_rejected_by_stale_reference(self):
        ns = self._namespace({"description": "placeholder", "score": 50})
        adapter.install(ns)
        winner = {
            "_sap_visual_unified_winner": True,
            "_sap_visual_unified_hard": False,
            "must_hits": 1,
            "avoid_hits": 0,
        }
        stale_reference = {"must_hits": 2, "avoid_hits": 0}
        self.assertTrue(ns["fallback_preserva_5_2"](winner, stale_reference))

        winner["_sap_visual_unified_hard"] = True
        self.assertFalse(ns["fallback_preserva_5_2"](winner, stale_reference))

    def test_contextual_retry_can_degrade_only_after_safety_mark(self):
        ns = self._namespace({"description": "placeholder", "score": 50})
        adapter.install(ns)
        rescue = {
            "_sap_contextual_rescue": True,
            "must_hits": 0,
            "avoid_hits": 0,
        }
        reference = {"must_hits": 2, "avoid_hits": 0}
        self.assertTrue(ns["fallback_preserva_5_2"](rescue, reference))
        rescue["avoid_hits"] = 1
        self.assertFalse(ns["fallback_preserva_5_2"](rescue, reference))

    def test_vse42_legacy_finalizer_cannot_reorder_visual_unified_pool(self):
        ns = self._namespace({"description": "placeholder", "score": 50})
        report = adapter.install(ns)
        visual_unified_winner = {"id": "visual-unified-winner"}
        legacy_chosen = {"id": "legacy-chosen"}
        ordered = [visual_unified_winner, legacy_chosen]

        self.assertFalse(ns["_vse42_enabled"]())
        self.assertEqual(
            ns["_vse42_finalize_pool"](ordered, legacy_chosen, {"scene": 2}),
            ordered,
        )
        self.assertIsNone(ns["_vse42_note_success"](visual_unified_winner))
        self.assertEqual(ns["_vse42_commit_media"]("scene_02.jpg"), [])
        self.assertTrue(report["vse42_authority_disabled"])
        self.assertEqual(report["authority"], "VISUAL_UNIFIED")

    def test_neutral_context_score_only_restores_missing_must_penalty(self):
        candidate = {
            "score": 21.1,
            "must_hits": 0,
            "_sap_verified_must_hits": 0,
            "_sap_must_total": 2,
        }
        self.assertAlmostEqual(adapter.neutral_context_score(candidate), 61.1, places=1)
        candidate["_sap_verified_must_hits"] = 1
        self.assertAlmostEqual(adapter.neutral_context_score(candidate), 41.1, places=1)

    def test_continuity_fallback_reuses_previous_valid_media_as_low_trust(self):
        candidate = {"description": "placeholder", "score": 50}
        ns = self._namespace(candidate)
        adapter.install(ns)

        with tempfile.TemporaryDirectory() as tmp:
            previous = Path(tmp) / "scene_01.jpg"
            previous.write_bytes(b"validated-media")
            ns["_SAP_LAST_VALID_MEDIA_PATH"] = str(previous)
            reused = ns["buscar_local"](False)
            self.assertEqual(reused, str(previous))
            local_candidate = {
                "fonte": "Local",
                "id": previous.name,
                "must_hits": 0,
            }
            self.assertFalse(ns["metadata_confiavel"](local_candidate))

    def test_federal_marshals_does_not_trigger_ocean_expansion(self):
        query = "vintage federal marshals wanted poster"
        self.assertNotIn("ocean", detect_concepts(query))
        plans = expansion_queries(query)
        self.assertTrue(plans)
        self.assertFalse(any("ocean sea underwater" in plan for plan in plans))
        self.assertFalse(any("marine ocean footage" in plan for plan in plans))

    def test_real_ocean_terms_still_expand(self):
        self.assertIn("ocean", detect_concepts("dark ocean water"))
        self.assertIn("ocean", detect_concepts("mar escuro com neblina"))
        plans = expansion_queries("dark ocean water")
        self.assertTrue(any("ocean sea underwater" in plan for plan in plans))


if __name__ == "__main__":
    unittest.main()
