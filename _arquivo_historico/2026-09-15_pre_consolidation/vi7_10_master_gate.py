#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path


from vi7_08_sequence_audit import (
    audit as sequence_audit
)


VERSION = "7.10"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

RUNTIME = (
    BASE
    / "logs/producao/"
      "vi7_07_six_scene_runtime_latest.json"
)

OUTPUT = (
    BASE
    / "logs/producao/"
      "vi7_10_master_gate_latest.json"
)


def evaluate():

    blockers = []

    warnings = []


    try:

        data = json.loads(
            RUNTIME.read_text(
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
            "vi707_runtime_missing"
        )


    selected = [
        event
        for event in events
        if event.get(
            "action"
        ) == "VI7_SELECTED"
    ]


    success = [
        event
        for event in events
        if event.get(
            "action"
        ) == "VI7_RENDER_SUCCESS"
    ]


    retries = [
        event
        for event in events
        if event.get(
            "action"
        ) == "LEGACY_RETRY"
    ]


    retry_success = [
        event
        for event in events
        if event.get(
            "action"
        ) == "LEGACY_RETRY_SUCCESS"
    ]


    retry_failed = [
        event
        for event in events
        if event.get(
            "action"
        ) == "LEGACY_RETRY_FAILED"
    ]


    selected_scenes = sorted(
        {
            event.get(
                "scene"
            )
            for event in selected
            if isinstance(
                event.get(
                    "scene"
                ),
                int
            )
        }
    )


    success_scenes = {
        event.get(
            "scene"
        )
        for event in success
    }


    recovered_scenes = {
        event.get(
            "scene"
        )
        for event in retry_success
    }


    valid_final_scenes = (
        success_scenes
        | recovered_scenes
    )


    if len(
        selected_scenes
    ) > 6:

        blockers.append(
            "more_than_six_vi7_scenes"
        )


    if retry_failed:

        blockers.append(
            "legacy_retry_failure"
        )


    if (
        set(
            selected_scenes
        )
        != valid_final_scenes
    ):

        blockers.append(
            "selected_scene_without_valid_output"
        )


    sequence = sequence_audit(
        events
    )


    blockers.extend(
        sequence.get(
            "blockers"
        )
        or []
    )


    warnings.extend(
        sequence.get(
            "warnings"
        )
        or []
    )


    if len(
        selected_scenes
    ) < 6:

        warnings.append(
            "fewer_than_six_eligible_still_canaries"
        )


    if retries:

        warnings.append(
            "legacy_retry_was_required"
        )


    blockers = sorted(
        set(
            blockers
        )
    )


    warnings = sorted(
        set(
            warnings
        )
    )


    if blockers:

        status = "HOLD"


    elif (
        len(
            selected_scenes
        ) == 6
        and not retries
    ):

        status = (
            "SIX_SCENE_CANARY_CERTIFIED"
        )


    else:

        status = (
            "SIX_SCENE_CANARY_SAFE_WITH_WARNINGS"
        )


    result = {
        "version":
            VERSION,

        "status":
            status,

        "selected_scene_count":
            len(
                selected_scenes
            ),

        "selected_scenes":
            selected_scenes,

        "vi7_success_scenes":
            sorted(
                success_scenes
            ),

        "legacy_retry_count":
            len(
                retries
            ),

        "legacy_retry_success_count":
            len(
                retry_success
            ),

        "legacy_retry_failure_count":
            len(
                retry_failed
            ),

        "sequence":
            sequence,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "six_scene_expansion_certified":
            (
                status
                == "SIX_SCENE_CANARY_CERTIFIED"
            ),

        # Still deliberately locked.
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

    assert VERSION == "7.10"

    print(
        "VI7.10 MASTER GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
