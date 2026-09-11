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
    "vi1250_07_architecture_audit_latest.json"
)


FILES = [
    BASE / "vi1250_01_seed_bank.py",
    BASE / "vi1250_02_query_expander.py",
    BASE / "vi1250_03_cached_real_search.py",
    BASE / "vi1250_04_candidate_engine.py",
    BASE / "vi1250_05_portfolio_optimizer.py",
    BASE / "vi1250_00_deep_real_source_expansion.py",
    BASE / "vi1250_06_portfolio_adversarial.py",
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


    direct_network = [
        value
        for value in imports

        if (
            value.startswith(
                "urllib"
            )
            or
            value
            in {
                "requests",
                "httpx",
                "aiohttp",
                "socket",
            }
        )
    ]


    return {
        "file":
            path.name,

        "direct_network":
            direct_network,

        "dangerous_calls":
            dangerous,

        "hardcoded_old_short_id":
            (
                "2026-09-01_1433"
                in text
            ),
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


        if item[
            "direct_network"
        ]:

            blockers.append(
                "network_boundary_violation:"
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
            "hardcoded_old_short_id"
        ]:

            blockers.append(
                "hardcoded_short_id:"
                + path.name
            )


    policy = json.loads(
        (
            BASE
            / "config/"
            "vi1250_source_expansion_policy.json"
        ).read_text(
            encoding="utf-8"
        )
    )


    execution = policy[
        "execution"
    ]


    if execution[
        "remote_media_download"
    ] is not False:

        blockers.append(
            "download_not_locked"
        )


    if execution[
        "ffmpeg"
    ] is not False:

        blockers.append(
            "ffmpeg_not_locked"
        )


    if execution[
        "renderer"
    ] is not False:

        blockers.append(
            "renderer_not_locked"
        )


    if execution[
        "video_generation"
    ] is not False:

        blockers.append(
            "video_not_locked"
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
            "1250.00",

        "status":
            (
                "VI1250_ARCHITECTURE_CERTIFIED"
                if not blockers
                else "HOLD"
            ),

        "files":
            reports,

        "network_boundary":
            "VI1200_TRANSPORT_ONLY",

        "remote_media_download":
            False,

        "ffmpeg":
            False,

        "renderer":
            False,

        "video_generation":
            False,

        "source_recovery":
            "SHADOW_ONLY",

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
        " VI1250 ARCHITECTURE AUDIT"
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
            "| direct_network=",
            item[
                "direct_network"
            ],
            "| dangerous=",
            item[
                "dangerous_calls"
            ],
            "| hardcoded=",
            item[
                "hardcoded_old_short_id"
            ]
        )


    print(
        "NETWORK BOUNDARY:",
        report[
            "network_boundary"
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
