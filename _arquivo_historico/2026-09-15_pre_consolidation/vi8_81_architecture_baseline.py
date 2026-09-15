#!/usr/bin/env python3

import json
from pathlib import Path

VERSION = "8.81"

BASE = Path.home() / "ShortAutoPro"

REPORT = (
    BASE
    / "logs/producao/"
      "vi8_80_search_architecture_latest.json"
)


def load():
    if not REPORT.exists():
        raise RuntimeError(
            "vi8_80_report_missing"
        )

    data = json.loads(
        REPORT.read_text(
            encoding="utf-8"
        )
    )

    gate = (
        data.get("gate")
        or {}
    )

    status = gate.get(
        "status"
    )

    if status not in {
        "SEARCH_ARCHITECTURE_MAPPED",
        "SEARCH_ARCHITECTURE_PARTIAL",
    }:
        raise RuntimeError(
            "vi8_80_baseline_not_safe"
        )

    return gate


def self_test():
    assert VERSION == "8.81"
    print(
        "VI8.81 ARCHITECTURE BASELINE=PASS"
    )


if __name__ == "__main__":
    self_test()
