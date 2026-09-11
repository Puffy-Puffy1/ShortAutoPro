#!/usr/bin/env python3

import ast

from vi1400_01_common import (
    ROOT,
    TMP,
    save_json,
)


def main():
    files = sorted(
        ROOT.glob(
            "vi1400_*.py"
        )
    )


    blockers = []

    report = []


    for path in files:

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

                if (
                    name

                    and

                    (
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
                    )
                ):

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
            ):

                if (
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


        report.append({
            "file":
                path.name,

            "network":
                network,

            "dangerous":
                dangerous,
        })


    status = (
        "VI1400_ARCHITECTURE_CERTIFIED"

        if not blockers

        else "HOLD"
    )


    save_json(
        TMP
        / "architecture.json",
        {
            "status":
                status,

            "files":
                report,

            "blockers":
                blockers,
        }
    )


    print(
        "STATUS:",
        status
    )

    print(
        "FILES:",
        len(
            files
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
