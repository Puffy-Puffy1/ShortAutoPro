#!/usr/bin/env python3

import os
import glob
import json
import hashlib
import subprocess
from datetime import date


BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())

MEDIA_DIR = os.path.join(
    BASE,
    "imagens",
    f"short_{SHORT_ID}"
)

REPORT = os.path.join(
    BASE,
    "roteiros",
    f"media_quality_{SHORT_ID}.json"
)


EXTS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".mp4"
}


def probe(path):

    try:

        out = subprocess.check_output(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries",
                "stream=width,height,duration",
                "-show_entries",
                "format=duration",
                "-of", "json",
                path
            ],
            text=True,
            stderr=subprocess.DEVNULL
        )

        data = json.loads(out)

        streams = data.get(
            "streams",
            []
        )

        if not streams:
            return None

        s = streams[0]

        width = int(
            s.get("width") or 0
        )

        height = int(
            s.get("height") or 0
        )

        duration = (
            s.get("duration")
            or data.get(
                "format",
                {}
            ).get(
                "duration"
            )
            or 0
        )

        try:
            duration = float(duration)
        except Exception:
            duration = 0.0

        return {
            "width": width,
            "height": height,
            "duration": duration
        }

    except Exception:

        return None


def sha256(path):

    h = hashlib.sha256()

    try:

        with open(path, "rb") as f:

            while True:

                chunk = f.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                h.update(chunk)

        return h.hexdigest()

    except Exception:

        return ""


def visual_hash(path):

    ext = os.path.splitext(
        path
    )[1].lower()

    cmd = [
        "ffmpeg",
        "-v", "error"
    ]

    if ext == ".mp4":
        cmd.extend(
            [
                "-ss", "0.30"
            ]
        )

    cmd.extend(
        [
            "-i", path,
            "-frames:v", "1",
            "-vf",
            "scale=16:16,format=gray",
            "-f", "rawvideo",
            "-"
        ]
    )

    try:

        raw = subprocess.check_output(
            cmd,
            stderr=subprocess.DEVNULL,
            timeout=20
        )

    except Exception:

        return ""


    if not raw:
        return ""


    values = list(
        raw[:256]
    )

    if not values:
        return ""


    avg = sum(values) / len(values)

    return "".join(
        "1" if x >= avg else "0"
        for x in values
    )


def hash_similarity(a, b):

    if not a or not b:
        return 0.0

    size = min(
        len(a),
        len(b)
    )

    if not size:
        return 0.0

    equal = sum(
        1
        for i in range(size)
        if a[i] == b[i]
    )

    return equal / size


files = []

if os.path.isdir(
    MEDIA_DIR
):

    for path in glob.glob(
        os.path.join(
            MEDIA_DIR,
            "scene_*"
        )
    ):

        if os.path.splitext(
            path
        )[1].lower() in EXTS:

            files.append(path)


files = sorted(files)

critical = []
warnings = []
assets = []


if len(files) != 12:

    critical.append(
        f"media_count={len(files)}"
    )


for i in range(1, 13):

    prefix = f"scene_{i:02d}"

    found = [
        x
        for x in files
        if os.path.basename(x).startswith(
            prefix
        )
    ]

    if len(found) != 1:

        critical.append(
            f"{prefix}_count={len(found)}"
        )


for path in files:

    info = probe(path)

    if info is None:

        critical.append(
            f"probe_failed:{os.path.basename(path)}"
        )

        continue


    ext = os.path.splitext(
        path
    )[1].lower()


    if (
        info["width"] <= 0
        or info["height"] <= 0
    ):

        critical.append(
            f"invalid_dimensions:{os.path.basename(path)}"
        )


    pixels = (
        info["width"]
        * info["height"]
    )


    if pixels < 320 * 180:

        critical.append(
            f"very_low_resolution:{os.path.basename(path)}"
        )

    elif pixels < 1280 * 720:

        warnings.append(
            f"low_resolution:{os.path.basename(path)}"
        )


    if ext == ".mp4":

        if info["duration"] < 0.40:

            critical.append(
                f"video_too_short:{os.path.basename(path)}"
            )

        elif info["duration"] < 1.0:

            warnings.append(
                f"short_video:{os.path.basename(path)}"
            )


    assets.append(
        {
            "file":
                os.path.basename(path),

            "path":
                path,

            "width":
                info["width"],

            "height":
                info["height"],

            "duration":
                round(
                    info["duration"],
                    3
                ),

            "sha256":
                sha256(path),

            "visual_hash":
                visual_hash(path)
        }
    )


# =====================================================
# EXACT DUPLICATES
# =====================================================

for i in range(
    len(assets)
):

    for j in range(
        i + 1,
        len(assets)
    ):

        a = assets[i]
        b = assets[j]


        if (
            a["sha256"]
            and a["sha256"]
            == b["sha256"]
        ):

            critical.append(
                "exact_duplicate:"
                f"{a['file']}="
                f"{b['file']}"
            )

            continue


        sim = hash_similarity(
            a["visual_hash"],
            b["visual_hash"]
        )


        if sim >= 0.985:

            warnings.append(
                "near_duplicate:"
                f"{a['file']}~"
                f"{b['file']}="
                f"{sim:.3f}"
            )


videos = sum(
    1
    for x in assets
    if x["file"].lower().endswith(
        ".mp4"
    )
)


if videos < 2:
    warnings.append(
        f"low_motion_mix={videos}"
    )


status = (
    "BLOCK"
    if critical
    else "PASS"
)


report = {
    "short_id": SHORT_ID,
    "version": "5.1",
    "status": status,
    "media_count": len(files),
    "videos": videos,
    "photos": len(files) - videos,
    "critical": critical,
    "warnings": warnings,
    "assets": assets
}


with open(
    REPORT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        report,
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print("================================")
print("MEDIA MASTER GATE 5.1")
print("================================")
print()

print(
    f"Mídias: {len(files)}/12"
)

print(
    f"Vídeos: {videos}"
)

print(
    f"Fotos: {len(files) - videos}"
)

print()


for item in warnings:
    print(
        f"AVISO: {item}"
    )


if critical:

    print()

    for item in critical:
        print(
            f"ERRO: {item}"
        )

    print()
    print("MEDIA MASTER GATE: BLOCK")

    raise SystemExit(1)


print()
print("MEDIA MASTER GATE: PASS")
print()
