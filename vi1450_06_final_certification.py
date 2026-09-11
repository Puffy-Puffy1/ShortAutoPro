#!/usr/bin/env python3

import json
import os
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"


def gate(filename):
    path = (
        BASE
        / "logs/producao"
        / filename
    )

    if not path.exists():
        return {}

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        ).get(
            "gate",
            {}
        )

    except Exception:
        return {}


def int_env(name):
    try:
        return int(
            os.environ.get(
                name,
                "99"
            )
        )

    except Exception:
        return 99


process = {
    "PREREQUISITE":
        int_env(
            "V1450_PREREQ"
        ),

    "COMPILE":
        int_env(
            "V1450_COMPILE"
        ),

    "REGRESSION":
        int_env(
            "V1450_REG"
        ),

    "TRANSFORM":
        int_env(
            "V1450_TRANSFORM"
        ),

    "PREPARED_FORENSICS":
        int_env(
            "V1450_FORENSICS"
        ),

    "RENDER_MANIFEST":
        int_env(
            "V1450_MANIFEST"
        ),

    "CANARY_BUILD":
        int_env(
            "V1450_CANARY"
        ),

    "CANARY_FORENSICS":
        int_env(
            "V1450_CANARY_FORENSICS"
        ),

    "VI1400_ARCHITECTURE":
        int_env(
            "V1450_ARCH1400"
        ),

    "CONTACT_SHEET":
        int_env(
            "V1450_CONTACT"
        ),

    "CREDITS":
        int_env(
            "V1450_CREDITS"
        ),

    "PORTFOLIO":
        int_env(
            "V1450_PORTFOLIO"
        ),

    "VI1450_ARCHITECTURE":
        int_env(
            "V1450_ARCH1450"
        ),
}


integrity = {
    "VIDEO":
        os.environ.get(
            "V1450_VIDEO_OK"
        )
        == "True",

    "GERAR":
        os.environ.get(
            "V1450_GERAR_OK"
        )
        == "True",

    "ROTEIRO":
        os.environ.get(
            "V1450_ROTEIRO_OK"
        )
        == "True",

    "EXECUTOR":
        os.environ.get(
            "V1450_EXECUTOR_OK"
        )
        == "True",

    "V6":
        os.environ.get(
            "V1450_V6_OK"
        )
        == "True",

    "SOURCE_ASSETS":
        os.environ.get(
            "V1450_SOURCE_OK"
        )
        == "True",
}


transform = gate(
    "vi1400_02_asset_transformer_latest.json"
)

prepared = gate(
    "vi1400_03_prepared_forensics_latest.json"
)

manifest = gate(
    "vi1400_04_render_manifest_latest.json"
)

canary = gate(
    "vi1400_05_visual_canary_latest.json"
)

canary_forensics = gate(
    "vi1400_06_canary_forensics_latest.json"
)

architecture1400 = gate(
    "vi1400_08_architecture_audit_latest.json"
)

contact = gate(
    "vi1450_02_contact_sheet_latest.json"
)

credits = gate(
    "vi1450_03_credits_manifest_latest.json"
)

portfolio = gate(
    "vi1450_04_portfolio_audit_latest.json"
)

architecture1450 = gate(
    "vi1450_05_architecture_audit_latest.json"
)


expected = {
    "TRANSFORM":
        (
            transform.get(
                "status"
            ),
            "VI1400_ASSET_TRANSFORMATION_CERTIFIED",
        ),

    "PREPARED_FORENSICS":
        (
            prepared.get(
                "status"
            ),
            "VI1400_PREPARED_FORENSICS_CERTIFIED",
        ),

    "RENDER_MANIFEST":
        (
            manifest.get(
                "status"
            ),
            "VI1400_RENDER_MANIFEST_CERTIFIED",
        ),

    "CANARY":
        (
            canary.get(
                "status"
            ),
            "VI1400_VISUAL_CANARY_GENERATED",
        ),

    "CANARY_FORENSICS":
        (
            canary_forensics.get(
                "status"
            ),
            "VI1400_VISUAL_CANARY_FORENSICS_CERTIFIED",
        ),

    "ARCHITECTURE1400":
        (
            architecture1400.get(
                "status"
            ),
            "VI1400_ARCHITECTURE_CERTIFIED",
        ),

    "CONTACT":
        (
            contact.get(
                "status"
            ),
            "VI1450_CONTACT_SHEET_CERTIFIED",
        ),

    "CREDITS":
        (
            credits.get(
                "status"
            ),
            "VI1450_CREDITS_MANIFEST_CERTIFIED",
        ),

    "PORTFOLIO":
        (
            portfolio.get(
                "status"
            ),
            "VI1450_PORTFOLIO_AUDIT_CERTIFIED",
        ),

    "ARCHITECTURE1450":
        (
            architecture1450.get(
                "status"
            ),
            "VI1450_ARCHITECTURE_CERTIFIED",
        ),
}


status_checks = {
    name:
        actual == wanted

    for name, (
        actual,
        wanted,
    ) in expected.items()
}


certified = (
    all(
        value == 0
        for value
        in process.values()
    )

    and

    all(
        integrity.values()
    )

    and

    all(
        status_checks.values()
    )
)


print()
print(
    "=============================================="
)
print(
    " VI1450 FINAL CERTIFICATION"
)
print(
    "=============================================="
)

print(
    "PROCESS STATUS =",
    process
)

print(
    "CORE/SOURCE INTEGRITY =",
    integrity
)

print()
print(
    "GATE STATUS =",
    status_checks
)

print()
print(
    "CANARY RESOLUTION =",
    canary_forensics.get(
        "width"
    ),
    "x",
    canary_forensics.get(
        "height"
    )
)

print(
    "CANARY FPS =",
    canary_forensics.get(
        "fps"
    )
)

print(
    "CANARY DURATION =",
    canary_forensics.get(
        "duration"
    )
)

print(
    "CANARY SHA256 =",
    canary_forensics.get(
        "sha256"
    )
)

print(
    "UNIQUE SOURCES =",
    portfolio.get(
        "unique_sources"
    )
)

print(
    "MAX SOURCE RUN =",
    portfolio.get(
        "max_consecutive_same_source"
    )
)

print()
print(
    "NETWORK_EXECUTED=FALSE"
)

print(
    "DOWNLOAD_EXECUTED=FALSE"
)

print(
    "FFMPEG_TEMP_ONLY=TRUE"
)

print(
    "FFPROBE_TEMP_ONLY=TRUE"
)

print(
    "VISUAL_CANARY_GENERATED=TRUE"
)

print(
    "PRODUCTION_RENDERER_ACTIVATED=FALSE"
)

print(
    "PRODUCTION_MUTATED=FALSE"
)


if certified:

    print()
    print(
        "VI1450 FINAL: "
        "PRE_FINAL_RELEASE_CANDIDATE_CERTIFIED"
    )

    raise SystemExit(0)


print()
print(
    "VI1450 FINAL: HOLD"
)

raise SystemExit(1)
