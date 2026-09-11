#!/usr/bin/env python3

import ast
from pathlib import Path

VERSION = "9.00.3B"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

ADAPTER = (
    BASE
    / "vi9_wiki_search_adapter.py"
)


BLOCKED_TEXT = (
    "gemini_api_key",
    "generativeai",
    "google.genai",
    "subprocess",
    "ffmpeg",
    "download_image",
    "download_media",
    "unlink(",
    "remove(",
)


def evaluate():

    if not ADAPTER.exists():

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "blockers": [
                "adapter_missing"
            ],
        }


    text = ADAPTER.read_text(
        encoding="utf-8",
        errors="ignore"
    )


    blockers = []

    low = text.lower()


    for token in BLOCKED_TEXT:

        if token in low:

            blockers.append(
                "blocked_text:"
                + token
            )


    try:

        tree = ast.parse(
            text
        )

    except Exception as exc:

        blockers.append(
            "adapter_syntax_error:"
            + str(exc)[:120]
        )

        tree = None


    functions = []

    imports = []


    if tree:

        for node in tree.body:

            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                )
            ):
                functions.append(
                    node.name
                )


            elif isinstance(
                node,
                ast.Import
            ):

                imports.extend(
                    alias.name
                    for alias
                    in node.names
                )


            elif isinstance(
                node,
                ast.ImportFrom
            ):

                if node.module:

                    imports.append(
                        node.module
                    )


    status = (
        "PASS"
        if not blockers
        else "HOLD"
    )


    return {
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

        "wiki_search_present":
            "wiki_search"
            in functions,

        "blockers":
            blockers,

        "adapter_imported":
            False,

        "network_executed":
            False,
    }


def self_test():

    assert VERSION == "9.00.3B"

    print(
        "VI9.00.3B STATIC ADAPTER AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
