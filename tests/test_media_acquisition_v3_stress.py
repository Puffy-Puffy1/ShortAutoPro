import base64, tempfile, unittest
from pathlib import Path
import media_acquisition_v3

PNG=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")

class FakeEngine:
    def __init__(self,fixture,fail_sid=None):
        self.fixture=Path(fixture); self.fail_sid=fail_sid; self.calls=[]
    def acquire_scene(self,sid,number,scene):
        self.calls.append(sid)
        if sid==self.fail_sid:
            from media_v3.diagnostics import SceneDiagnostics
            d=SceneDiagnostics("scene_01","fixture",must=[],avoid=[]); d.final_status="FAILED"; d.error="INJECTED_FAILURE"
            return None,d
        from media_v3.diagnostics import SceneDiagnostics
        from media_validator_v2 import validate
        v=validate(self.fixture); d=SceneDiagnostics("scene_01","fixture",must=[],avoid=[]); d.final_status="RESOLVED"; d.selected_provider="fixture"; d.selected_asset_id=sid
        return {"path":str(self.fixture),"sha256":v["sha256"],"probe":v["probe"],"provider":"fixture","asset_id":sid,"verification_mode":"fixture","provenance":{"provider":"fixture"}},d

class AcquisitionV3StressTests(unittest.TestCase):
    def _scene(self): return {"scene_id":"scene_01","query":"fixture"}
    def test_sequential_1_2_5_10_jobs_are_isolated(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); media_acquisition_v3.BASE=base; fixture=base/"fixture.png"; fixture.write_bytes(PNG)
            engine=FakeEngine(fixture)
            (base/"roteiros").mkdir()
            for n in range(1,11):
                sid=f"JOB_{n:02d}"
                (base/"roteiros"/f"scene_map_{sid}.json").write_text(__import__("json").dumps({"scenes":[self._scene()]}),encoding="utf-8")
                manifest=media_acquisition_v3.build_manifest(sid,engine)
                self.assertEqual(manifest["short_id"],sid); self.assertEqual(manifest["scene_count"],1)
                self.assertTrue((base/"manifests"/f"media_{sid}.json").is_file())
            self.assertEqual(len(set(engine.calls)),10)
            self.assertEqual(len(engine.calls),10)
            for n in range(1,11):
                self.assertTrue((base/"imagens"/f"short_JOB_{n:02d}"/"scene_01.json").is_file())

    def test_resume_reuses_frozen_media_without_reacquisition(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); media_acquisition_v3.BASE=base; fixture=base/"fixture.png"; fixture.write_bytes(PNG)
            sid="RESUME_01"; (base/"roteiros").mkdir()
            (base/"roteiros"/f"scene_map_{sid}.json").write_text(__import__("json").dumps({"scenes":[self._scene()]}),encoding="utf-8")
            engine=FakeEngine(fixture)
            first=media_acquisition_v3.build_manifest(sid,engine)
            second=media_acquisition_v3.build_manifest(sid,engine)
            self.assertEqual(first["integrity_sha256"],second["integrity_sha256"])
            self.assertEqual(engine.calls,[sid])

    def test_batch_failure_does_not_stop_other_jobs(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); media_acquisition_v3.BASE=base; fixture=base/"fixture.png"; fixture.write_bytes(PNG)
            (base/"roteiros").mkdir(); engine=FakeEngine(fixture,fail_sid="JOB_02"); results={}
            for n in range(1,6):
                sid=f"JOB_{n:02d}"
                (base/"roteiros"/f"scene_map_{sid}.json").write_text(__import__("json").dumps({"scenes":[self._scene()]}),encoding="utf-8")
                try: media_acquisition_v3.build_manifest(sid,engine); results[sid]="COMPLETED"
                except RuntimeError: results[sid]="FAILED"
            self.assertEqual(results,{"JOB_01":"COMPLETED","JOB_02":"FAILED","JOB_03":"COMPLETED","JOB_04":"COMPLETED","JOB_05":"COMPLETED"})

if __name__=="__main__": unittest.main()
