#!/usr/bin/env python3
"""Physical and semantic media master gate for ShortAutoPro 3.0.3."""
from __future__ import annotations

import glob
import hashlib
import json
import os
import subprocess
from datetime import date

BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

MEDIA_DIR = os.path.join(BASE, "imagens", f"short_{SHORT_ID}")
REPORT = os.path.join(BASE, "roteiros", f"media_quality_{SHORT_ID}.json")
SELECTION = os.path.join(BASE, "roteiros", f"media_selection_{SHORT_ID}.json")
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".mp4"}


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def probe(path):
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height,duration",
                "-show_entries", "format=duration", "-of", "json", path,
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        data = json.loads(out)
        if not isinstance(data, dict):
            return None
        streams = data.get("streams", [])
        if not isinstance(streams, list) or not streams:
            return None
        stream = streams[0]
        if not isinstance(stream, dict):
            return None
        width = int(stream.get("width") or 0)
        height = int(stream.get("height") or 0)
        fmt = data.get("format", {})
        if not isinstance(fmt, dict):
            fmt = {}
        duration = stream.get("duration") or fmt.get("duration") or 0
        try:
            duration = float(duration)
        except (TypeError, ValueError):
            duration = 0.0
        return {"width": width, "height": height, "duration": duration}
    except Exception:
        return None


def sha256(path):
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
    except Exception:
        return ""


def visual_hash(path):
    ext = os.path.splitext(path)[1].lower()
    command = ["ffmpeg", "-v", "error"]
    if ext == ".mp4":
        command.extend(["-ss", "0.30"])
    command.extend([
        "-i", path, "-frames:v", "1", "-vf", "scale=16:16,format=gray",
        "-f", "rawvideo", "-",
    ])
    try:
        raw = subprocess.check_output(command, stderr=subprocess.DEVNULL, timeout=20)
    except Exception:
        return ""
    if not raw:
        return ""
    values = list(raw[:256])
    if not values:
        return ""
    average = sum(values) / len(values)
    return "".join("1" if value >= average else "0" for value in values)


def hash_similarity(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(1 for x, y in zip(a, b) if x == y) / len(a)


def selection_index():
    data = read_json(SELECTION)
    scenes = data.get("scenes", []) if isinstance(data, dict) else []
    result = {}
    if not isinstance(scenes, list):
        return result
    for item in scenes:
        if not isinstance(item, dict):
            continue
        try:
            number = int(item.get("scene"))
        except (TypeError, ValueError):
            continue
        if 1 <= number <= QTD_CENAS:
            result[number] = item
    return result


files = []
if os.path.isdir(MEDIA_DIR):
    files = [
        path
        for path in glob.glob(os.path.join(MEDIA_DIR, "scene_*"))
        if os.path.splitext(path)[1].lower() in EXTS
    ]
files = sorted(files)

critical = []
warnings = []
assets = []
selections = selection_index()

if len(files) != QTD_CENAS:
    critical.append(f"media_count={len(files)}")

for i in range(1, QTD_CENAS + 1):
    prefix = f"scene_{i:02d}"
    found = [x for x in files if os.path.basename(x).startswith(prefix)]
    if len(found) != 1:
        critical.append(f"{prefix}_count={len(found)}")

# Every committed canonical download must be represented. Missing selection
# metadata generally means a blind local copy bypassed semantic verification.
if len(selections) != QTD_CENAS:
    critical.append(f"selection_manifest_count={len(selections)}")

for number in range(1, QTD_CENAS + 1):
    selected = selections.get(number)
    if not selected:
        continue
    provider = str(selected.get("provider", "") or "").strip().casefold()
    must_total = int(selected.get("must_total", 0) or 0)
    must_hits = int(selected.get("must_hits", 0) or 0)
    avoid_hits = int(selected.get("avoid_hits", 0) or 0)
    rescue = bool(selected.get("contextual_rescue"))

    if avoid_hits > 0:
        critical.append(f"scene_{number:02d}_avoid_hits={avoid_hits}")
    if provider == "local" and must_total > 0:
        critical.append(f"scene_{number:02d}_unverified_local_fallback")
    if must_total > 0 and must_hits <= 0:
        if rescue:
            warnings.append(f"scene_{number:02d}_contextual_rescue_without_must")
        else:
            critical.append(f"scene_{number:02d}_must_unverified")
    elif must_total > 0 and must_hits < must_total:
        warnings.append(f"scene_{number:02d}_partial_must={must_hits}/{must_total}")

for path in files:
    info = probe(path)
    basename = os.path.basename(path)
    if info is None:
        critical.append(f"probe_failed:{basename}")
        continue

    ext = os.path.splitext(path)[1].lower()
    if info["width"] <= 0 or info["height"] <= 0:
        critical.append(f"invalid_dimensions:{basename}")

    pixels = info["width"] * info["height"]
    if pixels < 320 * 180:
        critical.append(f"very_low_resolution:{basename}")
    elif pixels < 1280 * 720:
        warnings.append(f"low_resolution:{basename}")

    if ext == ".mp4":
        if info["duration"] < 0.40:
            critical.append(f"video_too_short:{basename}")
        elif info["duration"] < 1.0:
            warnings.append(f"short_video:{basename}")

    file_hash = sha256(path)
    if not file_hash:
        critical.append(f"hash_failed:{basename}")

    assets.append({
        "file": basename,
        "path": path,
        "width": info["width"],
        "height": info["height"],
        "duration": round(info["duration"], 3),
        "sha256": file_hash,
        "visual_hash": visual_hash(path),
    })

for i in range(len(assets)):
    for j in range(i + 1, len(assets)):
        first = assets[i]
        second = assets[j]
        if first["sha256"] and first["sha256"] == second["sha256"]:
            critical.append(f"exact_duplicate:{first['file']}={second['file']}")
            continue
        similarity = hash_similarity(first["visual_hash"], second["visual_hash"])
        if similarity >= 0.985:
            warnings.append(f"near_duplicate:{first['file']}~{second['file']}={similarity:.3f}")

videos = sum(1 for asset in assets if asset["file"].lower().endswith(".mp4"))
if videos < 3:
    warnings.append(f"low_motion_mix={videos}")

status = "BLOCK" if critical else "PASS"
report = {
    "short_id": SHORT_ID,
    "version": "5.3",
    "status": status,
    "expected_media_count": QTD_CENAS,
    "media_count": len(files),
    "selection_manifest_count": len(selections),
    "videos": videos,
    "photos": len(files) - videos,
    "critical": critical,
    "warnings": warnings,
    "selections": [selections[key] for key in sorted(selections)],
    "assets": assets,
}

os.makedirs(os.path.dirname(REPORT), exist_ok=True)
with open(REPORT, "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)

print()
print("================================")
print("MEDIA MASTER GATE 5.3")
print("================================")
print()
print(f"Mídias: {len(files)}/{QTD_CENAS}")
print(f"Seleções verificadas: {len(selections)}/{QTD_CENAS}")
print(f"Vídeos: {videos}")
print(f"Fotos: {len(files) - videos}")
print()

for item in warnings:
    print(f"AVISO: {item}")

if critical:
    print()
    for item in critical:
        print(f"ERRO: {item}")
    print()
    print("MEDIA MASTER GATE: BLOCK")
    raise SystemExit(1)

print()
print("MEDIA MASTER GATE: PASS")
print()
