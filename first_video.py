#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, secrets, subprocess, sys, uuid
from pathlib import Path
from subprocess_guard import run_group
from pipeline_contracts import PipelineArtifact, PipelineContext, PipelineStageResult, PipelineError

BASE=Path(os.getenv("SHORTAUTOPRO_BASE",Path.home()/"ShortAutoPro")).resolve()

def run_file(name,*args,timeout=1800):
    env=os.environ.copy(); env["SHORTAUTOPRO_BASE"]=str(BASE)
    proc=run_group([sys.executable,str(BASE/name),*args],cwd=BASE,env=env,check=False,timeout=timeout)
    if proc.returncode!=0:
        raise RuntimeError(f"FIRST_VIDEO_STAGE_FAILED:{name}:rc={proc.returncode}")
    return proc

def sid_value():
    return os.getenv("SHORT_ID","").strip() or ("fv_"+secrets.token_hex(6))

def run_stage(ctx, sid, label, name, *args, timeout=1800, artifacts=None):
    from datetime import datetime, timezone
    started = datetime.now(timezone.utc).isoformat()
    try:
        proc = run_file(name, *args, timeout=timeout)
        finished = datetime.now(timezone.utc).isoformat()
        ctx.add(PipelineStageResult(
            stage=label, status="PASS", run_id=ctx.run_id, short_id=sid,
            started_at=started, finished_at=finished,
            artifacts=[PipelineArtifact(**item) for item in (artifacts or [])],
        ))
        write_manifest(ctx, sid, "RUNNING")
        return proc
    except Exception as exc:
        finished = datetime.now(timezone.utc).isoformat()
        ctx.add(PipelineStageResult(
            stage=label, status="FAIL", run_id=ctx.run_id, short_id=sid,
            started_at=started, finished_at=finished,
            errors=[PipelineError(code=str(exc).split(":", 1)[0], message=str(exc), retryable=False)],
        ))
        write_manifest(ctx, sid, "FAILED")
        raise


def write_manifest(ctx, sid, status):
    out = BASE / "reports" / "first_video" / f"{sid}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = ctx.to_dict()
    payload["status"] = status
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")


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
    ctx = PipelineContext(run_id="first-video-" + uuid.uuid4().hex, short_id=sid)
    print(f"FIRST_VIDEO_START short_id={sid} topic={args.topic}")
    run_stage(ctx, sid, "TOPIC", "topic_engine_runtime.py", timeout=600)
    run_stage(ctx, sid, "SCRIPT", "script_runtime.py", timeout=900)
    roteiro = BASE / "roteiros" / f"short_{sid}.txt"
    if not roteiro.is_file():
        write_manifest(ctx, sid, "FAILED")
        raise RuntimeError("FIRST_VIDEO_SCRIPT_MISSING")
    run_stage(
        ctx, sid, "SCENES", "scene_director.py", timeout=900,
        artifacts=[{"name":"scene_map","path":str(BASE/"roteiros"/f"scene_map_{sid}.json"),"kind":"SceneMap"}],
    )
    print("FIRST_VIDEO_CONTENT=PASS")
    run_stage(
        ctx, sid, "MEDIA", "media_acquisition_v3.py", "--short-id", sid, timeout=1800,
        artifacts=[{"name":"media_manifest","path":str(BASE/"roteiros"/f"media_manifest_{sid}.json"),"kind":"MediaManifest"}],
    )
    print("FIRST_VIDEO_MEDIA=PASS")
    run_stage(
        ctx, sid, "RENDER_PLAN", "render_plan_v2.py", "--short-id", sid, timeout=300,
        artifacts=[{"name":"render_plan","path":str(BASE/"roteiros"/f"render_plan_{sid}.json"),"kind":"RenderPlan"}],
    )
    run_stage(ctx, sid, "AUDIO", "audio.py", timeout=900)
    print("FIRST_VIDEO_AUDIO=PASS")
    run_stage(ctx, sid, "CAPTIONS", "legenda_dinamica.py", timeout=900)
    run_stage(ctx, sid, "CAPTION_DIRECTOR", "professional_caption_director.py", timeout=300)
    run_stage(ctx, sid, "CAPTION_GUARD", "caption_layout_guard.py", timeout=300)
    print("FIRST_VIDEO_CAPTION=PASS")
    run_stage(ctx, sid, "RENDER", "render_engine_v2.py", "--short-id", sid, timeout=2400)
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
    write_manifest(ctx, sid, "PASSED")
    print(json.dumps({"short_id":sid,"path":str(final),"size_bytes":final.stat().st_size,
                      "duration":duration,
                      "resolution":f"{video.get('width')}x{video.get('height')}",
                      "fps":fps,"video_codec":video.get("codec_name"),
                      "audio_codec":audio.get("codec_name"),
                      "subtitle_streams":sum(1 for x in streams if x.get("codec_type")=="subtitle"),
                      "ffprobe":"PASS","technical_qa":"PASS"},ensure_ascii=False,indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
