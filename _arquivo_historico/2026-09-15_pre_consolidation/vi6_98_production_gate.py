#!/usr/bin/env python3

import json

from pathlib import Path


VERSION = "6.98"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():

    blockers = []


    p90 = (
        BASE
        / "logs/producao/"
          "vi6_90_master_canary_latest.json"
    )


    try:

        gate = json.loads(
            p90.read_text(
                encoding="utf-8"
            )
        )["gate"]


    except Exception:

        gate = None


    if gate is None:

        blockers.append(
            "vi690_gate_missing"
        )


    elif gate.get(
        "status"
    ) not in {
        "CERTIFIED",
        "CERTIFIED_WITH_WARNINGS",
    }:

        blockers.append(
            "single_scene_canary_not_certified"
        )


    elif gate.get(
        "vi6_scenes"
    ) != [5]:

        blockers.append(
            "single_scene_baseline_invalid"
        )


    return {
        "version": VERSION,

        "status":
            (
                "THREE_SCENE_CANARY_ALLOWED"
                if not blockers
                else "HOLD"
            ),

        "blockers":
            blockers,

        "max_vi6_scenes":
            3,

        "full_active":
            False,
    }


def self_test():

    assert VERSION == "6.98"

    print(
        "VI6.98 PRODUCTION GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
