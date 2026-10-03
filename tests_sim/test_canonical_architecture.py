import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import shortautopro_evolution as evo

ROOT=Path(__file__).resolve().parents[1]

class ConsolidationArchitectureTests(unittest.TestCase):
    def test_obsolete_runtime_wrappers_are_absent(self):
        obsolete=["gerar_short.sh","gerar_short_professional.sh","professional_pipeline_runtime.py","resume_short_professional_runtime.py","v6_professional_runtime.py","v6_runtime.py","v6.py","video.py","limpar_storage.sh","tools/apply_consolidation_1_0.py","31","SYNC_TEST.TXT",".resume_vi710_after_semantic_fix.sh.pre_segment_fix"]
        for relative in obsolete: self.assertFalse((ROOT/relative).exists(),relative)
        self.assertFalse((ROOT/"_arquivo_historico").exists())

    def test_canonical_pipeline_purges_forbidden_local_legacy_files(self):
        main=(ROOT/"main.py").read_text(encoding="utf-8"); purge=(ROOT/"tools"/"purge_legacy_runtime.py").read_text(encoding="utf-8")
        self.assertIn('p.run("0 - LEGACY RUNTIME PURGE", "tools/purge_legacy_runtime.py")',main)
        for legacy in ("gerar_short.sh","gerar_short_professional.sh","professional_pipeline_runtime.py","resume_short_professional_runtime.py","v6_professional_runtime.py","v6_runtime.py","v6.py","video.py","limpar_storage.sh","_arquivo_historico"): self.assertIn(legacy,purge)

    def test_single_canonical_pipeline_and_resume(self):
        main=(ROOT/"main.py").read_text(encoding="utf-8"); profile=(ROOT/"profile_run.sh").read_text(encoding="utf-8"); resume=(ROOT/"resume_short_runtime.py").read_text(encoding="utf-8")
        self.assertIn("CONSOLIDATION_3_0",main); self.assertIn("PROFESSIONAL_CANONICAL",main)
        self.assertIn("media_acquisition_v3.py",main); self.assertIn("render_plan_v2.py",main)
        self.assertIn("render_engine_v2.py",main)
        self.assertTrue((ROOT/"media_v3"/"acquisition.py").is_file())
        self.assertNotIn('p.run("MEDIA ENGINE V2 - ACQUIRE + VALIDATE + FREEZE MANIFEST", "media_engine_v2.py"',main)
        self.assertNotIn("media_stage_runtime.py",main)
        self.assertIn('MAIN="$BASE/main.py"',profile); self.assertIn('"$MAIN" run',profile)
        self.assertIn("import main as canonical",resume); self.assertIn("PROFESSIONAL_CANONICAL",resume)
        self.assertNotIn("SAP_PRO_EDIT",main); self.assertNotIn("gerar_short.sh",profile)

class EvolutionFacadeRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.base=Path(self.temp.name)
        self.old={"BASE":evo.BASE,"STATE_DIR":evo.STATE_DIR,"REPORT_DIR":evo.REPORT_DIR,"METRICS_DIR":evo.METRICS_DIR,"PROFILES_FILE":evo.PROFILES_FILE}
        evo.BASE=self.base; evo.STATE_DIR=self.base/".sap_state"; evo.REPORT_DIR=self.base/"reports"/"evolution"; evo.METRICS_DIR=self.base/"metrics"; evo.PROFILES_FILE=self.base/"config"/"channel_profiles.json"
        evo.PROFILES_FILE.parent.mkdir(parents=True,exist_ok=True)
        evo.PROFILES_FILE.write_text(json.dumps({"default":{"audio":{"target_lufs":-14}},"true_crime":{"audio":{"target_lufs":-14}}}),encoding="utf-8")
    def tearDown(self):
        for key,value in self.old.items(): setattr(evo,key,value)
        self.temp.cleanup()
    def test_explicit_missing_short_never_falls_back_to_unrelated_video(self):
        videos=self.base/"videos"; videos.mkdir(parents=True); (videos/"short_v6_other.mp4").write_bytes(b"unrelated")
        self.assertIsNone(evo.latest_video("missing")); self.assertEqual(evo.latest_video(None).name,"short_v6_other.mp4")
    def test_manual_quality_score_recovers_profile_from_short_artifact(self):
        roteiros=self.base/"roteiros"; roteiros.mkdir(parents=True); (roteiros/"pro_edit_plan_demo.json").write_text(json.dumps({"profile":"true_crime"}),encoding="utf-8")
        os.environ.pop("SAP_CHANNEL_PROFILE",None)
        with patch.object(evo,"_ORIGINAL_QUALITY_SCORE",side_effect=lambda sid:{"short_id":sid,"profile":os.getenv("SAP_CHANNEL_PROFILE","default")}):
            result=evo.quality_score("demo")
        self.assertEqual(result["profile"],"true_crime"); self.assertNotIn("SAP_CHANNEL_PROFILE",os.environ)
    def test_module_sandbox_assignment_is_forwarded_to_core(self): self.assertEqual(evo._core.BASE,self.base); self.assertEqual(evo._core.REPORT_DIR,self.base/"reports"/"evolution")

if __name__=="__main__": unittest.main()
