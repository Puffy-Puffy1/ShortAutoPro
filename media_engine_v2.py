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
ENGINE_VERSION = "2.0.1"

def _asset_name_is_forbidden(path: Path) -> bool:
    name = path.name.casefold()
    return any(token in name for token in ("slate", "placeholder", "neutral_editorial", "editorial_reuse"))

def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def _manifest_integrity(payload: dict[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("integrity_sha256", None)
    return hashlib.sha256(_canonical_json(unsigned)).hexdigest()


from media_provider_v2 import MediaProviderV2
from media_validator_v2 import validate as validate_asset

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
    if path.suffix.lower() in {".mp4", ".mov", ".webm", ".mkv"} and duration <= 0:
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


def _existing_asset_record(
    media_dir: Path,
    number: int,
    scene: dict[str, Any],
) -> dict[str, Any] | None:
    path = existing_asset(media_dir, number)
    sidecar = media_dir / f"scene_{number:02d}.json"
    if path is None or not sidecar.is_file():
        return None
    try:
        media_root = media_dir.resolve()
        resolved = path.resolve()
        resolved.relative_to(media_root)
        record = json.loads(sidecar.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            return None
        if _asset_name_is_forbidden(path):
            return None
        expected = str(record.get("checksum_sha256") or "")
        must_total = len(scene.get("must_have") or [])
        if (
            not expected
            or int(record.get("must_total", 0)) != must_total
            or (
                record.get("short_id") is not None
                and str(record.get("short_id") or "") != media_dir.name.removeprefix("short_")
            )
            or (
                record.get("scene_number") is not None
                and int(record.get("scene_number", 0) or 0) not in {0, number}
            )
        ):
            return None
        if sha256(path) != expected:
            return None
        probe = ffprobe_asset(path)
        record["path"] = str(path)
        record["probe"] = probe
        record["validated"] = True
        return record
    except (OSError, ValueError, TypeError, RuntimeError):
        return None


def _write_asset_sidecar(media_dir: Path, number: int, asset: dict[str, Any]) -> None:
    atomic_json(media_dir / f"scene_{number:02d}.json", asset)


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
        "license": str(candidate.get("license") or ""),
        "provenance": candidate.get("provenance", {}),
        "probe": probe,
        "validated": True,
        "short_id": str(candidate.get("_sap_short_id") or ""),
        "scene_number": int(candidate.get("_sap_scene_number", 0) or 0),
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

    candidates = PROVIDER.search(query, must, avoid, segmento=segment, visual_mode=visual_mode)
    for candidate in candidates:
        candidate["_sap_must_total"] = len(must)
        candidate["_sap_short_id"] = short_id
        candidate["_sap_scene_number"] = number
    strict = PROVIDER.prepare(candidates, len(must))
    verification_mode = "strict_must" if strict else ""
    if not strict and must:
        relaxed = PROVIDER.search(query, [], avoid, segmento=segment, visual_mode=visual_mode)
        for candidate in relaxed:
            candidate["_sap_must_total"] = len(must)
            candidate["_sap_short_id"] = short_id
            candidate["_sap_scene_number"] = number
            candidate["verification_mode"] = "query_relaxed"
            candidate["verification_note"] = (
                f"strict_must={len(must)};"
                f"verified_must={int(candidate.get('must_hits', 0) or 0)}"
            )
        strict = [
            c for c in relaxed
            if int(c.get("avoid_hits", 0) or 0) == 0
            and int(c.get("must_hits", 0) or 0) >= 1
            and float(c.get("score", 0) or 0) >= 45
        ]
        verification_mode = "query_relaxed" if strict else ""
    failures = []

    # Per-asset failover: a bad download/validation never terminates the scene
    # while another verified provider candidate remains available.
    for candidate in strict:
        try:
            ok, destination, download_meta = PROVIDER.download(candidate, number, short_id)
            if not ok or not destination:
                failures.append(f"{candidate.get('fonte','?')}:DOWNLOAD_FAILED")
                continue
            validation = validate_asset(destination)
            path = Path(destination)
            record = _candidate_record(candidate, path, validation["probe"])
            record["checksum_sha256"] = validation["sha256"]
            record["verification_mode"] = str(candidate.get("verification_mode") or verification_mode or "strict_must")
            record["verification_note"] = str(candidate.get("verification_note") or "")
            return record
        except Exception as exc:
            failures.append(f"{candidate.get('fonte','?')}:{type(exc).__name__}")

    # Local Library is an explicit provider in the Router. Keep this secondary
    # compatibility path for libraries created by the previous pipeline.
    local = _local_library_asset(query, must, avoid)
    if local is not None:
        return local

    if not candidates:
        raise RuntimeError(f"MEDIA_INCOMPLETE:scene_{number:02d}:providers_empty")
    if not strict:
        raise RuntimeError(
            f"MEDIA_INCOMPLETE:scene_{number:02d}:no_verified_asset:"
            f"must={','.join(must) or '-'}"
        )
    raise RuntimeError(
        f"MEDIA_DOWNLOAD_FAILED:scene_{number:02d}:"
        + (";".join(failures) if failures else "no_candidate_attempted")
    )




def build_manifest(short_id: str) -> dict[str, Any]:
    if not short_id or not __import__("re").fullmatch(r"[A-Za-z0-9._-]+", short_id) or ".." in short_id:
        raise RuntimeError("MEDIA_INPUT_INVALID:short_id")
    scenes = load_scene_map(short_id)
    media_dir = BASE / "imagens" / f"short_{short_id}"
    media_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for number, scene in enumerate(scenes, 1):
        existing = _existing_asset_record(media_dir, number, scene)
        if existing is not None:
            records.append(existing)
            continue
        record = acquire_scene(short_id, number, scene, media_dir)
        record["short_id"] = short_id
        record["scene_number"] = number
        _write_asset_sidecar(media_dir, number, record)
        records.append(record)
    scenes_out = [
        {
            "scene_id": str(scene.get("scene_id", scene.get("scene", number))),
            "scene_number": number,
            "asset": record,
        }
        for number, (scene, record) in enumerate(zip(scenes, records), 1)
    ]
    manifest = {
        "schema_version": "media-manifest-v2",
        "engine_version": ENGINE_VERSION,
        "short_id": short_id,
        "immutable": True,
        "scene_count": len(scenes_out),
        "scenes": scenes_out,
    }
    manifest["integrity_sha256"] = _manifest_integrity(manifest)
    atomic_json(BASE / "manifests" / f"media_{short_id}.json", manifest)
    return manifest


def main(short_id: str | None = None) -> int:
    if short_id is None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--short-id", required=True)
        args = parser.parse_args()
        short_id = args.short_id
    manifest = build_manifest(short_id)
    print(
        f"MEDIA_ENGINE_V2=PASS short_id={short_id} "
        f"scenes={manifest['scene_count']} assets={len(manifest['scenes'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
