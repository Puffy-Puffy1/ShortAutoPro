#!/usr/bin/env python3
"""Create an independent media-quality report from the frozen Media Engine V2 manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from media_validator_v2 import validate as validate_asset

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", Path.home() / "ShortAutoPro")).resolve()


def canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def manifest_integrity(payload: dict[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("integrity_sha256", None)
    return hashlib.sha256(canonical_json(unsigned)).hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def evaluate(short_id: str) -> dict[str, Any]:
    manifest_path = BASE / "manifests" / f"media_{short_id}.json"
    scene_map_path = BASE / "roteiros" / f"scene_map_{short_id}.json"
    errors: list[str] = []
    neutral_editorial_scenes: list[int] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        manifest = {}
        errors.append(f"manifest_unavailable:{type(exc).__name__}")
    try:
        scene_map = json.loads(scene_map_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        scene_map = {}
        errors.append(f"scene_map_unavailable:{type(exc).__name__}")

    scenes = manifest.get("scenes", []) if isinstance(manifest, dict) else []
    expected_scenes = scene_map.get("scenes", []) if isinstance(scene_map, dict) else []
    if not isinstance(scenes, list) or not isinstance(expected_scenes, list) or not expected_scenes:
        scenes = scenes if isinstance(scenes, list) else []
        expected_scenes = expected_scenes if isinstance(expected_scenes, list) else []
        errors.append("scene_inventory_invalid")
    if len(scenes) != len(expected_scenes):
        errors.append(f"scene_count_mismatch:manifest={len(scenes)}:scene_map={len(expected_scenes)}")
    if isinstance(manifest, dict):
        if manifest.get("short_id") != short_id:
            errors.append("manifest_short_id_mismatch")
        if manifest.get("integrity_sha256") != manifest_integrity(manifest):
            errors.append("manifest_integrity_mismatch")

    used_hashes: set[str] = set()
    validated_count = 0
    for index, entry in enumerate(scenes, start=1):
        if not isinstance(entry, dict) or not isinstance(entry.get("asset"), dict):
            errors.append(f"scene_{index:02d}:asset_record_invalid")
            continue
        asset = entry["asset"]
        path_text = str(asset.get("path") or "")
        path = Path(path_text).expanduser()
        try:
            resolved = path.resolve()
            resolved.relative_to(BASE)
        except (OSError, ValueError):
            errors.append(f"scene_{index:02d}:asset_path_outside_base")
            continue
        if not path.is_file():
            errors.append(f"scene_{index:02d}:asset_missing")
            continue
        if any(token in path.name.casefold() for token in ("slate", "placeholder", "neutral_editorial", "editorial_reuse")):
            neutral_editorial_scenes.append(index)
            errors.append(f"scene_{index:02d}:editorial_placeholder_forbidden")
        try:
            validation = validate_asset(path)
        except Exception as exc:
            errors.append(f"scene_{index:02d}:asset_validation:{type(exc).__name__}")
            continue
        checksum = str(validation.get("sha256") or "")
        expected_checksum = str(asset.get("checksum_sha256") or "")
        if not checksum or checksum != expected_checksum:
            errors.append(f"scene_{index:02d}:checksum_mismatch")
            continue
        if checksum in used_hashes:
            errors.append(f"scene_{index:02d}:duplicate_asset_checksum")
        used_hashes.add(checksum)
        must_total = int(asset.get("must_total", 0) or 0)
        must_hits = int(asset.get("must_hits", 0) or 0)
        if must_total > 0 and must_hits != must_total:
            errors.append(f"scene_{index:02d}:must_evidence_incomplete:{must_hits}/{must_total}")
        probe = validation.get("probe", {})
        if not isinstance(probe, dict) or int(probe.get("width", 0) or 0) <= 0 or int(probe.get("height", 0) or 0) <= 0:
            errors.append(f"scene_{index:02d}:invalid_dimensions")
        if not errors or not any(item.startswith(f"scene_{index:02d}:") for item in errors):
            validated_count += 1

    return {
        "schema_version": "media-quality-report-v1",
        "short_id": short_id,
        "status": "PASS" if not errors and len(scenes) == len(expected_scenes) and validated_count == len(scenes) else "FAIL",
        "expected_scenes": len(expected_scenes),
        "validated_scenes": validated_count,
        "neutral_editorial_scenes": neutral_editorial_scenes,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--short-id", required=True)
    args = parser.parse_args()
    short_id = str(args.short_id).strip()
    if not short_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for char in short_id) or ".." in short_id:
        print("MEDIA_QUALITY_REPORT=FAIL reason=invalid_short_id")
        return 2
    report = evaluate(short_id)
    output = BASE / "roteiros" / f"media_quality_{short_id}.json"
    atomic_json(output, report)
    print(
        f"MEDIA_QUALITY_REPORT={report['status']} "
        f"scenes={report['validated_scenes']}/{report['expected_scenes']} "
        f"errors={len(report['errors'])} report={output}"
    )
    for error in report["errors"]:
        print(f"MEDIA_QUALITY_ERROR={error}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
