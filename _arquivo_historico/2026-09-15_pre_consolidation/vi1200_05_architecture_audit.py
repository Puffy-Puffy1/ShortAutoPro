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
    / "logs/producao"
    / "vi1200_05_architecture_audit_latest.json"
)


FILES = [
    BASE
    / "vi1200_00_controlled_real_pipeline.py",

    BASE
    / "vi1200_01_real_transport.py",

    BASE
    / "vi1200_02_commons_provider.py",

    BASE
    / "vi1200_03_archive_provider.py",

    BASE
    / "vi1200_04_real_candidate_adapter.py",
]


def inspect_file(
    path
):
    tree = ast.parse(
        path.read_text(
            encoding="utf-8"
        )
    )


    imports = []

    dangerous_calls = []


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


            if isinstance(
                func,
                ast.Attribute
            ):
                if isinstance(
                    func.value,
                    ast.Name
                ):
                    root = (
                        func.value.id
                    )

                    if root in {
                        "subprocess",
                        "requests",
                        "httpx",
                        "aiohttp",
                    }:
                        dangerous_calls.append(
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
                        dangerous_calls.append(
                            root
                            + "."
                            + func.attr
                        )


    network_imports = [
        item
        for item in imports
        if (
            item.startswith(
                "urllib"
            )
            or
            item in {
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

        "network_imports":
            network_imports,

        "dangerous_calls":
            dangerous_calls,

        "network_allowed_here":
            (
                path.name
                ==
                "vi1200_01_real_transport.py"
            ),
    }


def main():
    reports = []

    blockers = []


    for path in FILES:
        if not path.exists():
            blockers.append(
                "missing:"
                + path.name
            )

            continue


        try:
            report = inspect_file(
                path
            )

        except Exception as exc:
            blockers.append(
                "parse_failure:"
                + path.name
                + ":"
                + type(exc).__name__
            )

            continue


        reports.append(
            report
        )


        if report[
            "dangerous_calls"
        ]:
            blockers.append(
                "dangerous_process_call:"
                + path.name
            )


        if (
            report[
                "network_imports"
            ]
            and
            not report[
                "network_allowed_here"
            ]
        ):
            blockers.append(
                "network_boundary_violation:"
                + path.name
            )


    transport = next(
        (
            item
            for item in reports
            if item[
                "file"
            ]
            ==
            "vi1200_01_real_transport.py"
        ),
        None
    )


    if (
        not transport
        or
        not transport[
            "network_imports"
        ]
    ):
        blockers.append(
            "controlled_transport_missing"
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
            "remote_media_download_not_locked"
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
            "ffmpeg_not_locked"
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
            "renderer_not_locked"
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
            "1200.00",

        "status":
            (
                "VI1200_ARCHITECTURE_CERTIFIED"
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
        " VI1200 ARCHITECTURE + NETWORK AUDIT"
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
                "network_allowed_here"
            ],
            "| dangerous=",
            item[
                "dangerous_calls"
            ]
        )


    print(
        "NETWORK BOUNDARY: TRANSPORT_ONLY"
    )

    print(
        "REMOTE MEDIA DOWNLOAD: False"
    )

    print(
        "FFMPEG: False"
    )

    print(
        "RENDERER: False"
    )

    print(
        "SOURCE RECOVERY: SHADOW_ONLY"
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
