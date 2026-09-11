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
    / "vi1100_01_architecture_audit_latest.json"
)


FILES = [
    BASE
    / "vi1100_00_general_pipeline_test.py",

    BASE
    / "vi1000_1_semantic_core.py",

    BASE
    / "vi1000_1_query_gate.py",

    BASE
    / "vi1000_runtime.py",

    BASE
    / "vi1000_command_hook.py",
]


FORBIDDEN_ROOTS = {
    "requests",
    "httpx",
    "aiohttp",
    "socket",
    "subprocess",
    "urllib.request",
}


def inspect_file(
    path
):
    text = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        text
    )


    imports = []

    calls = []


    for node in ast.walk(
        tree
    ):
        if isinstance(
            node,
            ast.Import
        ):
            for item in (
                node.names
            ):
                imports.append(
                    item.name
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
                        "requests",
                        "subprocess",
                        "socket",
                        "httpx",
                        "aiohttp",
                    }:
                        calls.append(
                            root
                            + "."
                            + func.attr
                        )


    forbidden_imports = []


    for item in imports:
        for forbidden in (
            FORBIDDEN_ROOTS
        ):
            if (
                item == forbidden
                or
                item.startswith(
                    forbidden
                    + "."
                )
            ):
                forbidden_imports.append(
                    item
                )


    core_write_literals = [
        'video.py").write',
        "video.py').write",
        'gerar_short.sh").write',
        "gerar_short.sh').write",
        'roteiro.py").write',
        "roteiro.py').write",
    ]


    return {
        "file":
            path.name,

        "syntax":
            True,

        "forbidden_imports":
            sorted(
                set(
                    forbidden_imports
                )
            ),

        "forbidden_calls":
            sorted(
                set(
                    calls
                )
            ),

        "hardcoded_elisa_short_id":
            (
                "2026-09-01_1433"
                in text
            ),

        "possible_core_write":
            any(
                value in text
                for value in (
                    core_write_literals
                )
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
            item = inspect_file(
                path
            )

        except Exception as exc:
            blockers.append(
                "syntax:"
                + path.name
                + ":"
                + type(exc).__name__
            )

            continue


        reports.append(
            item
        )


        if item[
            "forbidden_imports"
        ]:
            blockers.append(
                "network_or_process_import:"
                + path.name
            )


        if item[
            "forbidden_calls"
        ]:
            blockers.append(
                "network_or_process_call:"
                + path.name
            )


        if item[
            "hardcoded_elisa_short_id"
        ]:
            blockers.append(
                "hardcoded_old_short_id:"
                + path.name
            )


        if item[
            "possible_core_write"
        ]:
            blockers.append(
                "possible_core_write:"
                + path.name
            )


    report = {
        "version":
            "1100.00",

        "status":
            (
                "VI1100_ARCHITECTURE_CERTIFIED"
                if not blockers
                else "HOLD"
            ),

        "files":
            reports,

        "blockers":
            blockers,

        "network_capability":
            False,

        "process_execution_capability":
            False,

        "ffmpeg_execution":
            False,

        "video_generation":
            False,
    }


    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


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
        " VI1100 ARCHITECTURE AUDIT"
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
            "| imports=",
            item[
                "forbidden_imports"
            ],
            "| calls=",
            item[
                "forbidden_calls"
            ],
            "| hardcoded=",
            item[
                "hardcoded_elisa_short_id"
            ],
            "| core_write=",
            item[
                "possible_core_write"
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
