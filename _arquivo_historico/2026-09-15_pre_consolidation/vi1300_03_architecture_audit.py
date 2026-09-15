#!/usr/bin/env python3

import ast
import json

from pathlib import Path


BASE = (
    Path.home()
    / "ShortAutoPro"
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1300_03_architecture_audit_latest.json"
)


FILES = [
    BASE
    / "vi1300_01_presentation_safety.py",

    BASE
    / "vi1300_00_visual_preparation_director.py",

    BASE
    / "vi1300_02_regression.py",
]


NETWORK_NAMES = {
    "urllib",
    "requests",
    "httpx",
    "aiohttp",
    "socket",
}


def inspect_file(
    path,
):
    text = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        text
    )


    network = []

    process = []


    for node in ast.walk(
        tree
    ):

        if isinstance(
            node,
            ast.Import
        ):

            names = [
                item.name
                for item
                in node.names
            ]


        elif isinstance(
            node,
            ast.ImportFrom
        ):

            names = [
                node.module
            ] if node.module else []


        else:

            names = []


        for name in names:

            root = str(
                name
            ).split(
                "."
            )[0]


            if root in NETWORK_NAMES:

                network.append(
                    name
                )


            if root == "subprocess":

                process.append(
                    name
                )


    return {
        "file":
            path.name,

        "network":
            sorted(
                set(
                    network
                )
            ),

        "process":
            sorted(
                set(
                    process
                )
            ),

        "hardcoded_sid":
            (
                "2026-09-01_1433"
                in text
            ),
    }


def main():
    reports = []

    blockers = []


    for path in FILES:

        if not path.exists():

            blockers.append(
                "missing:"
                + path.name
            )

            continue


        item = inspect_file(
            path
        )


        reports.append(
            item
        )


        if item[
            "network"
        ]:

            blockers.append(
                "network:"
                + path.name
            )


        if item[
            "process"
        ]:

            blockers.append(
                "process:"
                + path.name
            )


        if item[
            "hardcoded_sid"
        ]:

            blockers.append(
                "hardcoded_sid:"
                + path.name
            )


    policy = json.loads(
        (
            BASE
            / "config/"
            "vi1300_visual_policy.json"
        ).read_text(
            encoding="utf-8"
        )
    )


    execution = (
        policy[
            "execution"
        ]
    )


    for key in [
        "network",
        "downloads",
        "ffmpeg",
        "ffprobe",
        "renderer",
        "video_generation",
        "production_mutation",
    ]:

        if execution[
            key
        ] is not False:

            blockers.append(
                key
                + "_not_locked"
            )


    if (
        policy[
            "source_recovery"
        ][
            "mode"
        ]
        != "SHADOW_ONLY"
    ):

        blockers.append(
            "source_recovery_not_shadow_only"
        )


    status = (
        "VI1300_ARCHITECTURE_CERTIFIED"

        if not blockers

        else "HOLD"
    )


    report = {
        "version":
            "1300.00",

        "status":
            status,

        "reports":
            reports,

        "blockers":
            blockers,

        "network":
            False,

        "downloads":
            False,

        "ffmpeg":
            False,

        "ffprobe":
            False,

        "renderer":
            False,

        "video":
            False,

        "production_mutation":
            False,
    }


    OUT.write_text(
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
        " VI1300 ARCHITECTURE AUDIT"
    )

    print(
        "=============================================="
    )


    print(
        "STATUS:",
        status
    )


    for item in reports:

        print(
            item[
                "file"
            ],
            "| network=",
            item[
                "network"
            ],
            "| process=",
            item[
                "process"
            ],
            "| hardcoded=",
            item[
                "hardcoded_sid"
            ]
        )


    print(
        "BLOCKERS:",
        blockers
    )


    if blockers:

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
