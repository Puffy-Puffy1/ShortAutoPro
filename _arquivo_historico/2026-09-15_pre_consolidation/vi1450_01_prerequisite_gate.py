#!/usr/bin/env python3

import json
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"


REQUIRED = {
    "VI1300": (
        BASE
        / "logs/producao/"
        "vi1300_00_visual_preparation_director_latest.json",
        "VI1300_VISUAL_PREPARATION_CERTIFIED",
    ),

    "VI1290": (
        BASE
        / "logs/producao/"
        "vi1290_00_asset_readiness_latest.json",
        "VI1290_ASSET_READINESS_CERTIFIED",
    ),

    "VI1280": (
        BASE
        / "logs/producao/"
        "vi1280_00_asset_forensics_latest.json",
        "VI1280_ASSET_FORENSICS_CERTIFIED",
    ),
}


def main():
    failed = []

    print()
    print(
        "=============================================="
    )
    print(
        " VI1450 PREREQUISITE GATE"
    )
    print(
        "=============================================="
    )

    for name, (
        path,
        expected,
    ) in REQUIRED.items():

        try:
            status = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            ).get(
                "gate",
                {}
            ).get(
                "status"
            )

        except Exception:
            status = "MISSING"

        ok = (
            status == expected
        )

        print(
            name,
            "=",
            status,
            "|",
            "PASS"
            if ok
            else "FAIL"
        )

        if not ok:
            failed.append(
                name
            )

    print(
        "FAILED:",
        failed
    )

    if failed:
        raise SystemExit(1)

    print(
        "VI1450_PREREQUISITES_CERTIFIED"
    )


if __name__ == "__main__":
    main()
