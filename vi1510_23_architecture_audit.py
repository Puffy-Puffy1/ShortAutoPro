#!/usr/bin/env python3

import ast

from vi1510_01_common import (
    BASE,
    ROOT,
    policy,
    save_json,
)


NETWORK_MODULES = {
    "urllib",
    "requests",
    "httpx",
    "aiohttp",
    "socket",
}


def run():
    blockers = []

    rows = []


    for path in sorted(
        ROOT.glob(
            "vi1510_*.py"
        )
    ):

        tree = ast.parse(
            path.read_text(
                encoding="utf-8"
            )
        )


        network = []

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

                names = (
                    [
                        node.module
                    ]

                    if node.module

                    else []
                )


            for name in names:

                root = str(
                    name
                ).split(
                    "."
                )[0]


                if root in NETWORK_MODULES:
                    network.append(
                        name
                    )


            if (
                isinstance(
                    node,
                    ast.Call
                )

                and

                isinstance(
                    node.func,
                    ast.Attribute
                )

                and

                isinstance(
                    node.func.value,
                    ast.Name
                )

                and

                node.func.value.id
                ==
                "os"

                and

                node.func.attr
                in {
                    "system",
                    "popen",
                }
            ):

                dangerous.append(
                    "os."
                    +
                    node.func.attr
                )


        if network:

            blockers.append(
                path.name
                +
                ":direct_network_forbidden"
            )


        if dangerous:

            blockers.append(
                path.name
                +
                ":dangerous_shell"
            )


        rows.append({
            "file":
                path.name,

            "network":
                network,

            "dangerous":
                dangerous,
        })


    config = policy()


    if (
        config.get(
            "production_mutation"
        )
        is not False
    ):

        blockers.append(
            "production_mutation_not_locked"
        )


    if (
        config.get(
            "publication"
        )
        is not False
    ):

        blockers.append(
            "publication_not_locked"
        )


    if (
        config.get(
            "network_direct"
        )
        is not False
    ):

        blockers.append(
            "network_direct_not_locked"
        )


    if (
        config.get(
            "source_recovery"
        )
        != "SHADOW_ONLY"
    ):

        blockers.append(
            "source_recovery_not_shadow_only"
        )


    report = {
        "status":
            (
                "VI1510_ARCHITECTURE_CERTIFIED"

                if not blockers

                else "VI1510_ARCHITECTURE_HOLD"
            ),

        "files":
            rows,

        "blockers":
            blockers,
    }


    save_json(
        BASE
        / "architecture.json",
        report
    )


    return report


if __name__ == "__main__":

    report = run()

    print(
        "STATUS:",
        report[
            "status"
        ]
    )

    print(
        "FILES:",
        len(
            report[
                "files"
            ]
        )
    )

    print(
        "BLOCKERS:",
        report[
            "blockers"
        ]
    )


    if report[
        "blockers"
    ]:

        raise SystemExit(
            1
        )
