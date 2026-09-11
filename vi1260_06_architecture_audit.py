#!/usr/bin/env python3

import ast
import json

from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

OUT = (
    BASE
    / "logs/producao/"
    "vi1260_06_architecture_audit_latest.json"
)


FILES = [
    BASE / "vi1260_01_semantic_roles.py",
    BASE / "vi1260_02_targeted_search.py",
    BASE / "vi1260_03_semantic_candidate_gate.py",
    BASE / "vi1260_04_global_optimizer.py",
    BASE / "vi1260_00_coverage_resolver.py",
    BASE / "vi1260_05_regression.py",
]


def inspect(
    path,
):
    tree = ast.parse(
        path.read_text(
            encoding="utf-8"
        )
    )

    network = []
    dangerous = []


    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import
        ):
            names = [
                item.name
                for item in node.names
            ]

        elif isinstance(
            node,
            ast.ImportFrom
        ):
            names = (
                [node.module]
                if node.module
                else []
            )

        else:
            names = []


        for name in names:

            if (
                name.startswith("urllib")
                or
                name
                in {
                    "requests",
                    "socket",
                    "httpx",
                    "aiohttp",
                }
            ):
                network.append(name)


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
                    "socket",
                    "httpx",
                    "aiohttp",
                }:
                    dangerous.append(
                        root
                        + "."
                        + func.attr
                    )


    return {
        "file":
            path.name,

        "direct_network":
            network,

        "dangerous":
            dangerous,
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


        item = inspect(path)

        reports.append(item)


        if item[
            "direct_network"
        ]:

            blockers.append(
                "direct_network:"
                + path.name
            )


        if item[
            "dangerous"
        ]:

            blockers.append(
                "dangerous:"
                + path.name
            )


    policy = json.loads(
        (
            BASE
            / "config/"
            "vi1260_semantic_policy.json"
        ).read_text(
            encoding="utf-8"
        )
    )


    execution = policy[
        "execution"
    ]


    for key in [
        "remote_media_download",
        "ffmpeg",
        "renderer",
        "video_generation",
        "production_mutation",
        "publication",
    ]:

        if execution[key] is not False:

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
        "VI1260_ARCHITECTURE_CERTIFIED"
        if not blockers
        else "HOLD"
    )


    report = {
        "version":
            "1260.00",

        "status":
            status,

        "files":
            reports,

        "blockers":
            blockers,

        "network_boundary":
            "EXISTING_VI1200_TRANSPORT_ONLY",

        "downloads":
            False,

        "ffmpeg":
            False,

        "renderer":
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
        " VI1260 ARCHITECTURE AUDIT"
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
            item["file"],
            "| network=",
            item["direct_network"],
            "| dangerous=",
            item["dangerous"]
        )

    print(
        "BLOCKERS:",
        blockers
    )


    if blockers:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
