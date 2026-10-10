#!/usr/bin/env python3
import json, os, shutil, subprocess, sys, tempfile, unittest, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(cmd, env):
    p = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True, timeout=300)
    if p.returncode:
        raise AssertionError((p.stdout + "\n" + p.stderr)[-6000:])
    return p.stdout

class RenderEngineV2ConsecutiveTests(unittest.TestCase):
    def test_1_2_5_10_consecutive_jobs_are_isolated(self):
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            self.skipTest("ffmpeg/ffprobe unavailable")
        counts = (1, 2, 5, 10)
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp); base = home / "ShortAutoPro"
            for p in ("roteiros", "audios", "videos", "manifests"):
                (base / p).mkdir(parents=True)
            results = []; ordinal = 0
            for count in counts:
                batch_outputs = []
                for _ in range(count):
                    ordinal += 1; sid = f"stress_{ordinal:02d}"
                    media = base / "imagens" / f"short_{sid}"; media.mkdir(parents=True)
                    scenes = [{"scene_id": str(i), "scene": i, "segment": f"scene {i}", "words": 4} for i in range(1, 4)]
                    plan = [{"scene": i, "pace_multiplier": 1.0, "zoom_start": 1.0, "zoom_end": 1.02, "pan": "center"} for i in range(1, 4)]
                    (base/"manifests"/f"scene_map_{sid}.json").write_text(json.dumps({
                        "schema_version":"SCENE_MAP_FROZEN_1.0","short_id":sid,
                        "mutable_upstream_closed":True,"scenes":scenes
                    }), encoding="utf-8")
                    render_plan = {"schema_version":"render-plan-v2","short_id":sid,"immutable":True,"scenes":plan}
                    render_plan["integrity_sha256"] = __import__("render_engine_v2")._manifest_integrity(render_plan)
                    (base/"roteiros"/f"pro_edit_plan_{sid}.json").write_text(json.dumps(render_plan), encoding="utf-8")
                    for i in range(1, 4):
                        out = media / f"scene_{i:02d}.png"
                        subprocess.run(["ffmpeg","-y","-loglevel","error","-f","lavfi","-i",
                                         f"testsrc2=size=1080x1920:rate=30:duration=0.5,hue=h={ordinal*17+i*11}",
                                         "-frames:v","1",str(out)], check=True, timeout=30)
                    assets=[]
                    for i in range(1,4):
                        path=media/f"scene_{i:02d}.png"
                        assets.append({"source":"fixture","asset_id":f"{sid}-{i}","asset_type":"image","path":str(path),
                                       "checksum_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                                       "probe":{"width":1080,"height":1920},"validated":True})
                    media_manifest = {
                        "schema_version":"media-manifest-v2","version":2,"engine":"Media Acquisition V3",
                        "short_id":sid,"immutable":True,"scene_count":3,
                        "scenes":[{"scene_id":str(i),"scene_number":i,"query":"fixture","must_have":[],"avoid":[],"asset":assets[i-1]} for i in range(1,4)]
                    }
                    media_manifest["integrity_sha256"] = __import__("render_engine_v2")._manifest_integrity(media_manifest)
                    (base/"manifests"/f"media_{sid}.json").write_text(json.dumps(media_manifest), encoding="utf-8")
                    audio = base/"audios"/f"short_{sid}.mp3"
                    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","lavfi","-i",
                                     "sine=frequency=440:sample_rate=48000:duration=2.5",
                                     "-c:a","libmp3lame",str(audio)], check=True, timeout=30)
                    (base/"videos"/f"short_{sid}.ass").write_text(
                        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n[V4+ Styles]\n"
                        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, TertiaryColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, AlphaLevel, Encoding\n"
                        "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,1,2,0,2,30,30,60,0,1\n"
                        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
                        "Dialogue: 0,0:00:00.00,0:00:02.50,Default,,0,0,0,,Render V2 stress\n", encoding="utf-8")
                    env=os.environ.copy(); env.update({"SHORTAUTOPRO_BASE":str(base),"HOME":str(home),"USERPROFILE":str(home),
                                                       "SAP_RENDER_V2_CRF":"20","SAP_RENDER_V2_CONCURRENCY":"2","SAP_RENDER_V2_BACKEND":"ffmpeg"})
                    run([sys.executable,str(ROOT/"render_engine_v2.py"),"--short-id",sid], env)
                    final=base/"videos"/f"short_v6_{sid}.mp4"
                    self.assertTrue(final.is_file()); self.assertGreater(final.stat().st_size,1000)
                    report=json.loads((base/"render_jobs"/sid/"render_001"/"render_report.json").read_text(encoding="utf-8"))
                    self.assertEqual(report["quality_gate"],"PASS"); self.assertEqual(report["short_id"],sid)
                    batch_outputs.append(final)
                results.append(batch_outputs)
            all_ids=[p.stem.replace("short_v6_","") for group in results for p in group]
            self.assertEqual(len(all_ids),18); self.assertEqual(len(set(all_ids)),18)
            for sid in all_ids:
                job=base/"render_jobs"/sid/"render_001"
                state=json.loads((job/"state.json").read_text(encoding="utf-8"))
                manifest=json.loads((job/"manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(state["status"],"PASSED"); self.assertEqual(manifest["short_id"],sid)

if __name__=="__main__": unittest.main()
