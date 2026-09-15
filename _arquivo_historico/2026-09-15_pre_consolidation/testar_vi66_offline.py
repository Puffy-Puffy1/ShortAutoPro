#!/usr/bin/env python3

import glob
import json
import os

from vi6_6_active_brain import (
    evaluate,
    reset_state
)


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)


reports = sorted(
    glob.glob(
        os.path.join(
            BASE,
            "roteiros",
            "visual_intelligence_6_*.json"
        )
    ),
    key=os.path.getmtime,
    reverse=True
)


if not reports:

    raise SystemExit(
        "ERRO: relatório VI6 não encontrado."
    )


path = reports[0]


with open(
    path,
    "r",
    encoding="utf-8"
) as f:

    data = json.load(f)


reset_state()


docs = 0
safe = 0
fallback = 0
blocked = 0
total = 0


print()
print(
    "======================================"
)
print(
    " VI6.6 RETROSPECTIVE AUDIT"
)
print(
    " SEM DOWNLOAD / SEM VIDEO"
)
print(
    "======================================"
)
print(
    "REPORT:",
    path
)
print()


for scene in data.get(
    "scenes",
    []
):

    total += 1

    number = int(
        scene.get(
            "scene",
            total
        )
        or total
    )


    pool = []

    winner = (
        scene.get("winner")
        or {}
    )


    if winner:
        pool.append(winner)


    pool.extend(
        (
            scene.get("top")
            or []
        )[:10]
    )


    valid = []


    for item in pool:

        result = evaluate(
            item,
            scene,
            scene
        )

        if result is not None:
            valid.append(result)


    valid.sort(
        key=lambda x:
            x["score"],
        reverse=True
    )


    if not valid:

        fallback += 1
        blocked += 1

        print(
            f"CENA {number:02d} "
            f"-> 5X_FALLBACK "
            f"| no-safe-candidate"
        )

        continue


    best = valid[0]


    if best["score"] < 52:

        fallback += 1

        print(
            f"CENA {number:02d} "
            f"-> 5X_FALLBACK "
            f"| score={best['score']}"
        )

        continue


    if (
        best["class"]
        == "REAL_DOCUMENTARY"
    ):

        docs += 1

    else:

        safe += 1


    item = best["item"]


    print(
        f"CENA {number:02d} "
        f"-> VI6.6 "
        f"| {best['class']} "
        f"| {item.get('fonte', '?')} / "
        f"{item.get('tipo', '?')} "
        f"| role={best['role']} "
        f"| score={best['score']} "
        f"| anchor={best['anchor_ratio']}"
    )


print()
print(
    "======================================"
)
print(
    " RESUMO VI6.6 OFFLINE"
)
print(
    "======================================"
)
print(
    "REAL_DOCUMENTARY:",
    docs
)
print(
    "SAFE_CONTEXT:",
    safe
)
print(
    "5X_FALLBACK:",
    fallback
)
print(
    "HARD/NO-SAFE:",
    blocked
)
print(
    "TOTAL:",
    total
)
print()
print(
    "DOWNLOADS NOVOS: 0"
)
print(
    "VIDEOS GERADOS: 0"
)
print()
