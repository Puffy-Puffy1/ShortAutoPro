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
    "vi1260_1_04_architecture_audit_latest.json"
)


FILES = [
    (
        BASE
        / "vi1260_1_01_strict_semantic_audit.py",
        False
    ),

    (
        BASE
        / "vi1260_1_02_repair_search.py",
        False
    ),

    (
        BASE
        / "vi1260_1_00_predownload_audit.py",
        False
    ),

    (
        BASE
        / "vi1260_1_03_regression.py",
        False
    ),

    (
        BASE
        / "vi1270_01_controlled_downloader.py",
        True
    ),
]


def inspect(
    path,
    network_allowed,
):
    text = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        text
    )


    network_imports = []

    dangerous = []


    for node in ast.walk(
        tree
    ):

        names = []


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

            if node.module:

                names = [
                    node.module
                ]


        for name in names:

            if (
                name.startswith(
                    "urllib"
                )
                or
                name
                in {
                    "requests",
                    "httpx",
                    "aiohttp",
                    "socket",
                }
            ):
                network_imports.append(
                    name
                )


        if isinstance(
            node,
            ast.Call
        ):

            func = node.func


            if (
                isinstance(
                    func,
                    ast.Attribute
                )
                and
                isinstance(
                    func.value,
                    ast.Name
                )
            ):

                root = (
                    func.value.id
                )


                if root in {
                    "subprocess",
                    "requests",
                    "httpx",
                    "aiohttp",
                    "socket",
                }:

                    dangerous.append(
                        root
                        + "."
                        + func.attr
                    )


                if (
                    root == "os"
                    and
                    func.attr
                    in {
                        "system",
                        "popen",
                    }
                ):

                    dangerous.append(
                        "os."
                        + func.attr
                    )


    blockers = []


    if (
        network_imports
        and
        not network_allowed
    ):
        blockers.append(
            "network_boundary_violation"
        )


    if dangerous:
        blockers.append(
            "dangerous_execution"
        )


    if (
        "2026-09-01_1433"
        in text
    ):
        blockers.append(
            "hardcoded_benchmark_short"
        )


    return {
        "file":
            path.name,

        "network_allowed":
            network_allowed,

        "network_imports":
            network_imports,

        "dangerous":
            dangerous,

        "blockers":
            blockers,
    }


def main():
    reports = []

    blockers = []


    for path, network_allowed in FILES:

        if not path.exists():

            blockers.append(
                "missing:"
                + path.name
            )

            continue


        item = inspect(
            path,
            network_allowed
        )


        reports.append(
            item
        )


        for blocker in (
            item[
                "blockers"
            ]
        ):

            blockers.append(
                path.name
                + ":"
                + blocker
            )


    policy = json.loads(
        (
            BASE
            / "config/"
            "vi1260_1_predownload_policy.json"
        ).read_text(
            encoding="utf-8"
        )
    )


    execution = policy[
        "execution"
    ]


    for key in [
        "ffmpeg",
        "renderer",
        "video_generation",
        "production_mutation",
        "publication",
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
        "VI1260_1_VI1270_ARCHITECTURE_CERTIFIED"

        if not blockers

        else "HOLD"
    )


    report = {
        "version":
            "1260.1+1270",

        "status":
            status,

        "files":
            reports,

        "controlled_binary_network_boundary":
            (
                "vi1270_01_controlled_downloader.py"
            ),

        "ffmpeg":
            False,

        "renderer":
            False,

        "video":
            False,

        "production_mutation":
            False,

        "blockers":
            blockers,
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
        " VI1260.1 + VI1270 ARCHITECTURE AUDIT"
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
                "network_imports"
            ],
            "| allowed=",
            item[
                "network_allowed"
            ],
            "| dangerous=",
            item[
                "dangerous"
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
