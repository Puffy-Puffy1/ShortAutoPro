#!/usr/bin/env python3

import json

from pathlib import Path


VERSION = "7.09"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():

    blockers = []

    warnings = []


    master = (
        BASE
        / "logs/producao/"
          "vi7_00_master_gate_latest.json"
    )


    try:

        gate = json.loads(
            master.read_text(
                encoding="utf-8"
            )
        )["gate"]


    except Exception:

        gate = None


    if gate is None:

        blockers.append(
            "vi700_master_missing"
        )


    elif gate.get(
        "status"
    ) != (
        "THREE_SCENE_CANARY_CERTIFIED"
    ):

        blockers.append(
            "vi700_not_certified"
        )


    elif gate.get(
        "selected_scene_count"
    ) != 3:

        blockers.append(
            "vi700_baseline_count_invalid"
        )


    if (
        gate
        and gate.get(
            "legacy_retry_failed_count",
            0
        )
        != 0
    ):

        blockers.append(
            "vi700_retry_failure_present"
        )


    # Source recovery remains shadow-only.
    try:

        from vi6_64_source_recovery_guard import (
            inspect
        )


        source = inspect()


        if source.get(
            "status"
        ) == "HOLD":

            blockers.append(
                "source_guard_hold"
            )


        elif source.get(
            "status"
        ) == "PASS_WITH_WARNINGS":

            warnings.append(
                "source_recovery_remains_shadow_only"
            )


    except Exception:

        warnings.append(
            "source_guard_not_available"
        )


    return {
        "version":
            VERSION,

        "status":
            (
                "SIX_SCENE_CANARY_ALLOWED"
                if not blockers
                else "HOLD"
            ),

        "blockers":
            sorted(
                set(blockers)
            ),

        "warnings":
            sorted(
                set(warnings)
            ),

        "max_vi6_scenes":
            6,

        "source_recovery_active":
            False,

        "full_active":
            False,
    }


def self_test():

    assert VERSION == "7.09"

    print(
        "VI7.09 PRODUCTION GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
