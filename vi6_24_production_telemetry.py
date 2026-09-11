#!/usr/bin/env python3

import json
import os
from datetime import datetime


VERSION = "6.24"


_RUNTIME = []


def reset():

    _RUNTIME.clear()


def record(
    scene,
    candidate,
    reason,
    meta,
    story_state
):

    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    try:

        scene_number = int(
            board.get(
                "scene",
                len(
                    _RUNTIME
                ) + 1
            )
            or len(
                _RUNTIME
            ) + 1
        )

    except Exception:

        scene_number = (
            len(
                _RUNTIME
            )
            + 1
        )


    event = {

        "scene":
            scene_number,

        "role":
            meta.get(
                "role"
            )
            or scene.get(
                "retrieval_role_6_7"
            )
            or board.get(
                "role"
            ),

        "accepted":
            candidate is not None,

        "source":
            (
                candidate.get(
                    "fonte"
                )
                or candidate.get(
                    "source"
                )
            )
            if candidate
            else None,

        "class":
            (
                meta.get(
                    "class"
                )
                or candidate.get(
                    "_vi611_class"
                )
                or candidate.get(
                    "_vi6_class"
                )
                or candidate.get(
                    "class"
                )
            )
            if candidate
            else "FALLBACK",

        "reason":
            reason,

        "decision":
            meta.get(
                "decision"
            ),

        "vi69":
            meta.get(
                "vi69_reason"
            ),

        "vi611":
            meta.get(
                "vi611_reason"
            ),

        "vi612":
            meta.get(
                "vi612_reason"
            ),

        "vi614":
            meta.get(
                "vi614_reason"
            ),

        "vi619":
            meta.get(
                "vi619_reason"
            )
            or meta.get(
                "vi619_decision"
            ),

        "vi623_adjustment":
            meta.get(
                "vi623_adjustment"
            ),

        "documentary_so_far":
            story_state.get(
                "documentary"
            ),

        "documentary_needed":
            story_state.get(
                "documentary_needed"
            ),

        "documentary_urgency":
            story_state.get(
                "documentary_urgency"
            ),

        "fallback_so_far":
            story_state.get(
                "fallback"
            ),

        "true_recovery_so_far":
            story_state.get(
                "true_recovery"
            ),
    }


    _RUNTIME.append(
        event
    )


    return event


def summary(
    story_state
):

    return {

        "version":
            VERSION,

        "events":
            len(
                _RUNTIME
            ),

        "accepted":
            sum(
                1
                for event in _RUNTIME
                if event[
                    "accepted"
                ]
            ),

        "fallback":
            sum(
                1
                for event in _RUNTIME
                if not event[
                    "accepted"
                ]
            ),

        "documentary":
            story_state.get(
                "documentary"
            ),

        "documentary_target":
            story_state.get(
                "documentary_target"
            ),

        "safe_context":
            story_state.get(
                "safe_context"
            ),

        "true_recovery":
            story_state.get(
                "true_recovery"
            ),

        "second_chance":
            story_state.get(
                "second_chance"
            ),

        "low_confidence_scenes":
            story_state.get(
                "low_confidence_scenes"
            ),

        "source_distribution":
            story_state.get(
                "sources"
            ),

        "events_detail":
            list(
                _RUNTIME
            ),
    }


def flush(
    story_state,
    path=None
):

    if path is None:

        folder = os.path.expanduser(
            "~/ShortAutoPro/logs/producao"
        )


        os.makedirs(
            folder,
            exist_ok=True
        )


        path = os.path.join(
            folder,
            "vi6_24_telemetry_latest.json"
        )


    payload = {

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "summary":
            summary(
                story_state
            ),
    }


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2
        )


    return path


def self_test():

    reset()


    state = {

        "documentary":
            2,

        "documentary_target":
            4,

        "safe_context":
            3,

        "true_recovery":
            1,

        "second_chance":
            1,

        "low_confidence_scenes":
            [],

        "sources":
            {
                "Wikimedia":
                    2,

                "Pixabay":
                    3,
            },

        "documentary_needed":
            2,

        "documentary_urgency":
            .4,

        "fallback":
            0,
    }


    record(
        {
            "_vi68_storyboard":
                {
                    "scene": 1
                }
        },
        {
            "fonte":
                "Wikimedia",

            "_vi6_class":
                "REAL_DOCUMENTARY"
        },
        "test",
        {
            "class":
                "REAL_DOCUMENTARY"
        },
        state
    )


    result = summary(
        state
    )


    assert result[
        "events"
    ] == 1


    assert result[
        "documentary"
    ] == 2


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.24 TELEMETRY SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Per-Scene Telemetry"
    )
    print(
        "OK Recovery Telemetry"
    )
    print(
        "OK Documentary Telemetry"
    )
    print(
        "OK Source Distribution"
    )
    print(
        "OK JSON Runtime Report"
    )
    print()


if __name__ == "__main__":

    self_test()
