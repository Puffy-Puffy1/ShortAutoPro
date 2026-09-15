#!/usr/bin/env python3

import json
from pathlib import Path

VERSION = "8.96"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

REPORT = (
    BASE
    / "logs/producao/"
      "vi8_70_search_shadow_foundation_latest.json"
)


def select():

    if not REPORT.exists():

        return {
            "version": VERSION,
            "status": "HOLD",
            "reason":
                "vi870_report_missing",
        }


    data = json.loads(
        REPORT.read_text(
            encoding="utf-8"
        )
    )

    gate = (
        data.get("gate")
        or {}
    )

    compiled = (
        gate.get("compiled")
        or {}
    )

    plans = (
        compiled.get("plans")
        or []
    )


    if not plans:

        return {
            "version": VERSION,
            "status":
                "NO_SEARCH_REQUIRED",
            "reason": None,
        }


    first = plans[0]

    queries = (
        first.get("queries")
        or []
    )

    if not queries:

        return {
            "version": VERSION,
            "status": "HOLD",
            "reason":
                "query_missing",
        }


    return {
        "version": VERSION,

        "status":
            "QUERY_SELECTED",

        "scene":
            first.get(
                "scene"
            ),

        "category":
            first.get(
                "category"
            ),

        "query":
            queries[0],

        "priority":
            first.get(
                "priority"
            ),
    }


def self_test():

    assert VERSION == "8.96"

    print(
        "VI8.96 PROBE QUERY SELECTOR=PASS"
    )


if __name__ == "__main__":
    self_test()
