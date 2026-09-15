#!/usr/bin/env python3

import ast
import json
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

OUT = (
    BASE
    / "logs/producao/"
    "vi1450_05_architecture_audit_latest.json"
)


FILES = {
    "vi1450_01_prerequisite_gate.py":
        False,

    "vi1450_02_contact_sheet.py":
        True,

    "vi1450_03_credits_manifest.py":
        False,

    "vi1450_04_portfolio_audit.py":
        False,
}


NETWORK_ROOTS = {
    "urllib",
    "requests",
    "httpx",
    "aiohttp",
    "socket",
}


def inspect_file(
    filename,
    process_allowed,
):
    path = (
        BASE
        / filename
    )

    if not path.exists():
        return {
            "file":
                filename,

            "missing":
                True,

            "network":
                [],

            "process":
                [],

            "blockers": [
                "missing"
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

    for node in ast.walk(
        tree
    ):

        names = []

        if isinstance(
            node,
            ast.Import
        ):
            names = [
                entry.name
                for entry
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
        not process_allowed
    ):
        blockers.append(
            "unexpected_process"
        )

    if (
        "2026-09-01_1433"
        in text
    ):
        blockers.append(
            "hardcoded_sid"
        )

    return {
        "file":
            filename,

        "missing":
            False,

        "network":
            sorted(
                set(network)
            ),

        "process":
            sorted(
                set(process)
            ),

        "process_allowed":
            process_allowed,

        "blockers":
            blockers,
    }


def main():
    reports = []

    blockers = []

    for filename, allowed in (
        FILES.items()
    ):
        item = inspect_file(
            filename,
            allowed,
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

    status = (
        "VI1450_ARCHITECTURE_CERTIFIED"
        if not blockers
        else
        "HOLD"
    )

    report = {
        "version":
            "1450.00",

        "status":
            status,

        "files":
            reports,

        "network":
            False,

        "downloads":
            False,

        "production_renderer":
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
        " VI1450 ARCHITECTURE AUDIT"
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
            "| blockers=",
            item[
                "blockers"
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
