#!/usr/bin/env python3

import ast
import json

from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

OUT = (
    BASE
    / "logs/producao/"
    "vi1400_08_architecture_audit_latest.json"
)


FILES = {
    "vi1400_01_transform_core.py":
        {
            "process":
                True
        },

    "vi1400_02_asset_transformer.py":
        {
            "process":
                False
        },

    "vi1400_03_prepared_forensics.py":
        {
            "process":
                False
        },

    "vi1400_04_render_manifest.py":
        {
            "process":
                False
        },

    "vi1400_05_visual_canary.py":
        {
            "process":
                True
        },

    "vi1400_06_canary_forensics.py":
        {
            "process":
                True
        },

    "vi1400_07_regression.py":
        {
            "process":
                False
        },
}


NETWORK_ROOTS = {
    "urllib",
    "requests",
    "httpx",
    "aiohttp",
    "socket",
}


def inspect(
    path,
    allow_process,
):
    tree = ast.parse(
        path.read_text(
            encoding="utf-8"
        )
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

            if root in NETWORK_ROOTS:

                network.append(
                    name
                )

            if root == "subprocess":

                process.append(
                    name
                )

    blockers = []

    if network:

        blockers.append(
            "network_import"
        )

    if (
        process
        and
        not allow_process
    ):

        blockers.append(
            "unexpected_process_boundary"
        )

    return {
        "file":
            path.name,

        "allow_process":
            allow_process,

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

        "blockers":
            blockers,
    }


def main():
    reports = []

    blockers = []

    for filename, policy in (
        FILES.items()
    ):

        path = (
            BASE
            /
            filename
        )

        if not path.exists():

            blockers.append(
                "missing:"
                + filename
            )

            continue

        item = inspect(
            path,
            policy[
                "process"
            ]
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
                filename
                + ":"
                + blocker
            )

    policy = json.loads(
        (
            BASE
            / "config/"
            "vi1400_release_candidate_policy.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    execution = (
        policy[
            "execution"
        ]
    )

    if execution[
        "network"
    ] is not False:

        blockers.append(
            "network_not_locked"
        )

    if execution[
        "downloads"
    ] is not False:

        blockers.append(
            "downloads_not_locked"
        )

    if execution[
        "renderer_production"
    ] is not False:

        blockers.append(
            "production_renderer_not_locked"
        )

    if execution[
        "production_mutation"
    ] is not False:

        blockers.append(
            "production_mutation_not_locked"
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
        "VI1400_ARCHITECTURE_CERTIFIED"
        if not blockers
        else
        "HOLD"
    )

    report = {
        "version":
            "1400.00",

        "status":
            status,

        "files":
            reports,

        "blockers":
            blockers,

        "network":
            False,

        "downloads":
            False,

        "production_renderer":
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
        " VI1400 ARCHITECTURE AUDIT"
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
            "| allowed=",
            item[
                "allow_process"
            ]
        )

    print(
        "BLOCKERS:",
        blockers
    )

    if blockers:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
