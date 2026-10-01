#!/usr/bin/env python3
"""Independent media validation boundary for Media Engine V2."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS
MIN_BYTES = 1000

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _signature_ok(path: Path) -> bool:
    head = path.read_bytes()[:32]
    ext = path.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        return head.startswith(b"\xff\xd8\xff")
    if ext == ".png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ext == ".webp":
        return head.startswith(b"RIFF") and head[8:12] == b"WEBP"
    # Containers are validated by ffprobe below.
    return ext in VIDEO_EXTS

def probe(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height,avg_frame_rate,nb_frames",
         "-show_entries", "format=format_name,duration,size",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=False, timeout=30,
    )
    if proc.returncode != 0:
        raise ValueError("PROBE_FAIL")
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("PROBE_INVALID_JSON") from exc
    streams = data.get("streams")
    if not isinstance(streams, list) or not streams:
        raise ValueError("NO_STREAM")
    video = next((x for x in streams if isinstance(x, dict) and x.get("codec_type") == "video"), None)
    if not video:
        raise ValueError("NO_VIDEO_STREAM")
    width, height = int(video.get("width") or 0), int(video.get("height") or 0)
    if width <= 0 or height <= 0:
        raise ValueError("INVALID_DIMENSIONS")
    fmt = data.get("format") if isinstance(data.get("format"), dict) else {}
    duration = float(fmt.get("duration") or 0.0)
    if duration <= 0:
        raise ValueError("INVALID_DURATION")
    return {
        "codec": str(video.get("codec_name") or ""),
        "width": width,
        "height": height,
        "duration": duration,
        "avg_frame_rate": str(video.get("avg_frame_rate") or ""),
        "format": str(fmt.get("format_name") or ""),
        "size_bytes": path.stat().st_size,
    }

def validate(path: str | Path) -> dict[str, Any]:
    p = Path(path).expanduser()
    if not p.is_file():
        raise ValueError("MEDIA_NOT_FOUND")
    size = p.stat().st_size
    if size <= MIN_BYTES:
        raise ValueError("MEDIA_TOO_SMALL")
    if p.suffix.lower() not in MEDIA_EXTS:
        raise ValueError("UNSUPPORTED_EXTENSION")
    if not _signature_ok(p):
        raise ValueError("CONTENT_SIGNATURE_MISMATCH")
    metadata = probe(p)
    digest = sha256(p)
    return {"path": str(p), "sha256": digest, "probe": metadata, "validated": True}
