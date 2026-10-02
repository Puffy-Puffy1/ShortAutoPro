#!/usr/bin/env python3
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class RenderEngineV2RealTests(unittest.TestCase):
    def test_one_real_render_and_ffprobe_gate(self):
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            self.skipTest("ffmpeg/ffprobe unavailable")
        if not (ROOT / "render_v2" / "node_modules" / ".bin" / "remotion").is_file():
            self.skipTest("Remotion dependencies not installed in this workflow")
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); base=home/"ShortAutoPro"; sid="v2_real"
            media=base/"imagens"/f"short_{sid}"; media.mkdir(parents=True)
            (base/"roteiros").mkdir(parents=True); (base/"audios").mkdir(parents=True); (base/"videos").mkdir(parents=True); (base/"manifests").mkdir(parents=True)
            for i in range(1,7):
                out=media/f"scene_{i:02d}.png"
                subprocess.run(["ffmpeg","-y","-loglevel","error","-f","lavfi","-i",f"testsrc2=size=1080x1920:rate=30:duration=0.5","-frames:v","1",str(out)],check=True,timeout=30)
            assets=[]
            for i in range(1,7):
                out=media/f"scene_{i:02d}.png"
                assets.append({"path":str(out),"checksum_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"validated":True,"must_hits":0,"must_total":0})
            manifest={"schema_version":"media-manifest-v2","short_id":sid,"immutable":True,"scene_count":len(assets),"scenes":[{"scene_id":str(i),"scene_number":i,"query":"","must_have":[],"avoid":[],"asset":asset} for i,asset in enumerate(assets,1)]}
            (base/"manifests"/f"media_{sid}.json").write_text(json.dumps(manifest),encoding="utf-8")
            audio=base/"audios"/f"short_{sid}.mp3"
            subprocess.run(["ffmpeg","-y","-loglevel","error","-f","lavfi","-i","sine=frequency=440:sample_rate=48000:duration=3","-c:a","libmp3lame",str(audio)],check=True,timeout=30)
            scenes=[{"scene":i,"segment":f"cena {i}","words":3} for i in range(1,7)]
            plan=[{"scene":i,"pace_multiplier":1.0,"zoom_start":1.0,"zoom_end":1.01,"pan":"center","transition_duration":0.05} for i in range(1,7)]
            (base/"roteiros"/f"scene_map_{sid}.json").write_text(json.dumps({"scenes":scenes}),encoding="utf-8")
            (base/"roteiros"/f"pro_edit_plan_{sid}.json").write_text(json.dumps({"scenes":plan}),encoding="utf-8")
            ass="[Script Info]\\nScriptType: v4.00+\\nPlayResX: 1080\\nPlayResY: 1920\\n\\n[V4+ Styles]\\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\\nStyle: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,2,40,40,80,1\\n\\n[Events]\\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\\nDialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,Render V2\\n"
            (base/"videos"/f"short_{sid}.ass").write_text(ass,encoding="utf-8")
            env=os.environ.copy(); env.update({"SHORTAUTOPRO_BASE":str(base),"HOME":str(home),"USERPROFILE":str(home)})
            proc=subprocess.run([sys.executable,str(ROOT/"render_engine_v2.py"),"--short-id",sid],cwd=ROOT,env=env,text=True,capture_output=True,timeout=1200)
            output=proc.stdout+proc.stderr
            self.assertEqual(proc.returncode,0,output)
            final=base/"videos"/f"short_v6_{sid}.mp4"
            self.assertTrue(final.is_file(),output)
            self.assertGreater(final.stat().st_size,1000)
            probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(final)],text=True))
            streams=probe["streams"]
            self.assertTrue(any(x.get("codec_type")=="video" for x in streams))
            self.assertTrue(any(x.get("codec_type")=="audio" for x in streams))

if __name__=="__main__":
    unittest.main()
