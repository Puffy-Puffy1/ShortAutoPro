#!/usr/bin/env python3

import ast

from vi1500_01_common import (
    BASE,
    ROOT,
    save_json,
)


FORBIDDEN_NETWORK = {
    "urllib",
    "requests",
    "httpx",
    "aiohttp",
    "socket",
}


def run():
    blockers = []

    files = []


    for path in sorted(
        ROOT.glob(
            "vi1500_*.py"
        )
    ):
        text = path.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            text
        )


        network = []

        dangerous = []


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
                names = (
                    [
                        node.module
                    ]
                    if node.module
                    else []
                )


            else:
                names = []


            for name in names:
                root = str(
                    name
                ).split(
                    "."
                )[0]


                if root in FORBIDDEN_NETWORK:
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
                ":direct_network_boundary"
            )


        if dangerous:
            blockers.append(
                path.name
                +
                ":dangerous_shell_call"
            )


        files.append({
            "file":
                path.name,

            "network":
                network,

            "dangerous":
                dangerous,
        })


    status = (
        "VI1500_ARCHITECTURE_CERTIFIED"

        if not blockers

        else "VI1500_ARCHITECTURE_HOLD"
    )


    report = {
        "status":
            status,

        "files":
            files,

        "blockers":
            blockers,

        "generator_network":
            "delegated_to_existing_pipeline",

        "publication":
            False,
    }


    save_json(
        BASE
        / "architecture_audit.json",
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
