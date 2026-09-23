import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import production_recovery
import visual_engine_unified
import visual_score_engine


class CanonicalVisualScoreTests(unittest.TestCase):
    def test_visual_unified_commit_persists_exact_selected_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            candidate = {
                "fonte": "Pixabay",
                "tipo": "foto",
                "id": "asset-123",
                "descricao": "old stone church exterior at night",
                "score": 84.0,
            }
            ctx = {
                "SHORT_ID": "case",
                "numero": 3,
                "busca": "old stone church night documentary",
                "segmento": "A igreja apareceu nos registros.",
                "cena": {"scene": 3, "query": "old stone church night documentary"},
            }
            with mock.patch.object(visual_engine_unified, "ROOT", base), \
                 mock.patch.object(
                     visual_engine_unified,
                     "_score",
                     return_value={
                         "effective": 72.0,
                         "must": 0,
                         "hard_mismatch": False,
                         "safety_reasons": [],
                     },
                 ):
                visual_engine_unified.note_commit_runtime(candidate, ctx)

            ledger = base / "roteiros" / "selected_media_case.json"
            self.assertTrue(ledger.is_file())
            data = json.loads(ledger.read_text(encoding="utf-8"))
            row = data["scenes"]["3"]
            self.assertEqual(row["provider"], "Pixabay")
            self.assertEqual(row["candidate_key"], "pixabay:asset-123")
            self.assertEqual(row["description"], candidate["descricao"])
            self.assertEqual(row["effective_score"], 72.0)
            self.assertFalse(row["hard_mismatch"])

    def test_shadow_only_score_is_observational_not_false_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            r = base / "roteiros"
            r.mkdir()
            scene_map = r / "scene_map_case.json"
            vi = r / "visual_intelligence_6_case.json"
            selected = r / "selected_media_case.json"
            out = r / "visual_score_case.json"
            media = base / "imagens" / "short_case"
            media.mkdir(parents=True)

            scenes = [
                {
                    "scene": i,
                    "segment": f"Trecho {i}",
                    "query": f"specific documentary query {i}",
                    "must_have": [],
                }
                for i in range(1, 13)
            ]
            shadows = [
                {
                    "winner": {
                        "descricao": "generic stock image",
                        "fonte": "Pixabay",
                        "semantic": 20,
                        "risk": "LOW",
                        "class": "SAFE_CONTEXT",
                    }
                }
                for _ in range(12)
            ]
            scene_map.write_text(json.dumps({"scenes": scenes}), encoding="utf-8")
            vi.write_text(json.dumps({"scenes": shadows}), encoding="utf-8")

            with mock.patch.object(visual_score_engine, "SID", "case"), \
                 mock.patch.object(visual_score_engine, "R", r), \
                 mock.patch.object(visual_score_engine, "MAP", scene_map), \
                 mock.patch.object(visual_score_engine, "VI", vi), \
                 mock.patch.object(visual_score_engine, "SELECTED", selected), \
                 mock.patch.object(visual_score_engine, "MEDIA", media), \
                 mock.patch.object(visual_score_engine, "OUT", out), \
                 mock.patch.object(visual_score_engine, "media_for", return_value=Path("dummy.jpg")), \
                 mock.patch.object(visual_score_engine, "probe", return_value=(1920, 1080)):
                rc = visual_score_engine.main()

            self.assertEqual(rc, 0)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "OBSERVE")
            self.assertEqual(report["measurement_confidence"], "LOW")
            self.assertEqual(report["canonical_commit_count"], 0)
            self.assertEqual(report["weak_scenes"], [])
            self.assertGreaterEqual(report["visual_score"], 78.0)
            self.assertEqual(len(report["shadow_weak_scenes"]), 12)

    def test_low_confidence_visual_report_does_not_trigger_pre_render_repair(self):
        report = {
            "status": "OBSERVE",
            "measurement_confidence": "LOW",
            "canonical_coverage": 0.0,
            "visual_score": 78.0,
            "weak_scenes": [],
            "scenes": [{} for _ in range(12)],
        }
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            r = base / "roteiros"
            r.mkdir(parents=True)
            path = r / "visual_score_case.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            with mock.patch.object(production_recovery, "BASE", base):
                state = production_recovery._visual_quality_state("case")
        self.assertFalse(state["authoritative"])
        self.assertFalse(state["needs_repair"])


if __name__ == "__main__":
    unittest.main()
