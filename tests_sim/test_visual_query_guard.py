import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import visual_query_guard


class VisualQueryGuardTests(unittest.TestCase):
    def test_generic_repeated_queries_are_repaired_without_touching_narration(self):
        segments = [
            "A igreja antiga apareceu nos registros da investigacao",
            "Uma carta foi encontrada perto da casa abandonada",
            "A policia voltou a estrada durante a noite",
            "Testemunhas falaram sobre um carro perto da ponte",
            "O documento citava uma escola na pequena cidade",
            "A familia procurou respostas no hospital local",
            "Uma fotografia mostrava a entrada da floresta",
            "O investigador revisou o arquivo do caso",
            "A testemunha descreveu um homem perto do rio",
            "A busca chegou a um cemiterio antigo",
            "Novos documentos mudaram a investigacao",
            "O caso terminou sem explicar o desaparecimento",
        ]
        scenes = [
            {
                "scene": i,
                "segment": segment,
                "query": "documentary visual context scene",
                "must_have": [],
                "avoid": [],
            }
            for i, segment in enumerate(segments, 1)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            r = base / "roteiros"
            r.mkdir()
            mapa = r / "scene_map_case.json"
            report = r / "visual_query_guard_case.json"
            mapa.write_text(json.dumps({"scenes": scenes}), encoding="utf-8")
            before = [x["segment"] for x in scenes]
            with mock.patch.object(visual_query_guard, "BASE", base), \
                 mock.patch.object(visual_query_guard, "R", r), \
                 mock.patch.object(visual_query_guard, "SID", "case"), \
                 mock.patch.object(visual_query_guard, "MAP", mapa), \
                 mock.patch.object(visual_query_guard, "REPORT", report):
                rc = visual_query_guard.main()
            self.assertEqual(rc, 0)
            out = json.loads(mapa.read_text(encoding="utf-8"))
            self.assertEqual([x["segment"] for x in out["scenes"]], before)
            queries = [x["query"] for x in out["scenes"]]
            self.assertTrue(all(not visual_query_guard.is_generic(q) for q in queries))
            counts = {}
            for q in queries:
                key = visual_query_guard.norm(q)
                counts[key] = counts.get(key, 0) + 1
            self.assertLess(max(counts.values()), 3)
            rep = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(rep["status"], "REPAIRED")
            self.assertEqual(len(rep["changed_scenes"]), 12)


if __name__ == "__main__":
    unittest.main()
