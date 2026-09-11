#!/usr/bin/env python3

import ast
import json
from pathlib import Path


BASE = (
    Path.home()
    / "ShortAutoPro"
)

FILES = [
    BASE /
    "vi1000_runtime.py",

    BASE /
    "vi1000_command_hook.py",

    BASE /
    "vi1000_00_launch_production_engine.py",

    BASE /
    "vi1000_01_regression_suite.py",
]

OUT = (
    BASE /
    "logs/producao/"
    "vi1000_02_architecture_audit_latest.json"
)


FORBIDDEN_RUNTIME_PATTERNS = [
    "subprocess.run([\"ffmpeg\"",
    "os.system(\"ffmpeg",
    "video.py",
    "gerar_short.sh",
]


def inspect_python(path):
    text = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        text
    )

    imports = []

    functions = []

    for node in ast.walk(
        tree
    ):
        if isinstance(
            node,
            ast.Import
        ):
            for item in node.names:
                imports.append(
                    item.name
                )

        elif isinstance(
            node,
            ast.ImportFrom
        ):
            imports.append(
                node.module
            )

        elif isinstance(
            node,
            ast.FunctionDef
        ):
            functions.append(
                node.name
            )


    network_imports = [
        item
        for item in imports
        if item in {
            "requests",
            "urllib.request",
            "httpx",
            "aiohttp",
        }
    ]


    return {
        "file":
            path.name,

        "syntax":
            "PASS",

        "imports":
            imports,

        "functions":
            functions,

        "network_imports":
            network_imports,

        "contains_hardcoded_1433":
            (
                "2026-09-01_1433"
                in text
            ),

        "contains_ffmpeg_literal":
            (
                "ffmpeg"
                in text.lower()
            ),
    }


def main():
    results = []

    blockers = []


    for path in FILES:
        if not path.exists():
            blockers.append(
                "missing:"
                + path.name
            )

            continue

        try:
            result = (
                inspect_python(
                    path
                )
            )

        except Exception as exc:
            blockers.append(
                "syntax:"
                + path.name
                + ":"
                + type(exc).__name__
            )

            continue

        results.append(
            result
        )


    for result in results:
        if result[
            "contains_hardcoded_1433"
        ]:
            blockers.append(
                "hardcoded_benchmark_short_id:"
                + result[
                    "file"
                ]
            )


        if result[
            "network_imports"
        ]:
            blockers.append(
                "unexpected_network_import:"
                + result[
                    "file"
                ]
            )


    status = (
        "VI1000_ARCHITECTURE_CERTIFIED"
        if not blockers
        else "HOLD"
    )


    report = {
        "version":
            "1000.00",

        "status":
            status,

        "files":
            results,

        "blockers":
            blockers,

        "dynamic_short_id":
            not any(
                "hardcoded_benchmark_short_id"
                in item
                for item in blockers
            ),

        "network_executed":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
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
        " VI1000 ARCHITECTURE AUDIT"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        status
    )

    print(
        "DYNAMIC SHORT ID:",
        report[
            "dynamic_short_id"
        ]
    )

    print(
        "BLOCKERS:",
        blockers
    )

    print()

    for item in results:
        print(
            item[
                "file"
            ],
            "| hardcoded=",
            item[
                "contains_hardcoded_1433"
            ],
            "| network=",
            item[
                "network_imports"
            ],
        )


if __name__ == "__main__":
    main()
