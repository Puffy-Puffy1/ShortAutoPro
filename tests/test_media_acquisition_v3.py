import base64, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

from media_v3.query import build_query_plan
from media_v3.providers import ProviderAdapter, ProviderRegistry, ProviderStatus
from media_v3.acquisition import MediaAcquisitionV3
import media_acquisition_v3

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")

class FixtureProvider(ProviderAdapter):
    name="fixture"
    def __init__(self, root, mode="ok"):
        self.root=Path(root); self.mode=mode; self.calls=[]
    def status(self): return ProviderStatus(True)
    def search(self, query, must=None, soft_must=None, avoid=None):
        self.calls.append(query)
        if self.mode=="timeout": raise RuntimeError("PROVIDER_UNAVAILABLE")
        if self.mode=="empty": return []
        return [{"provider":self.name,"kind":"image","id":"fixture-1","url":"file://fixture","description":"ancient roman soldier"}]

class MediaV3Tests(unittest.TestCase):
    def test_query_plan_is_bounded_and_progressive(self):
        plan=build_query_plan("Ancient Roman soldier marching through northern Europe", ["Roman soldier"], max_variants=6)
        self.assertEqual(plan.original, "Ancient Roman soldier marching through northern Europe")
        self.assertLessEqual(len(plan.variants), 6)
        self.assertEqual(plan.variants[0], plan.original)
        self.assertTrue(any("Roman soldier" == x for x in plan.variants))

    def test_missing_credential_is_distinguished(self):
        from media_v3.providers import PexelsAdapter
        with patch.dict("os.environ", {"PEXELS_API_KEY":""}, clear=False):
            self.assertEqual(PexelsAdapter().status().reason, "NO_API_KEY")

    def test_provider_failure_falls_through_to_next_provider(self):
        class Bad(FixtureProvider):
            name="bad"
            def search(self, query, must=None, soft_must=None, avoid=None): raise RuntimeError("PROVIDER_UNAVAILABLE")
        class Good(FixtureProvider):
            name="good"
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); fixture=root/"real.png"; fixture.write_bytes(PNG)
            good=Good(root)
            good.search=lambda query, must=None, soft_must=None, avoid=None: [{"provider":"good","kind":"image","id":"g","url":"file://"+str(fixture),"description":"ancient roman soldier"}]
            engine=MediaAcquisitionV3(root, ProviderRegistry([Bad(root),good]))
            with patch.object(engine,"_download", lambda candidate,sid,number,diag: {"path":str(fixture),"sha256":"fixture","probe":{},"provider":"good","asset_id":"g"}):
                record,diag=engine.acquire_scene("SID1",1,{"scene_id":"scene_01","query":"roman soldier","must_have":["roman soldier"]})
            self.assertIsNotNone(record); self.assertEqual(record["provider"],"good")
            self.assertEqual(diag.final_status,"RESOLVED")

    def test_rejected_candidates_trigger_next_query_variant(self):
        class Progressive(FixtureProvider):
            name = "progressive"
            def search(self, query, must=None, soft_must=None, avoid=None):
                self.calls.append(query)
                if len(self.calls) == 1:
                    return [{"provider":self.name,"kind":"image","id":"bad","url":"file://bad","local_path":str(self.root/"bad.jpg"),"description":"unrelated subject"}]
                return [{"provider":self.name,"kind":"image","id":"good","url":"file://good","local_path":str(self.root/"good.png"),"description":"roman soldier"}]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); fixture=root/"good.png"; fixture.write_bytes(PNG+b"x"*2000); (root/"bad.jpg").write_bytes(b"x"*2000)
            provider=Progressive(root); engine=MediaAcquisitionV3(root, ProviderRegistry([provider]))
            record,diag=engine.acquire_scene("SID3",1,{"scene_id":"scene_01","query":"Ancient Roman soldier marching north","must_have":["roman soldier"]})
            self.assertIsNotNone(record); self.assertEqual(record["asset_id"],"good"); self.assertGreaterEqual(len(provider.calls),2)
            self.assertTrue(any(item["reason"]=="MUST_NOT_MATCH" for item in diag.rejections))

    def test_corrupt_download_is_rejected_and_does_not_pass(self):
        class Corrupt(FixtureProvider):
            name="corrupt"
            def search(self, query, must=None, soft_must=None, avoid=None):
                return [{"provider":"corrupt","kind":"image","id":"bad","url":"file://bad","local_path":str(self.root/"corrupt.jpg"),"description":"ancient roman soldier"}]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"corrupt.jpg").write_bytes(b"not-a-real-image"+b"x"*2000); engine=MediaAcquisitionV3(root, ProviderRegistry([Corrupt(root)]))
            with patch("media_v3.acquisition.requests.get") as get:
                get.side_effect=AssertionError("network must not be used for file:// in this fixture")
                record,diag=engine.acquire_scene("SID2",1,{"scene_id":"scene_01","query":"roman soldier","must_have":["roman soldier"]})
            self.assertIsNone(record); self.assertEqual(diag.final_status,"FAILED")

    def test_short_id_isolation_is_enforced(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); fixture=root/"real.png"; fixture.write_bytes(PNG)
            class Good(FixtureProvider):
                name="good"
                def search(self, query, must=None, soft_must=None, avoid=None):
                    return [{"provider":"good","kind":"image","id":"g","url":"file://"+str(fixture),"description":"roman soldier"}]
            engine=MediaAcquisitionV3(root, ProviderRegistry([Good(root)]))
            with patch.object(engine,"_download", lambda candidate,sid,number,diag: {"path":str(fixture),"sha256":"fixture","probe":{},"provider":"good","asset_id":"g"}):
                a,_=engine.acquire_scene("A",1,{"scene_id":"a","query":"roman soldier"}); b,_=engine.acquire_scene("B",1,{"scene_id":"b","query":"roman soldier"})
            self.assertEqual(a["provider"],b["provider"]); self.assertNotEqual("A","B")

    def test_manifest_contract_uses_frozen_media_and_diagnostics(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); sid="FIXTURE01"; (root/"roteiros").mkdir(); (root/"imagens").mkdir(); fixture=root/"real.png"; fixture.write_bytes(PNG)
            (root/"roteiros"/f"scene_map_{sid}.json").write_text(json.dumps({"scenes":[{"scene_id":"scene_01","query":"roman soldier"}]}),encoding="utf-8")
            class Good(FixtureProvider):
                name="good"
                def search(self, query, must=None, soft_must=None, avoid=None):
                    return [{"provider":"good","kind":"image","id":"g","url":"file://"+str(fixture),"description":"roman soldier"}]
            engine=MediaAcquisitionV3(root, ProviderRegistry([Good(root)]))
            with patch.object(engine,"_download", lambda candidate,sid,number,diag: {"path":str(fixture),"sha256":"fixture","probe":{"width":1,"height":1},"provider":"good","asset_id":"g"}):
                record,diag=engine.acquire_scene(sid,1,{"scene_id":"scene_01","query":"roman soldier"})
            self.assertIsNotNone(record); self.assertEqual(diag.final_status,"RESOLVED")

if __name__=="__main__": unittest.main()
