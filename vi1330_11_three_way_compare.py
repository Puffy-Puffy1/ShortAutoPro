#!/usr/bin/env python3

import subprocess
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

A = (
    BASE
    / "videos/canary/vi1310/"
    "VI1310_contact_sheet.jpg"
)

B = (
    BASE
    / "videos/canary/vi1320/"
    "VI1320_contact_sheet.jpg"
)

C = (
    BASE
    / "videos/canary/vi1330/"
    "VI1330_contact_sheet.jpg"
)

OUT = (
    BASE
    / "videos/canary/vi1330/"
    "VI1310_VS_VI1320_VS_VI1330.jpg"
)


def main():
    for path in [
        A,
        B,
        C,
    ]:

        if not path.exists():

            raise SystemExit(
                "COMPARE INPUT MISSING: "
                + str(
                    path
                )
            )


    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(A),
        "-i",
        str(B),
        "-i",
        str(C),
        "-filter_complex",
        (
            "[0:v]"
            "scale=540:-1"
            "[a];"

            "[1:v]"
            "scale=540:-1"
            "[b];"

            "[2:v]"
            "scale=540:-1"
            "[c];"

            "[a][b][c]"
            "hstack=inputs=3"
            "[out]"
        ),
        "-map",
        "[out]",
        "-frames:v",
        "1",
        "-q:v",
        "3",
        str(OUT),
    ]


    result = subprocess.run(
        command,
        check=False,
    )


    if (
        result.returncode
        != 0
        or
        not OUT.exists()
    ):

        raise SystemExit(
            1
        )


    print(
        "THREE WAY COMPARISON:",
        OUT
    )


if __name__ == "__main__":
    main()
