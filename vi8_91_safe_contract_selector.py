#!/usr/bin/env python3

import json
from pathlib import Path

VERSION = "8.91"

BASE = Path.home() / "ShortAutoPro"

REPORT = (
    BASE
    / "logs/producao/"
      "vi8_90_safe_search_adapter_latest.json"
)


def select():

    data = json.loads(
        REPORT.read_text(
            encoding="utf-8"
        )
    )

    gate = (
        data.get("gate")
        or {}
    )

    if gate.get("status") not in {
        "SAFE_ADAPTER_BLUEPRINT_READY",
        "READY_WITH_STATIC_REVIEW",
    }:
        return {
            "version": VERSION,
            "status": "HOLD",
            "reason":
                "vi890_not_ready",
            "contract": None,
        }

    contracts = (
        gate.get("contracts")
        or []
    )

    safe = [
        item
        for item in contracts
        if item.get("status")
        == "READ_ONLY_SIGNATURE_ACCEPTABLE"
    ]

    if not safe:
        return {
            "version": VERSION,
            "status": "HOLD",
            "reason":
                "no_safe_contract",
            "contract": None,
        }

    return {
        "version": VERSION,
        "status":
            "SAFE_CONTRACT_SELECTED",
        "reason": None,
        "contract":
            safe[0],
        "providers":
            gate.get("providers")
            or [],
    }


def self_test():
    assert VERSION == "8.91"

    print(
        "VI8.91 SAFE CONTRACT SELECTOR=PASS"
    )


if __name__ == "__main__":
    self_test()
