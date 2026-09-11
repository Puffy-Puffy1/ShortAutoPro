#!/usr/bin/env python3

import ast
import json
from pathlib import Path

VERSION = "9.00.3B"

BASE = Path.home() / "ShortAutoPro"

ROTEIRO = (
    BASE
    / "roteiro.py"
)

AUDIT_REPORT = (
    BASE
    / "logs/producao/"
      "vi9_003b_wiki_client_audit.json"
)

OUTPUT = (
    BASE
    / "vi9_wiki_search_adapter.py"
)


def extract_wiki_search():

    text = ROTEIRO.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    tree = ast.parse(
        text
    )

    for node in tree.body:

        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                )
            )
            and node.name
            == "wiki_search"
        ):

            return (
                ast.get_source_segment(
                    text,
                    node
                )
            )

    return None


def build():

    audit = json.loads(
        AUDIT_REPORT.read_text(
            encoding="utf-8"
        )
    )


    if audit.get(
        "status"
    ) != "WIKI_CLIENT_STATIC_SAFE":

        result = {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "wiki_client_not_static_safe",

            "adapter_created":
                False,
        }

        return result


    source = extract_wiki_search()


    if not source:

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "wiki_search_source_missing",

            "adapter_created":
                False,
        }


    content = '''#!/usr/bin/env python3
"""
VI9 isolated Wikipedia search adapter.

This module intentionally avoids importing roteiro.py.

It contains only:
- wiki_search_client dependency
- wiki_search wrapper

No Gemini initialization.
No media download API.
No renderer integration.
"""

from wiki_client import wiki_search_client

VI9_ADAPTER_VERSION = "9.00.3B"

VI9_DOWNLOAD_ALLOWED = False
VI9_MEDIA_WRITE_ALLOWED = False
VI9_RENDER_ALLOWED = False
VI9_SOURCE_RECOVERY_ALLOWED = False

'''


    content += (
        source
        + "\n\n"
    )


    content += '''
def adapter_status():
    return {
        "version":
            VI9_ADAPTER_VERSION,

        "status":
            "ISOLATED_ADAPTER_READY",

        "download_allowed":
            VI9_DOWNLOAD_ALLOWED,

        "media_write_allowed":
            VI9_MEDIA_WRITE_ALLOWED,

        "renderer_allowed":
            VI9_RENDER_ALLOWED,

        "source_recovery_allowed":
            VI9_SOURCE_RECOVERY_ALLOWED,
    }
'''


    OUTPUT.write_text(
        content,
        encoding="utf-8"
    )


    return {
        "version":
            VERSION,

        "status":
            "ISOLATED_ADAPTER_READY",

        "adapter":
            str(OUTPUT),

        "adapter_created":
            True,

        "roteiro_imported":
            False,

        "wiki_client_imported":
            False,

        "network_executed":
            False,

        "gemini_executed":
            False,

        "download_executed":
            False,

        "media_mutated":
            False,
    }


if __name__ == "__main__":

    r = build()

    print(
        "ADAPTER STATUS:",
        r.get(
            "status"
        )
    )

    print(
        "ADAPTER CREATED:",
        r.get(
            "adapter_created"
        )
    )

    print(
        "REASON:",
        r.get(
            "reason"
        )
    )

    print(
        "ROTEIRO IMPORTED:",
        r.get(
            "roteiro_imported"
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
