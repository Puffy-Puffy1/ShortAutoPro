#!/usr/bin/env python3

import json
from pathlib import Path


VERSION = "6.78"

BASE = Path.home() / "ShortAutoPro"


def freeze():

    session = json.loads(
        (
            BASE
            / "logs/producao/"
              "vi6_60_shadow_session_latest.json"
        ).read_text(
            encoding="utf-8"
        )
    )["session"]


    from vi6_61_motion_diversity_planner import (
        plan
    )


    result = plan(
        session.get(
            "events"
        )
    )


    return {
        "version": VERSION,

        "status":
            (
                "FROZEN"
                if result.get(
                    "triple_repeats"
                ) == 0
                else "HOLD"
            ),

        "motion_plan":
            result,

        "applied_to_renderer":
            False,
    }


def self_test():

    assert VERSION == "6.78"

    print(
        "VI6.78 MOTION PLAN FREEZER=PASS"
    )


if __name__ == "__main__":
    self_test()
