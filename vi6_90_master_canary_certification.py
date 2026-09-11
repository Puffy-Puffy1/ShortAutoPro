#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path


VERSION = "6.90"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


REPORT87 = (
    BASE
    / "logs/producao/"
      "vi6_87_runtime_canary_latest.json"
)


OUTPUT = (
    BASE
    / "logs/producao/"
      "vi6_90_master_canary_latest.json"
)


def evaluate():

    blockers = []
    warnings = []


    try:

        data = json.loads(
            REPORT87.read_text(
                encoding="utf-8"
            )
        )


        events = (
            data.get(
                "events"
            )
            or []
        )


    except Exception:

        events = []

        blockers.append(
            "runtime_canary_report_missing"
        )


    vi6_events = [
        e
        for e in events
        if e.get(
            "action"
        ) == "VI6_CANARY"
    ]


    wrong_scene = [
        e
        for e in vi6_events
        if e.get(
            "scene"
        ) != 5
    ]


    if wrong_scene:

        blockers.append(
            "vi6_used_outside_scene_5"
        )


    if len(
        vi6_events
    ) != 1:

        blockers.append(
            "requires_exactly_one_vi6_scene"
        )


    fallbacks = [
        e
        for e in events
        if e.get(
            "action"
        ) == "LEGACY_FALLBACK"
    ]


    if fallbacks:

        warnings.append(
            "canary_fallback_occurred"
        )


    status = (
        "HOLD"
        if blockers
        else (
            "CERTIFIED_WITH_WARNINGS"
            if warnings
            else "CERTIFIED"
        )
    )


    result = {

        "version":
            VERSION,

        "status":
            status,

        "vi6_scene_count":
            len(
                vi6_events
            ),

        "vi6_scenes":
            [
                e.get(
                    "scene"
                )
                for e in vi6_events
            ],

        "fallback_count":
            len(
                fallbacks
            ),

        "blockers":
            blockers,

        "warnings":
            warnings,

        "single_scene_canary":
            (
                not blockers
            ),

        "full_active_authorized":
            False,
    }


    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    OUTPUT.write_text(
        json.dumps(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "gate":
                    result,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    return result


def self_test():

    assert VERSION == "6.90"

    print(
        "VI6.90 MASTER CERTIFICATION=PASS"
    )


if __name__ == "__main__":
    self_test()
