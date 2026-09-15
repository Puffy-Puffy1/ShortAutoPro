#!/usr/bin/env python3

import ast
import json
from pathlib import Path

VERSION = "9.00.3B"

BASE = Path.home() / "ShortAutoPro"

CLIENT = (
    BASE
    / "wiki_client.py"
)

SOURCE = (
    BASE
    / "roteiro.py"
)

REPORT = (
    BASE
    / "logs/producao/"
      "vi9_003b_wiki_client_audit.json"
)

BLOCKED_IMPORTS = {
    "google",
    "google.generativeai",
    "google.genai",
    "anthropic",
    "openai",
    "subprocess",
}

BLOCKED_CALLS = {
    "system",
    "popen",
    "unlink",
    "remove",
    "rmtree",
    "rename",
    "replace",
}

NETWORK_HINTS = {
    "requests",
    "urllib",
    "httpx",
    "aiohttp",
}


def call_name(node):

    if isinstance(
        node,
        ast.Name
    ):
        return node.id

    if isinstance(
        node,
        ast.Attribute
    ):
        return node.attr

    return None


def import_root(name):
    return str(
        name or ""
    ).split(".")[0]


def audit():

    if not CLIENT.exists():
        return {
            "version": VERSION,
            "status": "HOLD",
            "blockers": [
                "wiki_client.py_missing"
            ],
        }

    text = CLIENT.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    tree = ast.parse(
        text
    )

    imports = []

    functions = []

    top_level_calls = []

    dangerous_calls = []

    blocked_imports = []

    network_imports = []


    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            functions.append({
                "name":
                    node.name,

                "line":
                    node.lineno,

                "args":
                    [
                        arg.arg
                        for arg
                        in node.args.args
                    ],
            })


        elif isinstance(
            node,
            ast.Import
        ):

            for alias in node.names:

                module = (
                    alias.name
                )

                imports.append(
                    module
                )

                root = import_root(
                    module
                )

                if (
                    module in BLOCKED_IMPORTS
                    or root in BLOCKED_IMPORTS
                ):
                    blocked_imports.append(
                        module
                    )

                if root in NETWORK_HINTS:
                    network_imports.append(
                        module
                    )


        elif isinstance(
            node,
            ast.ImportFrom
        ):

            module = (
                node.module
                or ""
            )

            imports.append(
                module
            )

            root = import_root(
                module
            )

            if (
                module in BLOCKED_IMPORTS
                or root in BLOCKED_IMPORTS
            ):
                blocked_imports.append(
                    module
                )

            if root in NETWORK_HINTS:
                network_imports.append(
                    module
                )


        else:

            for child in ast.walk(
                node
            ):

                if not isinstance(
                    child,
                    ast.Call
                ):
                    continue

                name = call_name(
                    child.func
                )

                if not name:
                    continue

                top_level_calls.append({
                    "name":
                        name,

                    "line":
                        getattr(
                            child,
                            "lineno",
                            None
                        ),
                })

                if (
                    name.lower()
                    in BLOCKED_CALLS
                ):
                    dangerous_calls.append({
                        "name":
                            name,

                        "line":
                            getattr(
                                child,
                                "lineno",
                                None
                            ),
                    })


    function_names = [
        item["name"]
        for item in functions
    ]


    blockers = []

    warnings = []


    if (
        "wiki_search_client"
        not in function_names
    ):
        blockers.append(
            "wiki_search_client_missing"
        )


    if blocked_imports:
        blockers.append(
            "blocked_imports_detected"
        )


    if dangerous_calls:
        blockers.append(
            "dangerous_top_level_calls"
        )


    # Top-level calls are not automatically fatal,
    # but we will refuse to import until reviewed.
    harmless_top_level = {
        "load_dotenv",
    }


    suspicious_top_level = [
        item
        for item
        in top_level_calls
        if (
            str(
                item.get("name")
            ).lower()
            not in harmless_top_level
        )
    ]


    if suspicious_top_level:
        warnings.append(
            "top_level_calls_require_review"
        )


    if blockers:

        status = "HOLD"

    elif warnings:

        status = (
            "STATIC_REVIEW_REQUIRED"
        )

    else:

        status = (
            "WIKI_CLIENT_STATIC_SAFE"
        )


    result = {
        "version":
            VERSION,

        "status":
            status,

        "functions":
            functions,

        "imports":
            sorted(
                set(imports)
            ),

        "network_imports":
            sorted(
                set(
                    network_imports
                )
            ),

        "blocked_imports":
            sorted(
                set(
                    blocked_imports
                )
            ),

        "top_level_calls":
            top_level_calls,

        "dangerous_calls":
            dangerous_calls,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "wiki_client_imported":
            False,

        "network_executed":
            False,

        "download_executed":
            False,

        "media_mutated":
            False,
    }


    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    REPORT.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    return result


if __name__ == "__main__":

    r = audit()

    print(
        "VI9.00.3B WIKI CLIENT STATIC AUDIT=PASS"
    )

    print(
        "STATUS:",
        r.get("status")
    )

    print(
        "FUNCTIONS:",
        [
            x.get("name")
            for x
            in r.get(
                "functions",
                []
            )
        ]
    )

    print(
        "IMPORTS:",
        r.get("imports")
    )

    print(
        "NETWORK IMPORTS:",
        r.get(
            "network_imports"
        )
    )

    print(
        "TOP LEVEL CALLS:",
        r.get(
            "top_level_calls"
        )
    )

    print(
        "BLOCKED IMPORTS:",
        r.get(
            "blocked_imports"
        )
    )

    print(
        "DANGEROUS CALLS:",
        r.get(
            "dangerous_calls"
        )
    )

    print(
        "BLOCKERS:",
        r.get(
            "blockers"
        )
    )

    print(
        "WARNINGS:",
        r.get(
            "warnings"
        )
    )

    print(
        "WIKI CLIENT IMPORTED:",
        r.get(
            "wiki_client_imported"
        )
    )

    print(
        "NETWORK EXECUTED:",
        r.get(
            "network_executed"
        )
    )
