#!/usr/bin/env python3
"""Persistent local asset index for ShortAutoPro.

Indexes only media already accepted by Media Master Gate. It does not bypass
provider licensing, MUST verification or the canonical media selector.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", "").strip()
R = BASE / "roteiros"
STATE = BASE / ".sap_state" / "asset_library.json"
REPORTS = BASE / "reports" / "assets"


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def scene_number(filename: str) -> int | None:
    try:
        stem = Path(filename).stem
        if not stem.startswith("scene_"):
            return None
        return int(stem.split("_")[1])
    except Exception:
        return None


def quality(asset: dict[str, Any]) -> float:
    width = int(asset.get("width") or 0)
    height = int(asset.get("height") or 0)
    pixels = width * height
    if pixels >= 1920 * 1080:
        return 100.0
    if pixels >= 1280 * 720:
        return 92.0
    if pixels >= 854 * 480:
        return 78.0
    if pixels >= 320 * 180:
        return 60.0
    return 0.0


def index_short(sid: str) -> dict[str, Any]:
    media = load(R / f"media_quality_{sid}.json", {})
    scene_doc = load(R / f"scene_map_{sid}.json", {})
    if not isinstance(media, dict) or str(media.get("status", "")).upper() != "PASS":
        raise ValueError("Media Master Gate precisa estar PASS antes de indexar assets")
    scenes_raw = scene_doc.get("scenes", []) if isinstance(scene_doc, dict) else []
    scenes = {
        int(x.get("scene", 0)): x for x in scenes_raw
        if isinstance(x, dict) and int(x.get("scene", 0) or 0) > 0
    }
    library = load(STATE, {"version": "ASSET_LIBRARY_1.0", "assets": []})
    if not isinstance(library, dict):
        library = {"version": "ASSET_LIBRARY_1.0", "assets": []}
    existing = library.get("assets", [])
    if not isinstance(existing, list):
        existing = []
    by_hash = {
        str(item.get("sha256")): item for item in existing
        if isinstance(item, dict) and item.get("sha256")
    }
    indexed = []
    for asset in media.get("assets", []):
        if not isinstance(asset, dict) or not asset.get("sha256"):
            continue
        number = scene_number(str(asset.get("file", "")))
        scene = scenes.get(number or -1, {})
        digest = str(asset["sha256"])
        previous = by_hash.get(digest, {})
        record = {
            "asset_id": f"sha256:{digest[:16]}",
            "sha256": digest,
            "visual_hash": asset.get("visual_hash", ""),
            "file": asset.get("file"),
            "path": asset.get("path"),
            "width": int(asset.get("width") or 0),
            "height": int(asset.get("height") or 0),
            "duration": asset.get("duration", 0),
            "source": scene.get("source") or previous.get("source") or "unknown",
            "license": scene.get("license") or previous.get("license") or "unknown",
            "entities": scene.get("must_have", []) if isinstance(scene.get("must_have"), list) else [],
            "location": scene.get("location", ""),
            "year_or_era": scene.get("era", ""),
            "visual_style": scene.get("shot_type", ""),
            "quality": quality(asset),
            "used_count": int(previous.get("used_count", 0)) + (0 if sid in previous.get("short_ids", []) else 1),
            "short_ids": sorted(set((previous.get("short_ids", []) if isinstance(previous.get("short_ids"), list) else []) + [sid]))[-100:],
            "last_used_at": now(),
        }
        by_hash[digest] = record
        indexed.append(record)
    library["assets"] = list(by_hash.values())[-10000:]
    library["updated_at"] = now()
    atomic(STATE, library)

    first_candidates = []
    for item in indexed:
        number = scene_number(str(item.get("file", "")))
        if number is None or number > 3:
            continue
        scene = scenes.get(number, {})
        score = item["quality"] * 0.62
        score += 16.0 if number == 1 else (8.0 if number == 2 else 3.0)
        if str(scene.get("shot_type", "")) in {"close_up","detail","portrait","document"}:
            score += 10.0
        if scene.get("must_have"):
            score += 8.0
        first_candidates.append({
            "asset_id": item["asset_id"],
            "file": item["file"],
            "scene": number,
            "score": round(min(100.0, score), 1),
        })
    first_candidates.sort(key=lambda x: x["score"], reverse=True)
    report = {
        "short_id": sid,
        "version": "ASSET_LIBRARY_1.0",
        "indexed": len(indexed),
        "library_size": len(library["assets"]),
        "first_frame": {
            "candidates": first_candidates,
            "recommended": first_candidates[0] if first_candidates else None,
            "first_frame_score": first_candidates[0]["score"] if first_candidates else 0.0,
        },
    }
    atomic(REPORTS / f"assets_{sid}.json", report)
    print(
        f"SHORTAUTO_ASSET_LIBRARY=PASS indexed={report['indexed']} "
        f"library={report['library_size']} first_frame={report['first_frame']['first_frame_score']}"
    )
    return report


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def verified_candidate(scene: dict[str, Any], *, exclude_short_id: str = "") -> dict[str, Any] | None:
    """Return a previously gate-approved local asset that satisfies scene metadata.

    This is deliberately strict: unknown source/license, missing files, low
    quality, missing MUST entities, or mismatched location/era are rejected.
    It never invents semantic evidence from a filename.
    """
    library = load(STATE, {"assets": []})
    assets = library.get("assets", []) if isinstance(library, dict) else []
    if not isinstance(assets, list):
        return None

    must_raw = scene.get("must_have", []) if isinstance(scene, dict) else []
    must = {_norm(x) for x in must_raw if _norm(x)} if isinstance(must_raw, list) else set()
    if not must:
        return None

    wanted_location = _norm(scene.get("location", ""))
    wanted_era = _norm(scene.get("era", ""))
    candidates: list[dict[str, Any]] = []

    for item in assets:
        if not isinstance(item, dict):
            continue
        path = Path(str(item.get("path", "") or ""))
        try:
            if not path.is_file() or path.stat().st_size <= 1000:
                continue
        except OSError:
            continue
        if _norm(item.get("source")) in {"", "unknown"}:
            continue
        if _norm(item.get("license")) in {"", "unknown"}:
            continue
        try:
            if float(item.get("quality", 0) or 0) < 78.0:
                continue
        except (TypeError, ValueError):
            continue
        entities_raw = item.get("entities", [])
        entities = {_norm(x) for x in entities_raw if _norm(x)} if isinstance(entities_raw, list) else set()
        if not must.issubset(entities):
            continue
        if wanted_location and _norm(item.get("location")) != wanted_location:
            continue
        if wanted_era and _norm(item.get("year_or_era")) != wanted_era:
            continue
        short_ids = item.get("short_ids", []) if isinstance(item.get("short_ids"), list) else []
        if exclude_short_id and short_ids and set(short_ids) == {exclude_short_id}:
            continue
        candidates.append(item)

    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            -float(item.get("quality", 0) or 0),
            int(item.get("used_count", 0) or 0),
            str(item.get("last_used_at", "")),
        )
    )
    return dict(candidates[0])


def status() -> dict[str, Any]:
    library = load(STATE, {"assets": []})
    assets = library.get("assets", []) if isinstance(library, dict) else []
    return {
        "version": "ASSET_LIBRARY_1.0",
        "assets": len(assets) if isinstance(assets, list) else 0,
        "path": str(STATE),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    idx = sub.add_parser("index")
    idx.add_argument("--short-id", default=SID)
    sub.add_parser("status")
    args = parser.parse_args()
    if args.command == "status":
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    sid = str(args.short_id or "").strip()
    if not sid:
        print("ERRO ASSET LIBRARY: SHORT_ID vazio")
        return 1
    try:
        index_short(sid)
    except Exception as exc:
        print(f"ERRO ASSET LIBRARY: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
