#!/usr/bin/env python3
"""Validate that an approved release still belongs to the exact current MP4."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
MANIFESTS = BASE / "manifests"
VIDEOS = BASE / "videos"


def load_dict(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def validate(short_id: str) -> tuple[bool, str]:
    sid = str(short_id or "").strip()
    if not sid:
        return False, "short_id_empty"

    manifest = load_dict(MANIFESTS / f"{sid}.json")
    quality = load_dict(MANIFESTS / f"{sid}_quality.json")
    release = load_dict(MANIFESTS / f"{sid}_release.json")
    if not manifest or not quality or not release:
        return False, "release_files_missing_or_invalid"

    if str(manifest.get("short_id", "")) != sid:
        return False, "manifest_short_id_mismatch"
    if str(quality.get("short_id", "")) != sid:
        return False, "quality_short_id_mismatch"
    if str(release.get("short_id", "")) != sid:
        return False, "release_short_id_mismatch"
    if str(manifest.get("status", "")).upper() != "QUALITY_PASS":
        return False, "manifest_not_quality_pass"
    if quality.get("approved") is not True:
        return False, "quality_not_approved"
    if str(release.get("decision", "")).upper() not in {"PUBLISH", "ACCEPTABLE"}:
        return False, "release_not_approved"

    video = manifest.get("video", {}) if isinstance(manifest.get("video"), dict) else {}
    expected = (VIDEOS / f"short_v6_{sid}.mp4").resolve()
    try:
        configured = Path(str(video.get("path", "") or "")).expanduser().resolve()
    except Exception:
        return False, "manifest_video_path_invalid"
    if configured != expected:
        return False, "manifest_video_path_mismatch"

    try:
        stat = expected.stat()
    except OSError:
        return False, "video_missing"

    if stat.st_size < 500_000:
        return False, "video_too_small"
    if int(video.get("size_bytes", 0) or 0) != int(stat.st_size):
        return False, "video_size_identity_mismatch"
    if int(video.get("mtime_ns", 0) or 0) != int(stat.st_mtime_ns):
        return False, "video_mtime_identity_mismatch"

    return True, "PASS"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--short-id", required=True)
    args = parser.parse_args()
    ok, reason = validate(args.short_id)
    print(
        json.dumps(
            {"short_id": args.short_id, "status": "PASS" if ok else "BLOCK", "reason": reason},
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
