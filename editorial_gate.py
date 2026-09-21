#!/usr/bin/env python3

import os
import json
import glob
from datetime import date

BASE = os.path.abspath(
    os.path.expanduser(
        os.getenv("SHORTAUTOPRO_BASE", "~/ShortAutoPro")
    )
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

try:
    QTD_CENAS = int(
        os.getenv(
            "SHORT_QTD_CENAS",
            "12"
        )
    )
except ValueError:
    QTD_CENAS = 12

QTD_CENAS = max(
    6,
    min(QTD_CENAS, 20)
)

MEDIA = os.path.join(
    BASE,
    "imagens",
    f"short_{SHORT_ID}"
)

MAP = os.path.join(
    BASE,
    "roteiros",
    f"scene_map_{SHORT_ID}.json"
)

MOTION = os.path.join(
    BASE,
    "roteiros",
    f"motion_plan_{SHORT_ID}.json"
)


def load(path):

    try:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            dados = json.load(f)

        return dados if isinstance(dados, dict) else {}

    except Exception:

        return {}


scene_map = load(MAP)
motion = load(MOTION)

scenes = scene_map.get(
    "scenes",
    []
)

motion_scenes = motion.get(
    "scenes",
    []
)

if not isinstance(scenes, list):
    scenes = []

if not isinstance(motion_scenes, list):
    motion_scenes = []

files = []

if os.path.isdir(MEDIA):

    files = [
        x
        for x in glob.glob(
            os.path.join(
                MEDIA,
                "scene_*"
            )
        )
        if os.path.splitext(x)[1].lower()
        in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".mp4"
        }
    ]

problemas = []

if len(scenes) != QTD_CENAS:
    problemas.append(
        f"scene_map={len(scenes)}"
    )

if len(files) != QTD_CENAS:
    problemas.append(
        f"midias={len(files)}"
    )

if len(motion_scenes) != QTD_CENAS:
    problemas.append(
        f"motion={len(motion_scenes)}"
    )

for i in range(
    1,
    QTD_CENAS + 1
):

    existe = any(
        os.path.basename(x).startswith(
            f"scene_{i:02d}"
        )
        for x in files
    )

    if not existe:
        problemas.append(
            f"scene_{i:02d}_media_missing"
        )

print()
print("================================")
print("FINAL EDITORIAL GATE 5.1")
print("================================")
print()

print(
    f"Scene Map: {len(scenes)}/{QTD_CENAS}"
)
print(
    f"Mídias: {len(files)}/{QTD_CENAS}"
)
print(
    f"Motion Plan: {len(motion_scenes)}/{QTD_CENAS}"
)
print()

if problemas:

    print("EDITORIAL GATE: BLOCK")

    for p in problemas:
        print(
            f"  - {p}"
        )

    raise SystemExit(1)

print("EDITORIAL GATE: PASS")
print()
