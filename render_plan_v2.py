#!/usr/bin/env python3
"""Deterministic RenderPlan V2 producer.

Boundary:
  frozen SceneMap + immutable MediaManifest + audio/captions -> RenderPlan.
The module never acquires media and never renders.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", Path.home() / "ShortAutoPro")).resolve()


def canonical_json(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def integrity(payload: dict) -> str:
    unsigned = dict(payload)
    unsigned.pop("integrity_sha256", None)
    return hashlib.sha256(canonical_json(unsigned)).hexdigest()


def atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        tmp = ""
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def validate_short_id(value: str) -> str:
    sid = str(value or "").strip()
    if not sid or len(sid) > 96 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", sid) or ".." in sid:
        raise RuntimeError("RENDER_PLAN_INVALID:short_id")
    return sid


def main(short_id: str | None = None) -> int:
    import argparse

    if short_id is None:
        ap = argparse.ArgumentParser()
        ap.add_argument("--short-id", required=True)
        args = ap.parse_args()
        short_id = args.short_id

    sid = validate_short_id(short_id)
    scene_path = BASE / "manifests" / f"scene_map_{sid}.json"
    media_path = BASE / "manifests" / f"media_{sid}.json"
    out = BASE / "roteiros" / f"pro_edit_plan_{sid}.json"
    audio_path = BASE / "audios" / f"short_{sid}.mp3"
    caption_path = BASE / "videos" / f"short_{sid}.ass"

    if not scene_path.is_file():
        raise RuntimeError("RENDER_PLAN_INVALID:frozen_scene_map_missing")
    if not media_path.is_file():
        raise RuntimeError("RENDER_PLAN_INVALID:media_manifest_missing")

    scene_map = json.loads(scene_path.read_text(encoding="utf-8"))
    if (
        scene_map.get("schema_version") != "SCENE_MAP_FROZEN_1.0"
        or scene_map.get("short_id") != sid
        or scene_map.get("mutable_upstream_closed") is not True
    ):
        raise RuntimeError("RENDER_PLAN_INVALID:frozen_scene_map")

    scenes = scene_map.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise RuntimeError("RENDER_PLAN_INVALID:frozen_scene_map")

    media = json.loads(media_path.read_text(encoding="utf-8"))
    if media.get("short_id") != sid or media.get("schema_version") != "media-manifest-v2":
        raise RuntimeError("RENDER_PLAN_INVALID:media_manifest_identity")
    media_rows = media.get("scenes")
    if not isinstance(media_rows, list) or len(media_rows) != len(scenes):
        raise RuntimeError("RENDER_PLAN_INVALID:media_manifest_scene_count")
    expected_media_integrity = str(media.get("integrity_sha256") or "")
    if not expected_media_integrity:
        raise RuntimeError("RENDER_PLAN_INVALID:media_manifest_integrity_missing")
    if expected_media_integrity != integrity(media):
        raise RuntimeError("RENDER_PLAN_INVALID:media_manifest_integrity")

    if not audio_path.is_file():
        raise RuntimeError("RENDER_PLAN_INVALID:audio_missing")
    if not caption_path.is_file():
        raise RuntimeError("RENDER_PLAN_INVALID:captions_missing")

    plan = {
        "schema_version": "render-plan-v2",
        "short_id": sid,
        "immutable": True,
        "frozen_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "inputs": {
            "scene_map": str(scene_path),
            "media_manifest": str(media_path),
            "audio": str(audio_path),
            "captions": str(caption_path),
        },
        "scenes": [],
    }

    seen_ids: set[str] = set()
    for i, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            raise RuntimeError(f"RENDER_PLAN_INVALID:scene_{i:02d}")
        scene_id = str(scene.get("scene_id", scene.get("scene", i))).strip()
        if not scene_id or scene_id in seen_ids:
            raise RuntimeError(f"RENDER_PLAN_INVALID:scene_id_{i:02d}")
        seen_ids.add(scene_id)

        row = media_rows[i - 1]
        asset = row.get("asset", {}) if isinstance(row, dict) else {}
        if not isinstance(asset, dict) or asset.get("validated") is not True:
            raise RuntimeError(f"RENDER_PLAN_INVALID:scene_{i:02d}:media_not_validated")

        plan["scenes"].append(
            {
                "scene_id": scene_id,
                "media": {
                    "path": str(asset.get("path") or ""),
                    "checksum_sha256": str(asset.get("checksum_sha256") or ""),
                    "provider": str(asset.get("source") or ""),
                    "asset_id": str(asset.get("asset_id") or ""),
                },
                "audio": {"path": str(audio_path)},
                "caption": {"path": str(caption_path), "required": True},
                "pace_multiplier": 1.0,
                "zoom_start": 1.0,
                "zoom_end": 1.04,
                "pan": "center",
                "cut_style": "editorial_cut",
                "transition_duration": 0.0,
            }
        )

    plan["integrity_sha256"] = integrity(plan)
    atomic(out, plan)
    print(f"RENDER_PLAN_V2=PASS short_id={sid} scenes={len(plan['scenes'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
