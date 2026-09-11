#!/usr/bin/env python3

import os
import json
import glob
from datetime import date


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
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

            return json.load(f)

    except Exception:

        return {}


scene_map = load(
    MAP
)

motion = load(
    MOTION
)


scenes = scene_map.get(
    "scenes",
    []
)

motion_scenes = motion.get(
    "scenes",
    []
)


files = []

if os.path.isdir(
    MEDIA
):

    files = [
        x
        for x in glob.glob(
            os.path.join(
                MEDIA,
                "scene_*"
            )
        )
        if os.path.splitext(
            x
        )[1].lower()
        in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".mp4"
        }
    ]


problemas = []


if len(scenes) != 12:

    problemas.append(
        f"scene_map={len(scenes)}"
    )


if len(files) != 12:

    problemas.append(
        f"midias={len(files)}"
    )


if len(motion_scenes) != 12:

    problemas.append(
        f"motion={len(motion_scenes)}"
    )


for i in range(
    1,
    13
):

    existe = any(
        os.path.basename(
            x
        ).startswith(
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
print("FINAL EDITORIAL GATE 5.0")
print("================================")
print()

print(
    f"Scene Map: {len(scenes)}/12"
)

print(
    f"Mídias: {len(files)}/12"
)

print(
    f"Motion Plan: {len(motion_scenes)}/12"
)

print()


if problemas:

    print(
        "EDITORIAL GATE: BLOCK"
    )

    for p in problemas:

        print(
            f"  - {p}"
        )

    raise SystemExit(1)


print(
    "EDITORIAL GATE: PASS"
)
print()
