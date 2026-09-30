#!/usr/bin/env python3
"""ShortAutoPro Media Engine V2.

Single responsibility:
  scene requirements -> provider acquisition -> asset validation -> frozen manifest.

This module deliberately does not render, edit, encode, publish, or create SHORT_IDs.
It uses the repository's mature provider primitives as an acquisition compatibility
boundary; the production entrypoint calls this engine directly and never invokes the legacy
media controller.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", Path.home() / "ShortAutoPro")).resolve()
MEDIA_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"}
ENGINE_VERSION = "2.0.0"

from media_provider_v2 import MediaProviderV2

PROVIDER = MediaProviderV2()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        tmp = ""
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ffprobe_asset(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"MEDIA_NOT_FOUND:{path}")
    if path.stat().st_size <= 1000:
        raise RuntimeError(f"MEDIA_INVALID:too_small:{path.name}")
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries",
            "stream=codec_type,codec_name,width,height,avg_frame_rate,nb_frames",
            "-show_entries", "format=format_name,duration,size",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"MEDIA_VALIDATION_FAILED:{path.name}")
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"MEDIA_VALIDATION_FAILED:invalid_probe:{path.name}") from exc
    streams = data.get("streams", [])
    if not isinstance(streams, list) or not streams:
        raise RuntimeError(f"MEDIA_INVALID:no_stream:{path.name}")
    video = next((x for x in streams if isinstance(x, dict) and x.get("codec_type") == "video"), None)
    if not isinstance(video, dict):
        raise RuntimeError(f"MEDIA_INVALID:no_video:{path.name}")
    width, height = int(video.get("width") or 0), int(video.get("height") or 0)
    if width <= 0 or height <= 0:
        raise RuntimeError(f"MEDIA_INVALID:invalid_dimensions:{path.name}")
    fmt = data.get("format", {}) if isinstance(data, dict) else {}
    duration = float(fmt.get("duration") or 0.0)
    if duration < 0:
        raise RuntimeError(f"MEDIA_INVALID:invalid_duration:{path.name}")
    return {
        "codec": str(video.get("codec_name") or ""),
        "width": width,
        "height": height,
        "avg_frame_rate": str(video.get("avg_frame_rate") or ""),
        "duration": duration,
        "format": str(fmt.get("format_name") or ""),
        "size_bytes": int(path.stat().st_size),
    }


def load_scene_map(short_id: str) -> list[dict[str, Any]]:
    path = BASE / "roteiros" / f"scene_map_{short_id}.json"
    if not path.is_file():
        raise RuntimeError("MEDIA_INPUT_INVALID:scene_map_missing")
    raw = json.loads(path.read_text(encoding="utf-8"))
    scenes = raw.get("scenes") if isinstance(raw, dict) else raw
    if not isinstance(scenes, list) or not scenes:
        raise RuntimeError("MEDIA_INPUT_INVALID:scene_map_empty")
    rows = [x for x in scenes if isinstance(x, dict)]
    if len(rows) != len(scenes):
        raise RuntimeError("MEDIA_INPUT_INVALID:scene_map_scene_not_object")
    return rows


def existing_asset(media_dir: Path, number: int) -> Path | None:
    matches = sorted(
        p for p in media_dir.glob(f"scene_{number:02d}*")
        if p.is_file() and p.suffix.lower() in MEDIA_EXTS
    )
    return matches[0] if len(matches) == 1 else None


def _candidate_record(candidate: dict[str, Any], path: Path, probe: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": str(candidate.get("fonte") or candidate.get("source") or ""),
        "asset_id": str(candidate.get("id") or ""),
        "url": str(candidate.get("url") or ""),
        "asset_type": "video" if str(candidate.get("tipo", "")).lower() in {"vídeo", "video"} else "image",
        "description": str(candidate.get("descricao") or ""),
        "evidence_class": str(candidate.get("evidence_class") or ""),
        "must_hits": int(candidate.get("must_hits", 0) or 0),
        "must_total": int(candidate.get("_sap_must_total", 0) or 0),
        "path": str(path),
        "checksum_sha256": sha256(path),
        "probe": probe,
        "validated": True,
    }


def _local_library_asset(query: str, must: list[str], avoid: list[str]) -> dict[str, Any] | None:
    try:
        from shortauto_asset_library import search_candidates
        candidates = search_candidates(query, must, avoid, limit=3)
    except Exception:
        return None
    for candidate in candidates:
        path = Path(str(candidate.get("local_path") or "")).expanduser()
        expected = str(candidate.get("sha256") or "")
        if not path.is_file() or not expected:
            continue
        try:
            if sha256(path) != expected:
                continue
            probe = ffprobe_asset(path)
        except RuntimeError:
            continue
        record = dict(candidate)
        record["fonte"] = "LocalLibrary"
        record["_sap_must_total"] = len(must)
        record["must_hits"] = len(must)
        return _candidate_record(record, path, probe)
    return None


def acquire_scene(short_id: str, number: int, scene: dict[str, Any], media_dir: Path) -> dict[str, Any]:
    query = str(scene.get("query") or scene.get("busca") or scene.get("segment") or "").strip()
    must = [str(x).strip() for x in (scene.get("must_have") or []) if str(x).strip()]
    avoid = [str(x).strip() for x in (scene.get("avoid") or []) if str(x).strip()]
    visual_mode = str(scene.get("visual_mode") or scene.get("modo_visual") or "").strip()
    segment = str(scene.get("segment") or "").strip()
    if not query:
        raise RuntimeError(f"MEDIA_INPUT_INVALID:scene_{number:02d}:query_empty")

    # Provider acquisition is bounded and sequential. LocalLibrary is only a
    # fallback after provider search/verification/download has failed.
    os.environ.setdefault("SAP_MEDIA_PARALLEL_PROVIDERS", "0")
    os.environ.setdefault("SAP_MEDIA_PROVIDER_WORKERS", "1")

    candidates = PROVIDER.search(
        query, must, avoid, segmento=segment, visual_mode=visual_mode
    )
    total_must = len(must)
    strict = PROVIDER.prepare(candidates, total_must) if candidates else []
    if strict:
        candidate = strict[0]
        ok, destination = PROVIDER.download(candidate, number)
        if ok and destination:
            path = Path(destination)
            probe = ffprobe_asset(path)
            return _candidate_record(candidate, path, probe)

    local = _local_library_asset(query, must, avoid)
    if local is not None:
        return local

    if not candidates:
        raise RuntimeError(
            f"MEDIA_INCOMPLETE:scene_{number:02d}:providers_empty_and_library_miss"
        )
    if not strict:
        raise RuntimeError(
            f"MEDIA_INCOMPLETE:scene_{number:02d}:no_verified_asset:"
            f"must={','.join(must) or '-'}"
        )
    raise RuntimeError(f"MEDIA_DOWNLOAD_FAILED:scene_{number:02d}")

def build_manifest(short_id: str, scenes: list[dict[str, Any]], assets: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "media-manifest-v2",
        "version": 2,
        "engine": "Media Engine V2",
        "engine_version": ENGINE_VERSION,
        "short_id": short_id,
        "immutable": True,
        "created_at_epoch": __import__("time").time(),
        "scenes": [
            {
                "scene_id": str(scene.get("scene_id", scene.get("scene", i))),
                "scene_number": i,
                "query": str(scene.get("query") or scene.get("busca") or ""),
                "must_have": [str(x) for x in (scene.get("must_have") or [])],
                "avoid": [str(x) for x in (scene.get("avoid") or [])],
                "asset": asset,
            }
            for i, (scene, asset) in enumerate(zip(scenes, assets), 1)
        ],
    }


def validate_manifest(path: Path, short_id: str, expected: int) -> None:
    if not path.is_file():
        raise RuntimeError("MEDIA_MANIFEST_MISSING")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "media-manifest-v2" or data.get("short_id") != short_id:
        raise RuntimeError("MEDIA_MANIFEST_INVALID")
    rows = data.get("scenes")
    if not isinstance(rows, list) or len(rows) != expected:
        raise RuntimeError(f"MEDIA_MANIFEST_INCOMPLETE:{len(rows) if isinstance(rows, list) else 0}/{expected}")
    for row in rows:
        asset = row.get("asset", {}) if isinstance(row, dict) else {}
        if not asset.get("validated") or not asset.get("checksum_sha256"):
            raise RuntimeError("MEDIA_MANIFEST_UNVALIDATED")
        path_value = Path(str(asset.get("path") or ""))
        if not path_value.is_file() or sha256(path_value) != asset.get("checksum_sha256"):
            raise RuntimeError("MEDIA_MANIFEST_ASSET_IDENTITY_MISMATCH")
        ffprobe_asset(path_value)


def run(short_id: str) -> Path:
    scenes = load_scene_map(short_id)
    media_dir = BASE / "imagens" / f"short_{short_id}"
    media_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = BASE / "manifests" / f"media_{short_id}.json"

    # A completed frozen manifest is authoritative on resume.
    if manifest_path.is_file():
        validate_manifest(manifest_path, short_id, len(scenes))
        print(f"MEDIA_ENGINE_V2=FROZEN_MANIFEST_PASS short_id={short_id}")
        return manifest_path

    assets: list[dict[str, Any]] = []
    for number, scene in enumerate(scenes, 1):
        existing = existing_asset(media_dir, number)
        if existing is not None:
            try:
                probe = ffprobe_asset(existing)
                assets.append({
                    "source": str(scene.get("source") or ""),
                    "asset_id": "",
                    "url": "",
                    "asset_type": "video" if existing.suffix.lower() in {".mp4",".mov",".webm",".mkv"} else "image",
                    "description": "",
                    "evidence_class": "EXISTING_VALIDATED_INPUT",
                    "must_hits": 0,
                    "must_total": len(scene.get("must_have") or []),
                    "path": str(existing),
                    "checksum_sha256": sha256(existing),
                    "probe": probe,
                    "validated": True,
                })
                continue
            except RuntimeError:
                pass
        assets.append(acquire_scene(short_id, number, scene, media_dir))

    manifest = build_manifest(short_id, scenes, assets)
    atomic_json(manifest_path, manifest)
    validate_manifest(manifest_path, short_id, len(scenes))
    print(f"MEDIA_ENGINE_V2=PASS short_id={short_id} scenes={len(assets)} manifest={manifest_path}")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--short-id", required=True)
    args = parser.parse_args()
    try:
        run(args.short_id)
    except Exception as exc:
        print(f"MEDIA_ENGINE_V2=FAIL error={type(exc).__name__}:{exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
