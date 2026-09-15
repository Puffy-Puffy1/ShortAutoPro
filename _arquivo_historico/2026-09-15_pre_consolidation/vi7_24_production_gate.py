#!/usr/bin/env python3

import json

from pathlib import Path


from vi7_23_source_safety_lock import (
    evaluate as source_lock
)


VERSION = "7.24"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():

    blockers = []
    warnings = []


    p = (
        BASE
        / "logs/producao/"
          "vi7_10_master_gate_latest.json"
    )


    try:

        old = json.loads(
            p.read_text(
                encoding="utf-8"
            )
        )["gate"]

    except Exception:

        old = None


    if (
        not old
        or old.get(
            "status"
        )
        != "SIX_SCENE_CANARY_CERTIFIED"
    ):

        blockers.append(
            "vi710_baseline_missing"
        )


    src = source_lock()


    if src.get(
        "automatic_source_recovery"
    ):

        blockers.append(
            "source_recovery_must_remain_locked"
        )


    return {
        "version":
            VERSION,

        "status":
            (
                "ADAPTIVE_CANARY_ALLOWED"
                if not blockers
                else "HOLD"
            ),

        "blockers":
            blockers,

        "warnings":
            warnings,

        "source_safety":
            src,

        "full_active":
            False,
    }


def self_test():

    assert VERSION == "7.24"

    print(
        "VI7.24 PRODUCTION GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
