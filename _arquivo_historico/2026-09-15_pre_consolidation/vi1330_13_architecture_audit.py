#!/usr/bin/env python3

import ast
import json
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

POLICY = json.loads(
    (
        BASE
        / "config/vi1330_publication_quality_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)

FILES = [
    "vi1330_01_publication_visual_director.py",
    "vi1330_02_overlay_director.py",
    "vi1330_03_motion_engine.py",
    "vi1330_04_archive_video_director.py",
    "vi1330_05_subtitle_safety.py",
    "vi1330_06_scene_renderer.py",
    "vi1330_07_publication_render.py",
    "vi1330_08_technical_audit.py",
    "vi1330_09_visual_qa.py",
    "vi1330_10_contact_sheet.py",
    "vi1330_11_three_way_compare.py",
    "vi1330_12_regression.py",
]

OUT = (
    BASE
    / "logs/producao/"
    "vi1330_13_architecture_audit_latest.json"
)


NETWORK_MODULES = {
    "urllib",
    "requests",
    "httpx",
    "aiohttp",
    "socket",
}


def inspect_file(
    filename
):
    path = BASE / filename

    blockers = []

    network = []


    if not path.exists():

        return {
            "file":
                filename,

            "blockers": [
                "missing"
            ]
        }


    tree = ast.parse(
        path.read_text(
            encoding="utf-8"
        )
    )


    for node in ast.walk(
        tree
    ):

        names = []


        if isinstance(
            node,
            ast.Import
        ):

            names = [
                alias.name

                for alias in node.names
            ]


        elif isinstance(
            node,
            ast.ImportFrom
        ) and node.module:

            names = [
                node.module
            ]


        for name in names:

            if (
                name.split(
                    "."
                )[0]
                in NETWORK_MODULES
            ):

                network.append(
                    name
                )


    if network:

        blockers.append(
            "network_import"
        )


    return {
        "file":
            filename,

        "network":
            sorted(
                set(
                    network
                )
            ),

        "blockers":
            blockers,
    }


def main():
    reports = [
        inspect_file(
            filename
        )

        for filename in FILES
    ]


    blockers = []


    for item in reports:

        for blocker in (
            item.get(
                "blockers"
            )
            or []
        ):

            blockers.append(
                item[
                    "file"
                ]
                + ":"
                + blocker
            )


    if POLICY[
        "execution"
    ][
        "network"
    ] is not False:

        blockers.append(
            "network_not_locked"
        )


    if POLICY[
        "execution"
    ][
        "downloads"
    ] is not False:

        blockers.append(
            "downloads_not_locked"
        )


    if POLICY[
        "execution"
    ][
        "production_mutation"
    ] is not False:

        blockers.append(
            "production_not_locked"
        )


    if (
        POLICY[
            "source_recovery"
        ][
            "mode"
        ]
        !=
        "SHADOW_ONLY"
    ):

        blockers.append(
            "source_recovery_not_shadow"
        )


    status = (
        "VI1330_ARCHITECTURE_CERTIFIED"

        if not blockers

        else
        "VI1330_ARCHITECTURE_HOLD"
    )


    output = {
        "status":
            status,

        "files":
            reports,

        "blockers":
            blockers,
    }


    OUT.write_text(
        json.dumps(
            {
                "gate":
                    output
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
        " VI1330 ARCHITECTURE AUDIT"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        status
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
