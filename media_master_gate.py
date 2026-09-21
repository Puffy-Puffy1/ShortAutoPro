#!/usr/bin/env python3

import glob
import hashlib
import json
import os
import subprocess
from datetime import date

BASE = os.path.abspath(os.path.expanduser(os.getenv("SHORTAUTOPRO_BASE", "~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

MEDIA_DIR = os.path.join(BASE, "imagens", f"short_{SHORT_ID}")
REPORT = os.path.join(BASE, "roteiros", f"media_quality_{SHORT_ID}.json")
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".mp4"}
EDITORIAL_INDEX = os.path.join(MEDIA_DIR, ".editorial_reuse_index.json")


def editorial_scenes():
    try:
        with open(EDITORIAL_INDEX, "r", encoding="utf-8") as f:
            data = json.load(f)
        scenes = data.get("scenes", {}) if isinstance(data, dict) else {}
        if not isinstance(scenes, dict):
            return set()
        out = set()
        for key in scenes:
            try:
                out.add(int(key))
            except (TypeError, ValueError):
                pass
        return out
    except Exception:
        return set()


EDITORIAL_SCENES = editorial_scenes()



def atomic_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


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
        s = streams[0]
        if not isinstance(s, dict):
            return None
        width = int(s.get("width") or 0)
        height = int(s.get("height") or 0)
        formato = data.get("format", {})
        if not isinstance(formato, dict):
            formato = {}
        duration = s.get("duration") or formato.get("duration") or 0
        try:
            duration = float(duration)
        except (TypeError, ValueError):
            duration = 0.0
        return {"width": width, "height": height, "duration": duration}
    except Exception:
        return None


def sha256(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def visual_hash(path):
    ext = os.path.splitext(path)[1].lower()
    cmd = ["ffmpeg", "-v", "error"]
    if ext == ".mp4":
        cmd.extend(["-ss", "0.30"])
    cmd.extend([
        "-i", path, "-frames:v", "1", "-vf", "scale=16:16,format=gray",
        "-f", "rawvideo", "-",
    ])
    try:
        raw = subprocess.check_output(
            cmd,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
    except Exception:
        return ""
    if not raw:
        return ""
    values = list(raw[:256])
    if not values:
        return ""
    avg = sum(values) / len(values)
    return "".join("1" if x >= avg else "0" for x in values)


def hash_similarity(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(1 for x, y in zip(a, b) if x == y) / len(a)


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

if len(files) != QTD_CENAS:
    critical.append(f"media_count={len(files)}")

for i in range(1, QTD_CENAS + 1):
    prefix = f"scene_{i:02d}"
    found = [
        x for x in files
        if os.path.basename(x).startswith(prefix)
    ]
    if len(found) != 1:
        critical.append(f"{prefix}_count={len(found)}")

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
        a = assets[i]
        b = assets[j]
        if a["sha256"] and a["sha256"] == b["sha256"]:
            critical.append(f"exact_duplicate:{a['file']}={b['file']}")
            continue
        sim = hash_similarity(a["visual_hash"], b["visual_hash"])
        if sim >= 0.985:
            warnings.append(f"near_duplicate:{a['file']}~{b['file']}={sim:.3f}")

videos = sum(1 for x in assets if x["file"].lower().endswith(".mp4"))
if videos < 2:
    warnings.append(f"low_motion_mix={videos}")

if EDITORIAL_SCENES:
    warnings.append(
        "editorial_reuse_scenes="
        + ",".join(str(x) for x in sorted(EDITORIAL_SCENES))
    )

status = "BLOCK" if critical else "PASS"
report = {
    "short_id": SHORT_ID,
    "version": "5.2",
    "status": status,
    "expected_media_count": QTD_CENAS,
    "media_count": len(files),
    "videos": videos,
    "photos": len(files) - videos,
    "editorial_reuse_count": len(EDITORIAL_SCENES),
    "editorial_reuse_scenes": sorted(EDITORIAL_SCENES),
    "critical": critical,
    "warnings": warnings,
    "assets": assets,
}

os.makedirs(os.path.dirname(REPORT), exist_ok=True)
atomic_json(REPORT, report)

print()
print("================================")
print("MEDIA MASTER GATE 5.2")
print("================================")
print()
print(f"Mídias: {len(files)}/{QTD_CENAS}")
print(f"Vídeos: {videos}")
print(f"Fotos: {len(files) - videos}")
print(f"EditorialReuse: {len(EDITORIAL_SCENES)}")
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
