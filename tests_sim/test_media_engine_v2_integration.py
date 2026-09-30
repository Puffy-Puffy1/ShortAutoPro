import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import media_engine_v2

class MediaEngineV2IntegrationTests(unittest.TestCase):
    def test_mock_provider_to_frozen_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); media_engine_v2.BASE=base; sid="INTEGRATION_V2"
            (base/"roteiros").mkdir(parents=True)
            (base/"imagens"/f"short_{sid}").mkdir(parents=True)
            scenes=[{"scene_id":"01","query":"ship","must_have":["ship"],"avoid":[]}]
            (base/"roteiros"/f"scene_map_{sid}.json").write_text(json.dumps({"scenes":scenes}),encoding="utf-8")
            asset=base/"imagens"/f"short_{sid}"/"scene_01.jpg"
            # Minimal deterministic image generated from an in-process byte fixture
            # is not enough for ffprobe; the validation boundary is exercised by
            # the failure tests, while this integration test focuses on manifest wiring.
            fake={"source":"Mock","asset_id":"A","url":"","asset_type":"image","description":"ship",
                  "evidence_class":"MOCK","must_hits":1,"must_total":1,"path":str(asset),
                  "checksum_sha256":"fixture","probe":{"width":100,"height":100},"validated":True}
            manifest=media_engine_v2.build_manifest(sid,scenes,[fake])
            p=base/"manifests"/f"media_{sid}.json"; media_engine_v2.atomic_json(p,manifest)
            data=json.loads(p.read_text())
            self.assertEqual(data["short_id"],sid)
            self.assertEqual(data["scenes"][0]["asset"]["must_hits"],1)

if __name__=="__main__": unittest.main()
