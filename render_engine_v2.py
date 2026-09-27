#!/usr/bin/env python3
"""ShortAutoPro Render Engine V2.

Acquisition-free renderer boundary:
  frozen local inputs -> Remotion composition -> FFmpeg finalization -> FFprobe -> gates -> atomic commit.

This module never calls media providers, never creates a new SHORT_ID during
retry/resume, and never publishes a file before output validation succeeds.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from subprocess_guard import run_group

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", Path.home() / "ShortAutoPro")).resolve()
ENGINE_VERSION = "2.0.0"
FPS = 30
WIDTH = 1080
HEIGHT = 1920
MEDIA_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"}
STATES = ["CREATED","VALIDATING_INPUT","READY","RENDERING","RENDERED","VALIDATING_OUTPUT","PASSED","FAILED","RECOVERY_PENDING","RETRYING","CANCELLED"]

def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")

def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp, path); tmp = ""
    finally:
        if tmp:
            try: os.unlink(tmp)
            except OSError: pass

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be object")
    return data

def ass_time(value: str) -> float:
    h, m, rest = value.strip().split(":")
    s, cs = rest.split(".")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100.0

def parse_ass(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    cues = []
    for raw in path.read_text(encoding="utf-8", errors="strict").splitlines():
        if not raw.startswith("Dialogue:"):
            continue
        parts = raw.split(",", 9)
        if len(parts) != 10:
            raise ValueError("SUBTITLE_INVALID: malformed ASS dialogue")
        start, end = ass_time(parts[1]), ass_time(parts[2])
        text = parts[9].replace(r"\N", "\n").strip()
        if end <= start:
            raise ValueError("SUBTITLE_INVALID: non-positive cue")
        cues.append({"start": start, "end": end, "text": text})
    if any(cues[i]["start"] > cues[i+1]["start"] for i in range(len(cues)-1)):
        raise ValueError("SUBTITLE_INVALID: timestamp regression")
    return cues

def audio_duration(path: Path) -> float:
    p = run_group(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)], capture_output=True, text=True, check=False, timeout=30)
    if p.returncode != 0:
        raise RuntimeError(f"FFPROBE_FAILED:{path.name}")
    value = float((p.stdout or "").strip())
    if not math.isfinite(value) or value <= 0:
        raise RuntimeError("INVALID_DURATION: audio")
    return value

def choose_render_id(job_root: Path) -> str:
    if not job_root.exists():
        return "render_001"
    existing = sorted(p.name for p in job_root.iterdir() if p.is_dir() and p.name.startswith("render_"))
    if not existing:
        return "render_001"
    for name in existing:
        state = job_root / name / "state.json"
        if state.is_file():
            try:
                if read_json(state).get("status") != "PASSED":
                    return name
            except Exception:
                return name
    return f"render_{len(existing)+1:03d}"

def build_job(short_id: str) -> Path:
    source = BASE / "roteiros"
    scene_map_path = source / f"scene_map_{short_id}.json"
    edit_path = source / f"pro_edit_plan_{short_id}.json"
    audio = BASE / "audios" / f"short_{short_id}.mp3"
    ass = BASE / "videos" / f"short_{short_id}.ass"
    media_dir = BASE / "imagens" / f"short_{short_id}"
    for p in (scene_map_path, edit_path, audio, media_dir):
        if not p.exists():
            raise RuntimeError(f"RENDER_INPUT_INVALID:{p.name}")
    scenes_raw = read_json(scene_map_path).get("scenes")
    plan = read_json(edit_path)
    planned = plan.get("scenes")
    if not isinstance(scenes_raw, list) or not scenes_raw:
        raise RuntimeError("RENDER_INPUT_INVALID:scene_map")
    if not isinstance(planned, list) or len(planned) != len(scenes_raw):
        raise RuntimeError("RENDER_INPUT_INVALID:pro_edit_plan")
    duration = audio_duration(audio)
    weights = []
    for scene, edit in zip(scenes_raw, planned):
        words = int(scene.get("words", 0) or 0)
        if words <= 0:
            words = max(1, len(str(scene.get("segment", "")).split()))
        pace = float(edit.get("pace_multiplier", 1.0) or 1.0)
        weights.append(max(0.2, words * max(0.78, min(1.14, pace))))
    total_weight = sum(weights)
    durations = [duration * w / total_weight for w in weights]
    min_scene = 0.45
    for i, value in enumerate(durations):
        durations[i] = max(min_scene, value)
    scale = duration / sum(durations)
    durations = [x * scale for x in durations]
    root = BASE / "render_jobs" / short_id
    render_id = choose_render_id(root)
    job = root / render_id
    if (job / "job.json").is_file() and (job / "manifest.json").is_file() and (job / "timeline.json").is_file():
        return job
    public_assets = job / "public" / "assets"
    public_assets.mkdir(parents=True, exist_ok=True)
    (job / "audio").mkdir(parents=True, exist_ok=True)
    frozen_scenes = []
    t = 0.0
    for idx, (scene, edit, logical) in enumerate(zip(scenes_raw, planned, durations), 1):
        candidates = sorted(
            p for p in media_dir.glob(f"scene_{idx:02d}*")
            if p.is_file() and p.suffix.lower() in MEDIA_EXTS
        )
        if len(candidates) != 1:
            raise RuntimeError(f"RENDER_ASSET_INVALID:scene_{idx:02d}:expected_one_got_{len(candidates)}")
        src = candidates[0]
        if src.stat().st_size <= 1000:
            raise RuntimeError(f"RENDER_ASSET_INVALID:scene_{idx:02d}:too_small")
        # Reject known neutral/editorial placeholders at the render boundary.
        name = src.name.lower()
        if any(token in name for token in ("slate","placeholder","neutral_editorial","editorial_reuse")):
            raise RuntimeError(f"REAL_MEDIA_MISSING:scene_{idx:02d}")
        rel = f"assets/scene_{idx:02d}{src.suffix.lower()}"
        dst = public_assets / f"scene_{idx:02d}{src.suffix.lower()}"
        shutil.copy2(src, dst)
        frozen_scenes.append({
            "scene_id": str(scene.get("scene_id", scene.get("scene", idx))),
            "asset_path": str(src),
            "asset": rel,
            "asset_type": "video" if src.suffix.lower() in {".mp4",".mov",".webm",".mkv"} else "image",
            "duration": round(logical, 6),
            "start_time": round(t, 6),
            "end_time": round(t + logical, 6),
            "source": str(scene.get("source", "")),
            "provenance": scene.get("provenance", {}),
            "validation_status": "FROZEN_LOCAL",
            "checksum_sha256": sha256(src),
            "effect": {
                "zoom_start": edit.get("zoom_start", 1.0),
                "zoom_end": edit.get("zoom_end", edit.get("zoom_start", 1.0)),
                "pan": edit.get("pan", "center"),
            },
            "transition": {
                "type": edit.get("cut_style", "editorial_cut") if idx > 1 else "none",
                "duration": float(edit.get("transition_duration", 0.0) or 0.0),
            },
        })
        t += logical
    frozen_audio = job / "audio" / audio.name
    shutil.copy2(audio, frozen_audio)
    cues = parse_ass(ass) if ass.is_file() else []
    if not ass.is_file():
        raise RuntimeError("SUBTITLE_INVALID:subtitle file missing")
    manifest = {
        "schema_version": "render-manifest-v2",
        "short_id": short_id,
        "render_id": render_id,
        "engine_version": ENGINE_VERSION,
        "frozen_at": now(),
        "assets": frozen_scenes,
        "audio": {"path": str(frozen_audio), "required": True, "checksum_sha256": sha256(frozen_audio)},
    }
    timeline = {
        "schema_version": "render-timeline-v2",
        "short_id": short_id,
        "render_id": render_id,
        "fps": FPS,
        "width": WIDTH,
        "height": HEIGHT,
        "duration": round(duration, 6),
        "scenes": frozen_scenes,
        "subtitles": cues,
    }
    job_json = {
        "schema_version": "render-job-v2",
        "job_id": f"{short_id}:{render_id}",
        "short_id": short_id,
        "render_id": render_id,
        "fps": FPS,
        "width": WIDTH,
        "height": HEIGHT,
        "duration_target": round(duration, 6),
        "orientation": "portrait",
        "codec": "h264",
        "audio_required": True,
        "subtitles_required": True,
        "created_at": now(),
        "engine_version": ENGINE_VERSION,
    }
    atomic_json(job/"job.json", job_json)
    atomic_json(job/"manifest.json", manifest)
    atomic_json(job/"timeline.json", timeline)
    atomic_json(job/"state.json", {"job_id": job_json["job_id"], "status":"CREATED","history":[{"status":"CREATED","at":now()}]})
    return job

def transition(job: Path, status: str, **extra: Any) -> None:
    if status not in STATES:
        raise ValueError(status)
    path = job / "state.json"
    state = read_json(path) if path.is_file() else {"job_id": job.name, "history":[]}
    current = str(state.get("status", "CREATED"))
    allowed = {
        "CREATED":{"VALIDATING_INPUT","CANCELLED"},
        "VALIDATING_INPUT":{"READY","FAILED"},
        "READY":{"RENDERING","FAILED"},
        "RENDERING":{"RENDERED","FAILED"},
        "RENDERED":{"VALIDATING_OUTPUT","FAILED"},
        "VALIDATING_OUTPUT":{"PASSED","FAILED"},
        "FAILED":{"RECOVERY_PENDING","RETRYING","CANCELLED"},
        "RECOVERY_PENDING":{"RETRYING","CANCELLED"},
        "RETRYING":{"RENDERING","FAILED"},
        "PASSED":set(),
        "CANCELLED":set(),
    }
    if status != current and status not in allowed.get(current, set()):
        raise RuntimeError(f"INVALID_STATE_TRANSITION:{current}->{status}")
    state.update(extra)
    state["status"] = status
    state.setdefault("history", []).append({"status":status,"at":now(),**extra})
    atomic_json(path,state)

def run_cmd(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return run_group(cmd, cwd=cwd, capture_output=True, text=True, check=False, timeout=timeout)

def validate_input(job: Path) -> dict[str, Any]:
    manifest = read_json(job/"manifest.json")
    timeline = read_json(job/"timeline.json")
    errors=[]
    assets=manifest.get("assets",[])
    if not assets: errors.append("RENDER_ASSET_MISSING")
    for item in assets:
        path=Path(str(item.get("asset_path","")))
        if not path.is_file(): errors.append(f"RENDER_ASSET_MISSING:{item.get('scene_id')}")
        if item.get("validation_status")!="FROZEN_LOCAL": errors.append(f"RENDER_ASSET_INVALID:{item.get('scene_id')}")
    audio=Path(str(manifest.get("audio",{}).get("path","")))
    if not audio.is_file(): errors.append("AUDIO_STREAM_MISSING")
    if timeline.get("short_id") != manifest.get("short_id"): errors.append("RENDER_INPUT_INVALID:identity")
    if len(timeline.get("scenes",[])) != len(assets): errors.append("RENDER_INPUT_INVALID:timeline")
    if errors: raise RuntimeError(";".join(errors))
    return {"asset_count":len(assets),"subtitle_count":len(timeline.get("subtitles",[]))}

def remotion_binary() -> Path:
    p=BASE/"render_v2"/"node_modules"/".bin"/("remotion.cmd" if os.name=="nt" else "remotion")
    if p.is_file(): return p
    raise RuntimeError("RENDER_RUNTIME_MISSING:render_v2/node_modules; install render_v2 dependencies first")

def render_visual(job: Path) -> Path:
    output=job/"rendered.visual.mp4"
    output.unlink(missing_ok=True)
    props=job/"remotion_props.json"
    timeline=read_json(job/"timeline.json")
    props_data={"fps":FPS,"width":WIDTH,"height":HEIGHT,"duration_target":timeline["duration"],"timeline":timeline}
    atomic_json(props,props_data)
    cmd=[str(remotion_binary()),"render",str(BASE/"render_v2"/"src/index.tsx"),"ShortAutoProV2",str(output),
         "--props",str(props),"--public-dir",str(job/"public"),"--width",str(WIDTH),"--height",str(HEIGHT),"--fps",str(FPS),
         "--pixel-format","yuv420p","--codec","h264","--crf",os.getenv("SAP_RENDER_V2_CRF","20"),
         "--concurrency",os.getenv("SAP_RENDER_V2_CONCURRENCY","2"),"--log","error"]
    timeout=int(os.getenv("SAP_RENDER_V2_TIMEOUT_SECONDS","1800"))
    p=run_cmd(cmd,BASE,timeout)
    if p.returncode!=0:
        raise RuntimeError(f"REMOTION_FAILED:{p.returncode}:{(p.stderr or '')[-1600:]}")
    if not output.is_file() or output.stat().st_size<=1000:
        raise RuntimeError("REMOTION_FAILED:empty_output")
    return output

def ffmpeg_finalize(job: Path) -> Path:
    visual=job/"rendered.visual.mp4"; audio=Path(str(read_json(job/"manifest.json")["audio"]["path"]))
    temp=job/"final.rendering.mp4"; temp.unlink(missing_ok=True)
    cmd=["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(visual),"-i",str(audio),
         "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-ar","48000",
         "-shortest","-movflags","+faststart",str(temp)]
    p=run_cmd(cmd,BASE,int(os.getenv("SAP_RENDER_V2_FFMPEG_TIMEOUT_SECONDS","1200")))
    if p.returncode!=0: raise RuntimeError(f"FFMPEG_FAILED:{p.returncode}:{(p.stderr or '')[-1600:]}")
    if not temp.is_file() or temp.stat().st_size<=1000: raise RuntimeError("FFMPEG_FAILED:empty_output")
    return temp

def validate_output(path: Path, job: Path) -> dict[str, Any]:
    report=ffprobe_validator(path, job)
    if not report["quality_gate"]: raise RuntimeError("QUALITY_GATE_FAIL:"+",".join(report["errors"]))
    return report

def ffprobe_validator(path: Path, job: Path) -> dict[str, Any]:
    errors=[]
    if not path.is_file() or path.stat().st_size < 500_000: errors.append("MP4_EXISTS_OR_SIZE")
    probe=run_cmd(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],BASE,45)
    if probe.returncode!=0: errors.append("FFPROBE_FAILED")
    try: data=json.loads(probe.stdout or "{}")
    except Exception: data={}; errors.append("FFPROBE_JSON_INVALID")
    streams=data.get("streams",[]) if isinstance(data,dict) else []
    fmt=data.get("format",{}) if isinstance(data,dict) else {}
    video=next((s for s in streams if s.get("codec_type")=="video"),{})
    audio=next((s for s in streams if s.get("codec_type")=="audio"),{})
    target=float(read_json(job/"job.json")["duration_target"])
    try: actual=float(fmt.get("duration",0))
    except Exception: actual=0
    if not video: errors.append("VIDEO_STREAM_MISSING")
    if not audio: errors.append("AUDIO_STREAM_MISSING")
    if video and (int(video.get("width",0)),int(video.get("height",0)))!=(WIDTH,HEIGHT): errors.append("INVALID_RESOLUTION")
    if video and video.get("codec_name")!="h264": errors.append("INVALID_VIDEO_CODEC")
    if audio and audio.get("codec_name")!="aac": errors.append("INVALID_AUDIO_CODEC")
    if not math.isfinite(actual) or actual<=0 or abs(actual-target)>max(0.45,target*0.02): errors.append("INVALID_DURATION")
    if video:
        rate=str(video.get("avg_frame_rate",""))
        if rate not in {"30/1","30000/1001"}: errors.append("INVALID_FPS")
    decode=run_cmd(["ffmpeg","-v","error","-xerror","-i",str(path),"-map","0:v:0","-map","0:a:0","-f","null","-"],BASE,max(60,min(300,int(target*4+30))))
    if decode.returncode!=0: errors.append("OUTPUT_DECODE_FAILED")
    first=run_cmd(["ffmpeg","-v","error","-i",str(path),"-vf","select=eq(n\,0),signalstats,metadata=print:file=-","-frames:v","1","-f","null","-"],BASE,45)
    first_text=(first.stdout or "")+(first.stderr or "")
    yavg=None
    for line in first_text.splitlines():
        if "YAVG=" in line:
            try: yavg=float(line.split("YAVG=",1)[1].split()[0].strip("\r"))
            except Exception: pass
    if first.returncode!=0 or yavg is None: errors.append("FIRST_FRAME_INVALID")
    elif yavg < 3.0: errors.append("FIRST_FRAME_BLACK")
    black=run_cmd(["ffmpeg","-v","info","-i",str(path),"-vf","blackdetect=d=0.75:pix_th=0.01","-an","-f","null","-"],BASE,max(60,min(300,int(target*3+30))))
    black_text=(black.stderr or "")+(black.stdout or "")
    if "black_start:0" in black_text and "black_duration:" in black_text:
        import re
        m=re.search(r"black_start:0[^\n]*black_duration:([0-9.]+)",black_text)
        if m and float(m.group(1))>=0.75: errors.append("FATAL_OPENING_BLACK_SEGMENT")
    audio_silence=run_cmd(["ffmpeg","-v","info","-i",str(path),"-map","0:a:0","-af","silencedetect=n=-55dB:d=1.5","-f","null","-"],BASE,max(60,min(300,int(target*3+30))))
    silence_text=(audio_silence.stderr or "")+(audio_silence.stdout or "")
    if "silence_start: 0" in silence_text and "silence_duration:" in silence_text:
        errors.append("AUDIO_COMPLETELY_SILENT_AT_START")
    report={
        "engine":"render_v2","version":ENGINE_VERSION,"short_id":read_json(job/"job.json")["short_id"],"render_id":read_json(job/"job.json")["render_id"],
        "status":"PASSED" if not errors else "FAILED","duration_seconds":actual,"video_stream":bool(video),"audio_stream":bool(audio),
        "real_media":all(x.get("validation_status")=="FROZEN_LOCAL" for x in read_json(job/"manifest.json").get("assets",[])),
        "first_frame_valid":not any(x in errors for x in ("FIRST_FRAME_INVALID","FIRST_FRAME_BLACK")),
        "ffprobe":"PASS" if not any(x.startswith("FFPROBE") for x in errors) else "FAIL",
        "quality_gate":"PASS" if not errors else "FAIL","errors":errors,
    }
    atomic_json(job/"render_report.json",report)
    return report

def commit_output(temp: Path, job: Path, short_id: str) -> Path:
    final=BASE/"videos"/f"short_v6_{short_id}.mp4"
    final.parent.mkdir(parents=True,exist_ok=True)
    staging=job/"final.commit.mp4"
    shutil.copy2(temp,staging)
    if staging.stat().st_size < 500_000: raise RuntimeError("ATOMIC_COMMIT_FAILED:staging_small")
    os.replace(staging,final)
    return final

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--short-id",required=True)
    args=parser.parse_args()
    sid=args.short_id.strip()
    if not sid: print("RENDER_INPUT_INVALID:empty_short_id"); return 1
    try:
        job=build_job(sid)
        state=read_json(job/"state.json") if (job/"state.json").is_file() else {"status":"CREATED"}
        if state.get("status")=="PASSED":
            report=read_json(job/"render_report.json")
            print(json.dumps(report,ensure_ascii=False)); return 0
        transition(job,"VALIDATING_INPUT")
        detail=validate_input(job)
        transition(job,"READY",input=detail)
        transition(job,"RENDERING")
        started=time.monotonic()
        visual=render_visual(job)
        transition(job,"RENDERED",render_seconds=round(time.monotonic()-started,3))
        transition(job,"VALIDATING_OUTPUT")
        temp=ffmpeg_finalize(job)
        report=validate_output(temp,job)
        if not report["quality_gate"]:
            transition(job,"FAILED",error_code="QUALITY_GATE_FAIL",errors=report["errors"])
            return 1
        final=commit_output(temp,job,sid)
        transition(job,"PASSED",output=str(final),report=report)
        print(json.dumps(report,ensure_ascii=False))
        return 0
    except subprocess.TimeoutExpired as exc:
        try: transition(job,"FAILED",error_code="RENDER_TIMEOUT")
        except Exception: pass
        print("RENDER_TIMEOUT",exc); return 1
    except Exception as exc:
        try:
            if 'job' in locals():
                transition(job,"FAILED",error_code=str(exc).split(":",1)[0],error=str(exc)[-2000:])
        except Exception: pass
        print(f"RENDER_ENGINE_V2_FAILED: {exc}"); return 1

if __name__=="__main__":
    raise SystemExit(main())
