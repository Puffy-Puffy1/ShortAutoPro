#!/usr/bin/env python3

import os
import json
import glob

BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

R = os.path.join(
    BASE,
    "roteiros"
)

reports = sorted(
    glob.glob(
        os.path.join(
            R,
            "visual_intelligence_6_*.json"
        )
    ),
    key=os.path.getmtime,
    reverse=True
)

if not reports:
    raise SystemExit(
        "ERRO: nenhum relatório VI6 encontrado."
    )

p = reports[0]

with open(
    p,
    "r",
    encoding="utf-8"
) as f:
    d = json.load(f)


print()
print("======================================")
print(" VI6.3 ACTIVE DECISION TEST")
print(" SEM DOWNLOAD / SEM VIDEO")
print("======================================")
print()

print(
    "RELATORIO:",
    p
)

print()

ativos = 0
fallbacks = 0
bloqueados = 0


for cena in d.get(
    "scenes",
    []
):

    numero = int(
        cena.get(
            "scene",
            0
        )
        or 0
    )

    winner = (
        cena.get(
            "winner"
        )
        or {}
    )

    classe = str(
        winner.get(
            "class",
            ""
        )
    ).upper()

    risk = str(
        winner.get(
            "risk",
            ""
        )
    ).upper()

    quality = str(
        winner.get(
            "quality_tier",
            ""
        )
    ).upper()

    blocked = bool(
        winner.get(
            "blocked",
            False
        )
    )

    truth_ok = bool(
        winner.get(
            "truth_ok",
            False
        )
    )

    fallback_5x = bool(
        cena.get(
            "fallback_to_5x",
            False
        )
    )


    reason = None


    if fallback_5x:
        reason = "quality_floor_fallback"

    elif blocked:
        reason = "blocked"

    elif (
        "MISLEADING" in classe
        or risk == "HIGH"
    ):
        reason = "risk_block"

    elif quality not in {
        "NORMAL",
        "CONTROLLED_FALLBACK"
    }:
        reason = (
            "quality_"
            + (
                quality
                or "missing"
            )
        )

    elif classe not in {
        "REAL_DOCUMENTARY",
        "SAFE_CONTEXT"
    }:
        reason = (
            "class_"
            + (
                classe
                or "unknown"
            )
        )

    elif (
        classe == "REAL_DOCUMENTARY"
        and not truth_ok
    ):
        reason = "truth_anchor_failed"


    print(
        f"CENA {numero:02d}"
    )

    print(
        "  WINNER:",
        winner.get(
            "fonte"
        ),
        "/",
        winner.get(
            "tipo"
        )
    )

    print(
        "  CLASS:",
        classe
    )

    print(
        "  RISK:",
        risk
    )

    print(
        "  QUALITY:",
        quality
    )

    print(
        "  TRUTH_OK:",
        truth_ok
    )


    if reason:

        fallbacks += 1

        if (
            reason == "blocked"
            or reason == "risk_block"
        ):
            bloqueados += 1

        print(
            "  DECISION=5X_FALLBACK"
        )

        print(
            "  REASON=",
            reason
        )

    else:

        ativos += 1

        print(
            "  DECISION=VI6"
        )

        print(
            "  REASON=vi6_active_winner"
        )

    print()


print("======================================")
print(" RESULTADO")
print("======================================")

print(
    "VI6 ACTIVE:",
    ativos
)

print(
    "5X FALLBACK:",
    fallbacks
)

print(
    "RISK/BLOCK:",
    bloqueados
)

print(
    "TOTAL:",
    ativos + fallbacks
)

print()
print("NENHUM DOWNLOAD FOI FEITO")
print("NENHUM VIDEO FOI GERADO")
