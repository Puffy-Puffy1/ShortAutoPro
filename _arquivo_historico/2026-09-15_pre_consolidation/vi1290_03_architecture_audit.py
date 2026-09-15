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
    "vi1290_03_architecture_audit_latest.json"
)


FILES = [
    "vi1290_01_asset_planner.py",
    "vi1290_02_regression.py",
]


NETWORK_NAMES = {
    "urllib",
    "requests",
    "httpx",
    "aiohttp",
    "socket",
}


PROCESS_NAMES = {
    "subprocess",
}


def inspect_file(
    filename
):
    path = (
        BASE
        / filename
    )


    if not path.exists():

        return {
            "file":
                filename,

            "blockers": [
                "missing_file"
            ],
        }


    text = path.read_text(
        encoding="utf-8"
    )


    tree = ast.parse(
        text
    )


    network = []

    process = []

    dangerous = []


    for node in ast.walk(
        tree
    ):

        if isinstance(
            node,
            ast.Import
        ):

            for alias in node.names:

                root = alias.name.split(
                    "."
                )[0]


                if root in NETWORK_NAMES:

                    network.append(
                        alias.name
                    )


                if root in PROCESS_NAMES:

                    process.append(
                        alias.name
                    )


        elif isinstance(
            node,
            ast.ImportFrom
        ):

            if node.module:

                root = node.module.split(
                    "."
                )[0]


                if root in NETWORK_NAMES:

                    network.append(
                        node.module
                    )


                if root in PROCESS_NAMES:

                    process.append(
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

                if (
                    func.value.id
                    ==
                    "os"
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


    if network:

        blockers.append(
            "network_dependency"
        )


    if process:

        blockers.append(
            "process_execution_dependency"
        )


    if dangerous:

        blockers.append(
            "dangerous_execution"
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

        "process":
            sorted(
                set(
                    process
                )
            ),

        "dangerous":
            sorted(
                set(
                    dangerous
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


    policy = json.loads(
        (
            BASE
            / "config/"
            "vi1290_render_readiness_policy.json"
        ).read_text(
            encoding="utf-8"
        )
    )


    execution = policy[
        "execution"
    ]


    for key in [
        "network",
        "downloads",
        "ffmpeg",
        "ffprobe",
        "renderer",
        "video_generation",
        "production_mutation",
    ]:

        if execution.get(
            key
        ) is not False:

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
        !=
        "SHADOW_ONLY"
    ):

        blockers.append(
            "source_recovery_not_shadow_only"
        )


    status = (
        "VI1290_ARCHITECTURE_CERTIFIED"

        if not blockers

        else
        "VI1290_ARCHITECTURE_HOLD"
    )


    report = {
        "version":
            "1290.00",

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
        " VI1290 ARCHITECTURE AUDIT"
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
            item.get(
                "network"
            ),
            "| process=",
            item.get(
                "process"
            ),
            "| dangerous=",
            item.get(
                "dangerous"
            )
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
