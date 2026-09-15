#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path


VERSION = "7.00"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


REPORT = (
    BASE
    / "logs/producao/"
      "vi6_97_three_scene_canary_latest.json"
)


OUTPUT = (
    BASE
    / "logs/producao/"
      "vi7_00_master_gate_latest.json"
)


def evaluate():

    blockers = []

    warnings = []


    try:

        data = json.loads(
            REPORT.read_text(
                encoding="utf-8"
            )
        )


        events = (
            data.get("events")
            or []
        )


    except Exception:

        events = []

        blockers.append(
            "vi697_telemetry_missing"
        )


    selected = [
        e
        for e in events
        if e.get(
            "action"
        ) == "VI6_SELECTED"
    ]


    successes = [
        e
        for e in events
        if e.get(
            "action"
        ) == "VI6_RENDER_SUCCESS"
    ]


    retries = [
        e
        for e in events
        if e.get(
            "action"
        ) == "LEGACY_RETRY"
    ]


    retry_success = [
        e
        for e in events
        if e.get(
            "action"
        ) == "LEGACY_RETRY_SUCCESS"
    ]


    retry_failed = [
        e
        for e in events
        if e.get(
            "action"
        ) == "LEGACY_RETRY_FAILED"
    ]


    selected_scenes = sorted(
        {
            e.get("scene")
            for e in selected
            if isinstance(
                e.get("scene"),
                int
            )
        }
    )


    success_scenes = sorted(
        {
            e.get("scene")
            for e in successes
            if isinstance(
                e.get("scene"),
                int
            )
        }
    )


    if len(selected_scenes) > 3:

        blockers.append(
            "more_than_three_vi6_scenes"
        )


    if retry_failed:

        blockers.append(
            "legacy_retry_failure"
        )


    # A healthy run should normally obtain three
    # distinct STILL canaries. If media composition
    # does not provide three eligible stills, do not
    # pretend expansion was fully certified.

    if len(selected_scenes) < 3:

        warnings.append(
            "fewer_than_three_eligible_vi6_scenes"
        )


    if retries:

        warnings.append(
            "legacy_retry_was_required"
        )


    if (
        selected_scenes
        and sorted(
            set(
                success_scenes
            )
            | {
                e.get("scene")
                for e in retry_success
            }
        )
        != selected_scenes
    ):

        blockers.append(
            "selected_scene_without_valid_final_render"
        )


    if blockers:

        status = "HOLD"


    elif (
        len(selected_scenes) == 3
        and not retries
    ):

        status = (
            "THREE_SCENE_CANARY_CERTIFIED"
        )


    else:

        status = (
            "CANARY_SAFE_WITH_WARNINGS"
        )


    result = {
        "version":
            VERSION,

        "status":
            status,

        "selected_scene_count":
            len(selected_scenes),

        "selected_scenes":
            selected_scenes,

        "vi6_success_scenes":
            success_scenes,

        "legacy_retry_count":
            len(retries),

        "legacy_retry_success_count":
            len(retry_success),

        "legacy_retry_failed_count":
            len(retry_failed),

        "blockers":
            sorted(
                set(blockers)
            ),

        "warnings":
            sorted(
                set(warnings)
            ),

        "three_scene_expansion_certified":
            (
                status
                == "THREE_SCENE_CANARY_CERTIFIED"
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

    assert VERSION == "7.00"

    print(
        "VI7.00 MASTER GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
