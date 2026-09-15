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
    / "vi1000_1_architecture_audit_latest.json"
)


FILES = [
    BASE
    / "vi1000_1_semantic_core.py",

    BASE
    / "vi1000_1_query_gate.py",

    BASE
    / "vi1000_1_adversarial_suite.py",

    BASE
    / "vi1000_1_full_dry_run.py",

    BASE
    / "vi1000_runtime.py",

    BASE
    / "vi1000_command_hook.py",
]


FORBIDDEN_IMPORTS = {
    "requests",
    "socket",
    "httpx",
    "aiohttp",
    "subprocess",
    "urllib.request"
}


def inspect(
    path
):
    text = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        text
    )

    imports = []

    forbidden_calls = []


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
            target = node.func

            if isinstance(
                target,
                ast.Attribute
            ):
                if isinstance(
                    target.value,
                    ast.Name
                ):
                    root = (
                        target.value.id
                    )

                    if root in {
                        "subprocess",
                        "requests",
                        "socket"
                    }:
                        forbidden_calls.append(
                            root
                            + "."
                            + target.attr
                        )


    forbidden_imports = [
        item
        for item in imports
        if item in (
            FORBIDDEN_IMPORTS
        )
        or
        any(
            item.startswith(
                prefix
                + "."
            )
            for prefix in (
                FORBIDDEN_IMPORTS
            )
        )
    ]


    return {
        "file":
            path.name,

        "syntax":
            "PASS",

        "forbidden_imports":
            forbidden_imports,

        "forbidden_calls":
            forbidden_calls,

        "hardcoded_old_short_id":
            (
                "2026-09-01_1433"
                in text
            ),

        "writes_core_filename_literal":
            any(
                token in text
                for token in [
                    'open("video.py", "w"',
                    'open("gerar_short.sh", "w"',
                    'open("roteiro.py", "w"',
                    'write_text("video.py"',
                ]
            ),
    }


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
        item = inspect(
            path
        )

        results.append(
            item
        )

    except Exception as exc:
        blockers.append(
            "syntax:"
            + path.name
            + ":"
            + type(exc).__name__
        )


for item in results:
    if item[
        "forbidden_imports"
    ]:
        blockers.append(
            "forbidden_import:"
            + item[
                "file"
            ]
        )

    if item[
        "forbidden_calls"
    ]:
        blockers.append(
            "forbidden_call:"
            + item[
                "file"
            ]
        )

    if item[
        "hardcoded_old_short_id"
    ]:
        blockers.append(
            "hardcoded_old_short_id:"
            + item[
                "file"
            ]
        )

    if item[
        "writes_core_filename_literal"
    ]:
        blockers.append(
            "possible_core_write:"
            + item[
                "file"
            ]
        )


report = {
    "version":
        "1000.1",

    "status":
        (
            "VI1000_1_ARCHITECTURE_CERTIFIED"
            if not blockers
            else "HOLD"
        ),

    "files":
        results,

    "blockers":
        blockers,

    "network_capability_present":
        False
        if not any(
            item[
                "forbidden_imports"
            ]
            for item in results
        )
        else True,

    "ffmpeg_execution_capability_present":
        False
        if not any(
            "subprocess"
            in item[
                "forbidden_imports"
            ]
            for item in results
        )
        else True,

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
    " VI1000.1 ARCHITECTURE AUDIT"
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

for item in results:
    print(
        item[
            "file"
        ],
        "| forbidden imports=",
        item[
            "forbidden_imports"
        ],
        "| calls=",
        item[
            "forbidden_calls"
        ],
        "| hardcoded=",
        item[
            "hardcoded_old_short_id"
        ]
    )

print(
    "BLOCKERS:",
    blockers
)
