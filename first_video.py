#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re, secrets, subprocess, sys
from pathlib import Path
from subprocess_guard import run_group

BASE=Path(os.getenv("SHORTAUTOPRO_BASE",Path.home()/"ShortAutoPro")).resolve()

def run_file(name,*args,timeout=1800):
    env=os.environ.copy(); env["SHORTAUTOPRO_BASE"]=str(BASE)
    proc=run_group([sys.executable,str(BASE/name),*args],cwd=BASE,env=env,check=False,timeout=timeout)
    if proc.returncode!=0:
        raise RuntimeError(f"FIRST_VIDEO_STAGE_FAILED:{name}:rc={proc.returncode}")
    return proc

def sid_value():
    return os.getenv("SHORT_ID","").strip() or ("fv_"+secrets.token_hex(6))

def split_script(text):
    words=re.findall(r"\b[\wÀ-ÿ'-]+\b",text,flags=re.UNICODE)
    if len(words)<12: raise RuntimeError("FIRST_VIDEO_SCRIPT_TOO_SHORT")
    mid=max(6,len(words)//2)
    return " ".join(words[:mid])," ".join(words[mid:])

def write_scene_map(sid,topic,script):
    a,b=split_script(script)
    q1=" ".join(re.findall(r"[A-Za-z0-9]+",topic))[:90] or "documentary subject"
    scenes=[
      {"scene_id":"first-video-01","segment":a,"query":f"{q1} documentary","must_have":[],"avoid":["wrong person","unrelated event"],"words":len(a.split())},
      {"scene_id":"first-video-02","segment":b,"query":f"{q1} detail","must_have":[],"avoid":["wrong person","unrelated event"],"words":len(b.split())},
    ]
    out=BASE/"roteiros"/f"scene_map_{sid}.json"; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"schema_version":"scene-map-first-video-v1","short_id":sid,"scenes":scenes},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (BASE/"roteiros"/f"short_{sid}.txt").write_text(script,encoding="utf-8")
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--topic",required=True)
    ap.add_argument("--short-id",default="")
    args=ap.parse_args()
    sid=args.short_id.strip() or sid_value()
    os.environ["SHORT_ID"]=sid
    os.environ["SHORT_TOPIC_EXACT"]=args.topic.strip()
    os.environ["SHORT_ALLOW_REPEAT_TOPIC"]="1"
    os.environ["SHORT_QTD_CENAS"]="2"
    print(f"FIRST_VIDEO_START short_id={sid} topic={args.topic}")
    run_file("topic_engine_runtime.py",timeout=600)
    run_file("script_runtime.py",timeout=900)
    roteiro=BASE/"roteiros"/f"short_{sid}.txt"
    if not roteiro.is_file(): raise RuntimeError("FIRST_VIDEO_SCRIPT_MISSING")
    script=roteiro.read_text(encoding="utf-8").strip()
    write_scene_map(sid,args.topic,script)
    print("FIRST_VIDEO_CONTENT=PASS")
    run_file("media_acquisition_v3.py","--short-id",sid,timeout=1800)
    print("FIRST_VIDEO_MEDIA=PASS")
    run_file("render_plan_v2.py","--short-id",sid,timeout=300)
    run_file("audio.py",timeout=900)
    print("FIRST_VIDEO_AUDIO=PASS")
    run_file("legenda_dinamica.py",timeout=900)
    run_file("professional_caption_director.py",timeout=300)
    run_file("caption_layout_guard.py",timeout=300)
    print("FIRST_VIDEO_CAPTION=PASS")
    run_file("render_engine_v2.py","--short-id",sid,timeout=2400)
    final=BASE/"videos"/f"short_v6_{sid}.mp4"
    if not final.is_file() or final.stat().st_size<=1000: raise RuntimeError("FIRST_VIDEO_OUTPUT_INVALID")
    probe=run_group(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(final)],cwd=BASE,capture_output=True,text=True,check=True,timeout=60)
    data=json.loads(probe.stdout)
    streams=data.get("streams",[])
    video=next((x for x in streams if x.get("codec_type")=="video"),{})
    audio=next((x for x in streams if x.get("codec_type")=="audio"),{})
    if not video or not audio: raise RuntimeError("FIRST_VIDEO_FFPROBE_MISSING_STREAM")
    duration=float(data.get("format",{}).get("duration") or 0)
    fps=video.get("avg_frame_rate") or ""
    if duration <= 0 or not video.get("width") or not video.get("height") or not video.get("codec_name") or not audio.get("codec_name"):
        raise RuntimeError("FIRST_VIDEO_TECHNICAL_QA_INVALID_METADATA")
    print(json.dumps({"short_id":sid,"path":str(final),"size_bytes":final.stat().st_size,
                      "duration":duration,
                      "resolution":f"{video.get('width')}x{video.get('height')}",
                      "fps":fps,"video_codec":video.get("codec_name"),
                      "audio_codec":audio.get("codec_name"),
                      "subtitle_streams":sum(1 for x in streams if x.get("codec_type")=="subtitle"),
                      "ffprobe":"PASS","technical_qa":"PASS"},ensure_ascii=False,indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
