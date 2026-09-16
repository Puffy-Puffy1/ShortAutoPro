import os
import tempfile
import unittest
from pathlib import Path

import media_runtime_adapter_v1 as adapter


class MediaRescue302Tests(unittest.TestCase):
    def test_spoon_context_can_rescue_without_faking_must(self):
        candidate = {
            "score": 21.1,
            "must_hits": 0,
            "avoid_hits": 0,
            "fonte": "Pixabay",
            "tipo": "foto",
            "descricao": "vintage metal spoon cutlery on dark table",
            "url": "https://example.invalid/spoon.jpg",
            "id": "spoon-1",
        }
        result = [candidate]
        adapter._mark_contextual_rescue(
            result,
            "vintage metal spoon used as prison tool close up",
            ["rusty metal spoon", "primitive tool"],
            "",
        )
        self.assertEqual(candidate["must_hits"], 0)
        self.assertTrue(candidate.get("_sap_contextual_rescue"))
        self.assertGreaterEqual(candidate.get("_sap_contextual_score", 0.0), 0.25)

    def test_contextual_rescue_rejects_identity_sensitive_scene(self):
        candidate = {
            "score": 80,
            "must_hits": 0,
            "avoid_hits": 0,
            "descricao": "man portrait prison bars",
        }
        ok, _, reason = adapter._contextual_metrics(
            candidate,
            "named prisoner portrait",
            ["single prisoner", "iron bars"],
            "named person identity",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "IDENTITY_SENSITIVE")

    def test_empty_strict_failover_uses_marked_contextual_pool(self):
        candidate = {
            "score": 21.1,
            "must_hits": 0,
            "avoid_hits": 0,
            "_sap_contextual_rescue": True,
            "_sap_contextual_score": 0.5,
            "tipo": "foto",
        }
        namespace = {
            "ordenar_failover_5_2": lambda *args, **kwargs: [],
        }
        self.assertTrue(adapter._wrap_failover(namespace))
        pool = namespace["ordenar_failover_5_2"](
            [candidate], 2, {"route": "stock_first"}, ""
        )
        self.assertEqual(pool, [candidate])

    def test_unified_winner_cannot_be_rejected_by_stale_reference(self):
        winner = {
            "must_hits": 1,
            "avoid_hits": 0,
            "_sap_visual_unified_winner": True,
        }
        reference = {"must_hits": 2, "avoid_hits": 0}
        namespace = {"fallback_preserva_5_2": lambda c, r: False}
        self.assertTrue(adapter._wrap_reference_guard(namespace))
        self.assertTrue(namespace["fallback_preserva_5_2"](winner, reference))

    def test_continuity_fallback_reuses_last_success_only_as_last_resort(self):
        old = os.environ.get("SAP_MEDIA_CONTINUITY_FALLBACK")
        os.environ["SAP_MEDIA_CONTINUITY_FALLBACK"] = "1"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                previous = Path(tmp) / "scene_01.jpg"
                previous.write_bytes(b"fake")
                namespace = {
                    "buscar_local": lambda preferir_video: None,
                    "_SAP_LAST_SUCCESS_PATH": str(previous),
                }
                self.assertTrue(adapter._wrap_local_continuity_fallback(namespace))
                self.assertEqual(namespace["buscar_local"](False), str(previous))
        finally:
            if old is None:
                os.environ.pop("SAP_MEDIA_CONTINUITY_FALLBACK", None)
            else:
                os.environ["SAP_MEDIA_CONTINUITY_FALLBACK"] = old

    def test_runtime_adapter_declares_single_authority_contract(self):
        source = Path(adapter.__file__).read_text(encoding="utf-8")
        self.assertIn('"SAP_VISUAL_UNIFIED": "1"', source)
        self.assertIn('"SAP_VSE42_BRIDGE": "0"', source)
        self.assertIn('"SAP_VG4X": "0"', source)
        self.assertIn("MEDIA_LEGACY_DECISION_BRIDGES=DISABLED", source)
        self.assertIn("SAP_CONTEXTUAL_RESCUE_ACTIVATED", source)
        self.assertIn("SAP_MEDIA_CONTINUITY_FALLBACK=REUSE_PREVIOUS_SCENE", source)


if __name__ == "__main__":
    unittest.main()
