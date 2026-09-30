import json, os, subprocess, sys, tempfile, unittest, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class RenderManifestE2ETests(unittest.TestCase):
    def test_frozen_manifest_to_ffmpeg_to_ffprobe_quality_gate(self):
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            self.skipTest("ffmpeg/ffprobe unavailable")
        with tempfile.TemporaryDirectory() as td:
            home=Path(td); base=home/"ShortAutoPro"
            for p in ("roteiros","audios","videos","manifests"):
                (base/p).mkdir(parents=True)
            sid="E2E_V2"
            media=base/"imagens"/f"short_{sid}"; media.mkdir(parents=True)
            scenes=[{"scene_id":"01","scene":1,"segment":"fixture","words":4},
                    {"scene_id":"02","scene":2,"segment":"fixture","words":4}]
            plan=[{"scene_id":"01","pace_multiplier":1.0,"zoom_start":1.0,"zoom_end":1.02,"pan":"center"},
                  {"scene_id":"02","pace_multiplier":1.0,"zoom_start":1.0,"zoom_end":1.02,"pan":"center"}]
            (base/"roteiros"/f"scene_map_{sid}.json").write_text(json.dumps({"scenes":scenes}),encoding="utf-8")
            (base/"roteiros"/f"pro_edit_plan_{sid}.json").write_text(json.dumps({"scenes":plan}),encoding="utf-8")
            assets=[]
            for i in (1,2):
                path=media/f"scene_{i:02d}.png"
                subprocess.run(["ffmpeg","-y","-loglevel","error","-f","lavfi","-i",f"testsrc2=size=1080x1920:rate=30:duration=1.0","-frames:v","1",str(path)],check=True,timeout=30)
                import hashlib
                assets.append({"source":"fixture","asset_id":str(i),"asset_type":"image","path":str(path),
                               "checksum_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                               "probe":{"width":1080,"height":1920},"validated":True})
            (base/"manifests"/f"media_{sid}.json").write_text(json.dumps({
                "schema_version":"media-manifest-v2","version":2,"engine":"Media Engine V2",
                "short_id":sid,"immutable":True,"scenes":[{"scene_id":str(i),"scene_number":i,
                "query":"fixture","must_have":[],"avoid":[],"asset":assets[i-1]} for i in (1,2)]
            }),encoding="utf-8")
            subprocess.run(["ffmpeg","-y","-loglevel","error","-f","lavfi","-i","sine=frequency=440:sample_rate=48000:duration=2.0",
                            "-c:a","aac",str(base/"audios"/f"short_{sid}.mp3")],check=True,timeout=30)
            (base/"videos"/f"short_{sid}.ass").write_text(
                "[Script Info]\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
                "Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,V2 fixture\n",encoding="utf-8")
            env=os.environ.copy(); env.update({"SHORTAUTOPRO_BASE":str(base),"SAP_RENDER_V2_BACKEND":"ffmpeg","HOME":str(home)})
            p=subprocess.run([sys.executable,str(ROOT/"render_engine_v2.py"),"--short-id",sid],
                             cwd=ROOT,env=env,text=True,capture_output=True,timeout=300)
            self.assertEqual(p.returncode,0,p.stdout+"\n"+p.stderr)
            final=base/"videos"/f"short_v6_{sid}.mp4"
            self.assertTrue(final.is_file()); self.assertGreater(final.stat().st_size,1000)
            report=json.loads((base/"render_jobs"/sid/"render_001"/"render_report.json").read_text())
            self.assertEqual(report["ffprobe"],"PASS")
            self.assertEqual(report["quality_gate"],"PASS")
            self.assertTrue(report["first_frame_valid"])

if __name__=="__main__": unittest.main()
