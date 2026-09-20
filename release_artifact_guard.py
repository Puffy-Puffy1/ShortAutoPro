#!/usr/bin/env python3
"""Validate that an approved release still belongs to the exact current MP4."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
MANIFESTS = BASE / "manifests"
VIDEOS = BASE / "videos"
ROTEIROS = BASE / "roteiros"
CREDITS = BASE / "credits"


def file_sha256(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return ""


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

    manifest_path = MANIFESTS / f"{sid}.json"
    quality_input = quality.get("input_identity", {}) if isinstance(quality.get("input_identity"), dict) else {}
    manifest_sha_for_quality = file_sha256(manifest_path)
    if (
        not manifest_sha_for_quality
        or quality_input.get("production_manifest_sha256") != manifest_sha_for_quality
    ):
        return False, "quality_manifest_identity_mismatch"

    if str(release.get("decision", "")).upper() not in {"PUBLISH", "ACCEPTABLE"}:
        return False, "release_not_approved"

    input_identity = release.get("input_identity", {}) if isinstance(release.get("input_identity"), dict) else {}
    quality_path = MANIFESTS / f"{sid}_quality.json"
    manifest_sha = file_sha256(manifest_path)
    quality_sha = file_sha256(quality_path)
    if not manifest_sha or input_identity.get("production_manifest_sha256") != manifest_sha:
        return False, "release_manifest_identity_mismatch"
    if not quality_sha or input_identity.get("final_quality_sha256") != quality_sha:
        return False, "release_quality_identity_mismatch"

    artifact_identity = manifest.get("artifact_identity", {}) if isinstance(manifest.get("artifact_identity"), dict) else {}
    inputs = artifact_identity.get("input_artifacts", {}) if isinstance(artifact_identity.get("input_artifacts"), dict) else {}
    topic_path_raw = str(inputs.get("topic_path", "") or "")
    try:
        topic_path = Path(topic_path_raw).expanduser().resolve()
    except Exception:
        return False, "manifest_topic_path_invalid"
    allowed_topics = {
        (ROTEIROS / f"used_topic_{sid}.txt").resolve(),
        (ROTEIROS / f"topic_{sid}.txt").resolve(),
    }
    if topic_path not in allowed_topics:
        return False, "manifest_topic_path_mismatch"

    critical_inputs = {
        "topic_sha256": topic_path,
        "hook_sha256": ROTEIROS / f"hook_{sid}.txt",
        "script_sha256": ROTEIROS / f"short_{sid}.txt",
        "source_sha256": ROTEIROS / f"fonte_{sid}.txt",
        "publish_sha256": ROTEIROS / f"publish_{sid}.json",
        "publish_integrity_sha256": ROTEIROS / f"publish_integrity_{sid}.json",
        "source_ledger_sha256": CREDITS / f"ledger_{sid}.json",
    }
    for key, path in critical_inputs.items():
        current_sha = file_sha256(path)
        expected_sha = str(inputs.get(key, "") or "")
        if not current_sha or current_sha != expected_sha:
            return False, f"manifest_input_identity_mismatch:{key}"

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
