#!/usr/bin/env python3

import json
import subprocess

from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

PREPARED = (
    BASE
    / "temp/vi1400/prepared"
)

OUT = (
    BASE
    / "temp/vi1450/"
    "VI1450_contact_sheet.jpg"
)

REPORT = (
    BASE
    / "logs/producao/"
    "vi1450_02_contact_sheet_latest.json"
)


def main():
    missing = [
        number
        for number in range(
            1,
            13
        )
        if not (
            PREPARED
            /
            f"scene_{number:02d}.png"
        ).exists()
    ]

    if missing:
        raise SystemExit(
            "MISSING PREPARED SCENES:"
            + str(missing)
        )

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUT.unlink(
        missing_ok=True
    )

    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-framerate", "1",
        "-start_number", "1",
        "-i",
        str(
            PREPARED
            / "scene_%02d.png"
        ),
        "-vf",
        (
            "scale=270:480,"
            "tile=4x3:nb_frames=12"
        ),
        "-frames:v", "1",
        "-q:v", "2",
        str(OUT),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        print(
            result.stderr
        )

        raise SystemExit(
            result.returncode
        )

    valid = (
        OUT.exists()
        and
        OUT.stat().st_size
        > 10000
    )

    status = (
        "VI1450_CONTACT_SHEET_CERTIFIED"
        if valid
        else
        "HOLD"
    )

    report = {
        "version":
            "1450.00",

        "status":
            status,

        "path":
            str(
                OUT.resolve()
            )
            if OUT.exists()
            else None,

        "bytes":
            OUT.stat().st_size
            if OUT.exists()
            else 0,

        "scene_count":
            12,

        "production_mutation":
            False,
    }

    REPORT.write_text(
        json.dumps(
            {
                "gate":
                    report
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print()
    print(
        "=============================================="
    )
    print(
        " VI1450 CONTACT SHEET"
    )
    print(
        "=============================================="
    )

    print(
        "OUTPUT:",
        report[
            "path"
        ]
    )

    print(
        "BYTES:",
        report[
            "bytes"
        ]
    )

    print(
        "STATUS:",
        status
    )

    if not valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
