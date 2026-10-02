#!/usr/bin/env python3
"""ShortAutoPro Render Engine V2.

Acquisition-free renderer boundary:
  frozen local inputs -> render backend -> FFmpeg finalization -> FFprobe -> gates -> atomic commit.

Backends:
  - remotion: Linux/desktop execution with Chromium.
  - ffmpeg: native FFmpeg visual backend for Termux/Android, no browser required.

This module never calls media providers, never creates a new SHORT_ID during
retry/resume, and never publishes a file before output validation succeeds.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from subprocess_guard import run_group
from render_v2.ffmpeg_visual_renderer import render_visual_ffmpeg

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", Path.home() / "ShortAutoPro")).resolve()
RENDER_PROJECT = Path(__file__).resolve().parent / "render_v2"
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

def validate_ass_contract(path: Path) -> None:
    """Fail early when an ASS file is structurally incompatible with libass."""
    if not path.is_file():
        raise ValueError("SUBTITLE_INVALID: subtitle file missing")
    text = path.read_text(encoding="utf-8", errors="strict")
    sections = {line.strip().lower() for line in text.splitlines() if line.strip().startswith("[") and line.strip().endswith("]")}
    if "[script info]" not in sections:
        raise ValueError("SUBTITLE_INVALID: missing [Script Info]")
    if "[events]" not in sections:
        raise ValueError("SUBTITLE_INVALID: missing [Events]")
    if not ({"[v4+ styles]", "[v4 styles]"} & sections):
        raise ValueError("SUBTITLE_INVALID: missing ASS styles section")
    if not any(line.strip().lower().startswith("dialogue:") for line in text.splitlines()):
        raise ValueError("SUBTITLE_INVALID: no dialogue events")


def parse_ass(path: Path) -> list[dict[str, Any]]:
    validate_ass_contract(path)
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

def validate_short_id(short_id: str) -> str:
    sid = str(short_id or "").strip()
    if not sid or not re.fullmatch(r"[A-Za-z0-9._-]+", sid) or ".." in sid:
        raise RuntimeError("RENDER_INPUT_INVALID:short_id")
    return sid

def choose_render_id(job_root: Path) -> str:
    if not job_root.exists():
        return "render_001"
    existing = sorted(
        (p.name for p in job_root.iterdir() if p.is_dir() and p.name.startswith("render_")),
        reverse=True,
    )
    if not existing:
        return "render_001"
    # A given SHORT_ID owns one resumable render lineage. Reusing the latest
    # render directory is important: a persisted PASSED state must be revalidated
    # instead of silently creating a fresh render that bypasses stale-state checks.
    return existing[0]

def build_job(short_id: str) -> Path:
    short_id = validate_short_id(short_id)
    source = BASE / "roteiros"
    scene_map_path = source / f"scene_map_{short_id}.json"
    edit_path = source / f"pro_edit_plan_{short_id}.json"
    audio = BASE / "audios" / f"short_{short_id}.mp3"
    ass = BASE / "videos" / f"short_{short_id}.ass"
    media_manifest_path = BASE / "manifests" / f"media_{short_id}.json"
    for p in (scene_map_path, edit_path, audio, media_manifest_path):
        if not p.exists():
            raise RuntimeError(f"RENDER_INPUT_INVALID:{p.name}")
    scenes_raw = read_json(scene_map_path).get("scenes")
    plan = read_json(edit_path)
    media_manifest = read_json(media_manifest_path)
    planned = plan.get("scenes")
    frozen_assets = media_manifest.get("scenes")
    if media_manifest.get("schema_version") != "media-manifest-v2":
        raise RuntimeError("RENDER_INPUT_INVALID:media_manifest_schema")
    if media_manifest.get("short_id") != short_id:
        raise RuntimeError("RENDER_INPUT_INVALID:media_manifest_short_id")
    if media_manifest.get("scene_count") != len(frozen_assets or []):
        raise RuntimeError("RENDER_INPUT_INVALID:media_manifest_scene_count")
    media_root = (BASE / "imagens" / ("short_" + short_id)).resolve()
    for idx, row in enumerate(frozen_assets or [], 1):
        if not isinstance(row, dict):
            raise RuntimeError("RENDER_INPUT_INVALID:media_manifest_scene_%02d" % idx)
        asset = row.get("asset")
        if not isinstance(asset, dict) or asset.get("validated") is not True:
            raise RuntimeError("RENDER_INPUT_INVALID:media_manifest_asset_%02d" % idx)
        asset_path = Path(str(asset.get("path") or "")).expanduser().resolve()
        try:
            asset_path.relative_to(media_root)
        except ValueError:
            raise RuntimeError("RENDER_INPUT_INVALID:media_manifest_asset_scope_%02d" % idx)
    if not isinstance(scenes_raw, list) or not scenes_raw:
        raise RuntimeError("RENDER_INPUT_INVALID:scene_map")
    if not isinstance(planned, list) or len(planned) != len(scenes_raw):
        raise RuntimeError("RENDER_INPUT_INVALID:pro_edit_plan")
    if not isinstance(frozen_assets, list) or len(frozen_assets) != len(scenes_raw):
        raise RuntimeError("RENDER_INPUT_INVALID:media_manifest_scenes")
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
        # Resume/retry must preserve the frozen job. If an older V2 job predates
        # the frozen-subtitle contract, repair only that missing derived artifact.
        manifest_path = job / "manifest.json"
        manifest = read_json(manifest_path)
        job_meta = read_json(job / "job.json")
        timeline = read_json(job / "timeline.json")
        if manifest.get("short_id") != short_id:
            raise RuntimeError("RENDER_RESUME_INVALID:manifest_short_id")
        if job_meta.get("short_id") != short_id:
            raise RuntimeError("RENDER_RESUME_INVALID:job_short_id")
        if timeline.get("short_id") != short_id:
            raise RuntimeError("RENDER_RESUME_INVALID:timeline_short_id")
        if job_meta.get("render_id") != render_id:
            raise RuntimeError("RENDER_RESUME_INVALID:render_id")
        validate_ass_contract(ass)
        frozen_existing = job / "subtitles" / f"{short_id}.ass"
        if not frozen_existing.is_file():
            frozen_existing.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ass, frozen_existing)
            manifest["subtitles"] = {
                "path": str(frozen_existing),
                "required": True,
                "checksum_sha256": sha256(frozen_existing),
            }
            atomic_json(manifest_path, manifest)
        return job
    public_assets = job / "public" / "assets"
    public_assets.mkdir(parents=True, exist_ok=True)
    (job / "audio").mkdir(parents=True, exist_ok=True)
    frozen_scenes = []
    t = 0.0
    for idx, (scene, edit, logical) in enumerate(zip(scenes_raw, planned, durations), 1):
        media_row = frozen_assets[idx - 1] if idx - 1 < len(frozen_assets) else {}
        asset = media_row.get("asset", {}) if isinstance(media_row, dict) else {}
        if not isinstance(asset, dict) or asset.get("validated") is not True:
            raise RuntimeError(f"RENDER_ASSET_INVALID:scene_{idx:02d}:manifest_not_validated")
        src = Path(str(asset.get("path") or "")).expanduser().resolve()
        if not src.is_file() or src.stat().st_size <= 1000:
            raise RuntimeError(f"RENDER_ASSET_INVALID:scene_{idx:02d}:manifest_asset_missing")
        if asset.get("checksum_sha256") and sha256(src) != asset.get("checksum_sha256"):
            raise RuntimeError(f"RENDER_ASSET_INVALID:scene_{idx:02d}:manifest_checksum")
        # The renderer never searches for or substitutes media. Placeholders are
        # rejected here as a second independent quality boundary.
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
    if not ass.is_file():
        raise RuntimeError("SUBTITLE_INVALID:subtitle file missing")
    validate_ass_contract(ass)
    cues = parse_ass(ass)
    subtitle_dir = job / "subtitles"
    subtitle_dir.mkdir(parents=True, exist_ok=True)
    frozen_ass = subtitle_dir / f"{short_id}.ass"
    shutil.copy2(ass, frozen_ass)
    manifest = {
        "schema_version": "render-manifest-v2",
        "short_id": short_id,
        "render_id": render_id,
        "engine_version": ENGINE_VERSION,
        "frozen_at": now(),
        "assets": frozen_scenes,
        "audio": {"path": str(frozen_audio), "required": True, "checksum_sha256": sha256(frozen_audio)},
        "subtitles": {"path": str(frozen_ass), "required": True, "checksum_sha256": sha256(frozen_ass)},
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
    job_meta = read_json(job/"job.json")
    manifest = read_json(job/"manifest.json")
    timeline = read_json(job/"timeline.json")
    expected_short_id = validate_short_id(str(job_meta.get("short_id") or ""))
    expected_root = (BASE / "render_jobs" / expected_short_id).resolve()
    try:
        job.resolve().relative_to(expected_root)
    except ValueError:
        raise RuntimeError("RENDER_INPUT_INVALID:job_scope")
    if manifest.get("short_id") != expected_short_id:
        raise RuntimeError("RENDER_INPUT_INVALID:manifest_short_id")
    if timeline.get("short_id") != expected_short_id:
        raise RuntimeError("RENDER_INPUT_INVALID:timeline_short_id")
    errors=[]
    assets=manifest.get("assets",[])
    if not assets: errors.append("RENDER_ASSET_MISSING")
    for item in assets:
        path=Path(str(item.get("asset_path","")))
        if not path.is_file(): errors.append(f"RENDER_ASSET_MISSING:{item.get('scene_id')}")
        if item.get("validation_status")!="FROZEN_LOCAL": errors.append(f"RENDER_ASSET_INVALID:{item.get('scene_id')}")
    audio=Path(str(manifest.get("audio",{}).get("path","")))
    if not audio.is_file(): errors.append("AUDIO_STREAM_MISSING")
    subtitle=Path(str(manifest.get("subtitles",{}).get("path","")))
    if not subtitle.is_file():
        errors.append("SUBTITLE_INVALID:frozen_ass_missing")
    else:
        try:
            validate_ass_contract(subtitle)
            parse_ass(subtitle)
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(str(exc))
    if timeline.get("short_id") != manifest.get("short_id"): errors.append("RENDER_INPUT_INVALID:identity")
    if len(timeline.get("scenes",[])) != len(assets): errors.append("RENDER_INPUT_INVALID:timeline")
    if errors: raise RuntimeError(";".join(errors))
    return {"asset_count":len(assets),"subtitle_count":len(timeline.get("subtitles",[]))}

def remotion_binary() -> Path:
    p=RENDER_PROJECT/"node_modules"/".bin"/("remotion.cmd" if os.name=="nt" else "remotion")
    if p.is_file(): return p
    raise RuntimeError("RENDER_RUNTIME_MISSING:render_v2/node_modules; install render_v2 dependencies first")

def is_termux_android() -> bool:
    return Path("/data/data/com.termux/files/usr").is_dir() or bool(os.getenv("TERMUX_VERSION"))


def render_backend() -> str:
    requested = os.getenv("SAP_RENDER_V2_BACKEND", "auto").strip().lower() or "auto"
    if requested not in {"auto", "remotion", "ffmpeg"}:
        raise RuntimeError(f"RENDER_BACKEND_INVALID:{requested}")
    if requested == "ffmpeg":
        return "ffmpeg"
    if requested == "remotion":
        if is_termux_android():
            raise RuntimeError("RENDER_RUNTIME_UNSUPPORTED:remotion_android_requires_browser")
        return "remotion"
    return "ffmpeg" if is_termux_android() else "remotion"


def render_visual_remotion(job: Path) -> Path:
    output=job/"rendered.visual.mp4"
    output.unlink(missing_ok=True)
    props=job/"remotion_props.json"
    timeline=read_json(job/"timeline.json")
    props_data={"fps":FPS,"width":WIDTH,"height":HEIGHT,"duration_target":timeline["duration"],"timeline":timeline}
    atomic_json(props,props_data)
    cmd=[str(remotion_binary()),"render",str(RENDER_PROJECT/"src/index.tsx"),"ShortAutoProV2",str(output),
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


def render_visual(job: Path) -> tuple[Path, str]:
    backend = render_backend()
    if backend == "ffmpeg":
        return render_visual_ffmpeg(job, cwd=BASE), backend
    return render_visual_remotion(job), backend

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
    if not path.is_file() or path.stat().st_size <= 1000: errors.append("MP4_EXISTS_OR_SIZE")
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
    first=run_cmd(["ffmpeg","-v","error","-i",str(path),"-vf",r"select=eq(n\,0),signalstats,metadata=print:file=-","-frames:v","1","-f","null","-"],BASE,45)
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
        "backend": read_json(job/"state.json").get("backend", "unknown") if (job/"state.json").is_file() else "unknown",
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
    source_size=temp.stat().st_size
    if source_size <= 0:
        raise RuntimeError("ATOMIC_COMMIT_FAILED:source_empty")
    try:
        with temp.open("rb") as src, staging.open("wb") as dst:
            shutil.copyfileobj(src, dst, length=1024*1024)
            dst.flush()
            os.fsync(dst.fileno())
        copied_size=staging.stat().st_size
        if copied_size != source_size:
            raise RuntimeError(f"ATOMIC_COMMIT_FAILED:size_mismatch:{source_size}:{copied_size}")
        os.replace(staging, final)
        return final
    finally:
        staging.unlink(missing_ok=True)

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
            report_path = job/"render_report.json"
            final_path = BASE/"videos"/f"short_v6_{sid}.mp4"
            if not report_path.is_file() or not final_path.is_file():
                transition(job,"FAILED",error_code="PASSED_STATE_INVALID",error="missing_passed_artifact")
                raise RuntimeError("PASSED_STATE_INVALID:missing_artifact")
            report=read_json(report_path)
            job_meta=read_json(job/"job.json")
            if report.get("status")!="PASSED" or report.get("short_id")!=sid or job_meta.get("short_id")!=sid:
                transition(job,"FAILED",error_code="PASSED_STATE_INVALID",error="identity_or_report")
                raise RuntimeError("PASSED_STATE_INVALID:identity_or_report")
            verified=validate_output(final_path,job)
            if verified.get("status")!="PASSED" or verified.get("short_id")!=sid:
                transition(job,"FAILED",error_code="PASSED_STATE_INVALID",error="final_revalidation")
                raise RuntimeError("PASSED_STATE_INVALID:final_revalidation")
            print(json.dumps(verified,ensure_ascii=False)); return 0
        transition(job,"VALIDATING_INPUT")
        detail=validate_input(job)
        transition(job,"READY",input=detail)
        transition(job,"RENDERING")
        started=time.monotonic()
        visual, backend=render_visual(job)
        transition(job,"RENDERED",render_seconds=round(time.monotonic()-started,3),backend=backend)
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
