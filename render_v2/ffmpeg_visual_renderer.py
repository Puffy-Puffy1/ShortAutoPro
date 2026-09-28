#!/usr/bin/env python3
"""FFmpeg-native visual backend for ShortAutoPro Render Engine V2.

This is not the legacy renderer. It consumes the exact frozen Render V2
timeline and produces the visual MP4 with native FFmpeg, allowing Termux/
Android to execute Render V2 without a Chromium dependency.

The backend is intentionally acquisition-free and fail-closed:
frozen assets -> per-scene clips -> concat -> frozen ASS burn-in.
"""
from __future__ import annotations

import math
import os
import shutil
from pathlib import Path
from typing import Any

from subprocess_guard import run_group


def _read_json(path: Path) -> dict[str, Any]:
    import json
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be object")
    return data


def _run(cmd: list[str], cwd: Path, timeout: int):
    return run_group(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def _even(value: float) -> int:
    return max(2, int(math.floor(value / 2.0) * 2))


def _safe_zoom(scene: dict[str, Any]) -> float:
    effect = scene.get("effect") or {}
    try:
        z1 = float(effect.get("zoom_start", 1.0) or 1.0)
        z2 = float(effect.get("zoom_end", z1) or z1)
    except (TypeError, ValueError):
        z1 = z2 = 1.0
    return max(1.0, min(1.18, max(z1, z2)))


def _scene_filter(scene: dict[str, Any]) -> str:
    zoom = _safe_zoom(scene)
    scaled_w = _even(1080 * zoom)
    scaled_h = _even(1920 * zoom)
    return (
        f"scale={scaled_w}:{scaled_h}:force_original_aspect_ratio=increase,"
        f"crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
        "setsar=1,format=yuv420p"
    )


def _write_concat_file(path: Path, clips: list[Path]) -> None:
    def quote(value: str) -> str:
        return value.replace("'", "'\\''")

    path.write_text(
        "".join(f"file '{quote(str(p.resolve()))}'\n" for p in clips),
        encoding="utf-8",
    )


def _render_scene(
    *,
    scene: dict[str, Any],
    index: int,
    public_dir: Path,
    output: Path,
    cwd: Path,
    timeout: int,
) -> None:
    asset = public_dir / str(scene["asset"])
    duration = float(scene["duration"])
    if duration <= 0:
        raise RuntimeError(f"RENDER_INPUT_INVALID:scene_{index:02d}:duration")
    if not asset.is_file():
        raise RuntimeError(f"RENDER_ASSET_MISSING:scene_{index:02d}")

    asset_type = str(scene.get("asset_type", "image")).lower()
    filt = _scene_filter(scene)

    if asset_type == "image":
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-framerate", "30", "-t", f"{duration:.6f}",
            "-i", str(asset), "-vf", filt, "-r", "30",
            "-frames:v", str(max(1, round(duration * 30))),
            "-an", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", os.getenv("SAP_RENDER_V2_CRF", "20"),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
        ]
    elif asset_type == "video":
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-stream_loop", "-1", "-i", str(asset), "-t", f"{duration:.6f}",
            "-vf", filt, "-r", "30", "-an", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", os.getenv("SAP_RENDER_V2_CRF", "20"),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
        ]
    else:
        raise RuntimeError(
            f"RENDER_ASSET_INVALID:scene_{index:02d}:asset_type={asset_type}"
        )

    proc = _run(cmd, cwd, timeout)
    if proc.returncode != 0:
        raise RuntimeError(
            f"FFMPEG_SCENE_FAILED:scene_{index:02d}:{(proc.stderr or '')[-1400:]}"
        )
    if not output.is_file() or output.stat().st_size <= 1000:
        raise RuntimeError(f"FFMPEG_SCENE_FAILED:scene_{index:02d}:empty_output")


def render_visual_ffmpeg(job: Path, *, cwd: Path) -> Path:
    """Render the frozen V2 timeline using FFmpeg only."""
    timeline = _read_json(job / "timeline.json")
    scenes = timeline.get("scenes") or []
    if not scenes:
        raise RuntimeError("RENDER_INPUT_INVALID:no_scenes")

    public_dir = job / "public"
    work = job / "ffmpeg_visual"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)

    timeout = int(os.getenv("SAP_RENDER_V2_FFMPEG_SCENE_TIMEOUT_SECONDS", "600"))
    clips: list[Path] = []

    for index, scene in enumerate(scenes, 1):
        clip = work / f"scene_{index:03d}.mp4"
        _render_scene(
            scene=scene,
            index=index,
            public_dir=public_dir,
            output=clip,
            cwd=cwd,
            timeout=timeout,
        )
        clips.append(clip)

    concat_file = work / "concat.txt"
    _write_concat_file(concat_file, clips)

    visual = job / "rendered.visual.mp4"
    visual.unlink(missing_ok=True)

    concat_proc = _run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-c", "copy", "-movflags", "+faststart", str(visual),
        ],
        cwd,
        int(os.getenv("SAP_RENDER_V2_FFMPEG_CONCAT_TIMEOUT_SECONDS", "900")),
    )
    if concat_proc.returncode != 0:
        raise RuntimeError(
            f"FFMPEG_CONCAT_FAILED:{(concat_proc.stderr or '')[-1600:]}"
        )
    if not visual.is_file() or visual.stat().st_size <= 1000:
        raise RuntimeError("FFMPEG_CONCAT_FAILED:empty_output")

    subtitle_path = job / "subtitles" / f"{job.parent.name}.ass"
    if not subtitle_path.is_file():
        raise RuntimeError("SUBTITLE_INVALID:frozen_ass_missing")

    subtitled = job / "rendered.visual.subtitled.mp4"
    subtitle_filter = f"ass={subtitle_path.as_posix()}"
    subtitle_proc = _run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(visual), "-vf", subtitle_filter, "-r", "30",
            "-c:v", "libx264", "-preset", "veryfast",
            "-crf", os.getenv("SAP_RENDER_V2_CRF", "20"),
            "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart",
            str(subtitled),
        ],
        cwd,
        int(os.getenv("SAP_RENDER_V2_FFMPEG_SUBTITLE_TIMEOUT_SECONDS", "900")),
    )
    if subtitle_proc.returncode != 0:
        raise RuntimeError(
            f"SUBTITLE_RENDER_FAILED:{(subtitle_proc.stderr or '')[-1600:]}"
        )
    if not subtitled.is_file() or subtitled.stat().st_size <= 1000:
        raise RuntimeError("SUBTITLE_RENDER_FAILED:empty_output")
    os.replace(subtitled, visual)
    return visual
