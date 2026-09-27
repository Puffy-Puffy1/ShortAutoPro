import importlib.util, json, os, tempfile, unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("batch_runtime",ROOT/"batch_runtime.py")
br=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(br)

class FakeRun:
    def __init__(self,code=0): self.returncode=code

class BatchRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); self.base=Path(self.t.name)
        for p in ("queue","reports/batches","logs/lotes",".sap_state","roteiros","videos","manifests"): (self.base/p).mkdir(parents=True,exist_ok=True)
        for p in ("main.py","release_artifact_guard.py","resume_short_runtime.py"): (self.base/p).write_text("# stub\n")
        self.old=(br.BASE,br.QUEUE,br.STATE,br.REPORTS)
        br.BASE=self.base; br.QUEUE=self.base/"queue"; br.STATE=br.QUEUE/"batch_state.json"; br.REPORTS=self.base/"reports"/"batches"
    def tearDown(self):
        br.BASE,br.QUEUE,br.STATE,br.REPORTS=self.old; self.t.cleanup()
    def test_state_has_ten_unique_items(self):
        d=br.new_state(10)
        self.assertEqual(len(d["items"]),10); self.assertEqual(len({x["short_id"] for x in d["items"]}),10)
        self.assertTrue(all(x["status"]=="QUEUED" for x in d["items"]))
        json.loads(br.STATE.read_text())
    def test_partial_item_uses_exact_resume(self):
        d=br.new_state(2); item=d["items"][1]; sid=item["short_id"]
        (self.base/"roteiros"/f"scene_map_{sid}.json").write_text("{}")
        calls=[]
        def fake(cmd,**kw): calls.append(cmd); return FakeRun(0)
        with mock.patch.object(br.subprocess,"run",side_effect=fake), mock.patch.object(br,"release_ok",side_effect=[False,True]):
            br.run_item(d,item,recovery=True)
        self.assertEqual(calls[0][-3:],["resume","--short-id",sid])
        self.assertEqual(item["status"],"COMPLETED")
    def test_fresh_item_uses_run(self):
        d=br.new_state(1); item=d["items"][0]; calls=[]
        def fake(cmd,**kw): calls.append(cmd); return FakeRun(0)
        with mock.patch.object(br.subprocess,"run",side_effect=fake), mock.patch.object(br,"release_ok",side_effect=[False,True]):
            br.run_item(d,item)
        self.assertEqual(calls[0][-2:],["run","--reuse-short-id"])
    def test_middle_failure_does_not_stop_later_items(self):
        d=br.new_state(5); seen=[]
        def fake_item(state,item,recovery=False):
            seen.append((item["index"],recovery))
            if item["index"]==3 and not recovery: item.update(status="RETRY_PENDING",attempts=1,error_code="MEDIA_PROVIDER_TIMEOUT")
            else: item.update(status="COMPLETED",attempts=item.get("attempts",0)+1,release="PUBLISH")
            br.save(state)
        with mock.patch.object(br,"run_item",side_effect=fake_item), mock.patch.object(br,"write_report",return_value=(Path("a"),Path("b"))):
            rc=br.execute(d)
        self.assertEqual(rc,0); self.assertEqual([x["status"] for x in d["items"]],["COMPLETED"]*5)
        self.assertIn((4,False),seen); self.assertIn((3,True),seen)
    def test_interrupted_completed_items_are_not_repeated(self):
        d=br.new_state(10)
        for x in d["items"][:4]: x["status"]="COMPLETED"
        called=[]
        def fake_item(state,item,recovery=False): called.append(item["index"]); item["status"]="COMPLETED"; br.save(state)
        with mock.patch.object(br,"run_item",side_effect=fake_item), mock.patch.object(br,"write_report",return_value=(Path("a"),Path("b"))):
            self.assertEqual(br.execute(d),0)
        self.assertEqual(called,list(range(5,11)))
    def test_clean_env_drops_cross_video_transients(self):
        with mock.patch.dict(os.environ,{"SHORT_ID":"old","SAP_REUSE_SHORT_ID":"1","SHORT_TOPIC_EXACT":"old-topic","KEEP_ME":"1"},clear=False):
            env=br.clean_env("new")
        self.assertEqual(env["SHORT_ID"],"new"); self.assertNotIn("SAP_REUSE_SHORT_ID",env); self.assertNotIn("SHORT_TOPIC_EXACT",env); self.assertEqual(env["KEEP_ME"],"1")

if __name__=="__main__": unittest.main()
