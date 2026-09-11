#!/usr/bin/env python3

from pathlib import Path

from vi8_71_search_code_discovery import (
    discover
)

from vi8_72_network_call_auditor import (
    audit as network_audit
)

from vi8_73_search_function_classifier import (
    classify
)

from vi8_74_provider_detector import (
    detect
)

VERSION = "8.77"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    discovery = discover()

    modules = []

    for item in (
        discovery.get("files")
        or []
    ):
        path = Path(
            item["path"]
        )

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore"
            )
        except Exception:
            text = ""

        network = network_audit(
            path
        )

        functions = []

        for fn in (
            item.get(
                "functions"
            )
            or []
        ):
            functions.append({
                "name": fn,
                "role":
                    classify(fn),
            })

        modules.append({
            "path":
                item.get(
                    "relative"
                ),

            "keyword_hits":
                item.get(
                    "hits"
                ),

            "providers":
                detect(text),

            "functions":
                functions,

            "network_calls":
                network.get(
                    "calls"
                )
                or [],

            "network_call_count":
                network.get(
                    "count",
                    0
                ),
        })

    modules.sort(
        key=lambda x: (
            -x[
                "network_call_count"
            ],
            x["path"]
        )
    )

    return {
        "version": VERSION,
        "module_count":
            len(modules),
        "modules":
            modules,
    }


def self_test():
    assert VERSION == "8.77"

    print(
        "VI8.77 SEARCH ARCHITECTURE MAPPER=PASS"
    )


if __name__ == "__main__":
    self_test()
