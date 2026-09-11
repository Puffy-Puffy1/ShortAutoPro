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
    "vi1200_11_architecture_audit_latest.json"
)


FILES = [
    BASE
    / "vi1200_01_real_transport.py",

    BASE
    / "vi1200_02_commons_provider.py",

    BASE
    / "vi1200_03_archive_provider.py",

    BASE
    / "vi1200_04_real_candidate_adapter.py",

    BASE
    / "vi1200_06_visual_precision.py",

    BASE
    / "vi1200_07_search_expansion.py",

    BASE
    / "vi1200_10_hardened_real_pipeline.py",
]


def inspect(
    path
):
    text = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        text
    )


    imports = []

    dangerous = []


    for node in ast.walk(
        tree
    ):

        if isinstance(
            node,
            ast.Import
        ):

            imports.extend(
                item.name
                for item in node.names
            )


        elif isinstance(
            node,
            ast.ImportFrom
        ):

            if node.module:
                imports.append(
                    node.module
                )


        elif isinstance(
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
                        root
                        + "."
                        + func.attr
                    )


    network = [
        item
        for item in imports

        if (
            item.startswith(
                "urllib"
            )
            or
            item
            in {
                "requests",
                "httpx",
                "aiohttp",
                "socket",
            }
        )
    ]


    allowed = (
        path.name
        ==
        "vi1200_01_real_transport.py"
    )


    return {
        "file":
            path.name,

        "network_imports":
            network,

        "network_allowed":
            allowed,

        "dangerous_calls":
            dangerous,

        "hardcoded_benchmark_short_id":
            (
                "2026-09-01_1433"
                in text
            ),

        "core_write":
            False,
    }


def main():
    blockers = []

    reports = []


    for path in FILES:

        if not path.exists():

            blockers.append(
                "missing:"
                + path.name
            )

            continue


        try:

            item = inspect(
                path
            )

        except Exception as exc:

            blockers.append(
                "parse:"
                + path.name
                + ":"
                + type(exc).__name__
            )

            continue


        reports.append(
            item
        )


        if (
            item[
                "network_imports"
            ]
            and
            not item[
                "network_allowed"
            ]
        ):

            blockers.append(
                "network_boundary:"
                + path.name
            )


        if item[
            "dangerous_calls"
        ]:

            blockers.append(
                "dangerous_execution:"
                + path.name
            )


        if item[
            "hardcoded_benchmark_short_id"
        ]:

            blockers.append(
                "hardcoded_short_id:"
                + path.name
            )


    policy = json.loads(
        (
            BASE
            / "config/"
            "vi1200_real_policy.json"
        ).read_text(
            encoding="utf-8"
        )
    )


    if (
        policy[
            "media"
        ][
            "remote_media_download"
        ]
        is not False
    ):

        blockers.append(
            "download_lock_disabled"
        )


    if (
        policy[
            "execution"
        ][
            "ffmpeg"
        ]
        is not False
    ):

        blockers.append(
            "ffmpeg_lock_disabled"
        )


    if (
        policy[
            "execution"
        ][
            "renderer"
        ]
        is not False
    ):

        blockers.append(
            "renderer_lock_disabled"
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


    report = {
        "version":
            "1200.1",

        "status":
            (
                "VI1200_1_ARCHITECTURE_CERTIFIED"
                if not blockers
                else "HOLD"
            ),

        "files":
            reports,

        "blockers":
            blockers,

        "network_boundary":
            "TRANSPORT_ONLY",

        "remote_media_download":
            False,

        "ffmpeg":
            False,

        "renderer":
            False,

        "source_recovery":
            "SHADOW_ONLY",
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
        " VI1200.1 ARCHITECTURE AUDIT"
    )

    print(
        "=============================================="
    )


    print(
        "STATUS:",
        report[
            "status"
        ]
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
                "dangerous_calls"
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
