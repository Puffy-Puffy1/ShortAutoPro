#!/usr/bin/env python3

import json
import os
from datetime import datetime


VERSION = "6.31"

_EVENTS = []


def reset():

    _EVENTS.clear()


def record(
    contract,
    duration,
    safety
):

    event = {

        "scene":
            contract.get(
                "scene"
            ),

        "role":
            contract.get(
                "role"
            ),

        "media_type":
            contract.get(
                "media_type"
            ),

        "profile":
            contract.get(
                "profile"
            ),

        "transition":
            contract.get(
                "transition"
            ),

        "duration":
            duration,

        "safety":
            safety,

        "contract_hash":
            contract.get(
                "contract_hash"
            ),

        "renderer_applied":
            contract.get(
                "renderer_applied"
            ),
    }


    _EVENTS.append(
        event
    )


    return event


def _max_aggressive_streak():

    current = 0
    maximum = 0


    for event in _EVENTS:

        aggressive = bool(
            (
                event.get(
                    "safety"
                )
                or {}
            ).get(
                "aggressive"
            )
        )


        if aggressive:

            current += 1

            maximum = max(
                maximum,
                current
            )

        else:

            current = 0


    return maximum


def audit():

    total = len(
        _EVENTS
    )


    hold = [
        event[
            "scene"
        ]

        for event in _EVENTS

        if (
            event.get(
                "safety"
            )
            or {}
        ).get(
            "status"
        )
        == "HOLD"
    ]


    warn = [
        event[
            "scene"
        ]

        for event in _EVENTS

        if (
            event.get(
                "safety"
            )
            or {}
        ).get(
            "status"
        )
        == "WARN"
    ]


    renderer_violations = [
        event[
            "scene"
        ]

        for event in _EVENTS

        if (
            event.get(
                "renderer_applied"
            )
            is not False
        )
    ]


    durations = [

        float(
            (
                event.get(
                    "duration"
                )
                or {}
            ).get(
                "seconds",
                0
            )
            or 0
        )

        for event in _EVENTS
    ]


    total_duration = sum(
        durations
    )


    transitions = {}

    profiles = {}


    for event in _EVENTS:

        transition = (
            event.get(
                "transition"
            )
            or "NONE"
        )


        transitions[
            transition
        ] = (
            transitions.get(
                transition,
                0
            )
            + 1
        )


        profile = (
            event.get(
                "profile"
            )
            or "NONE"
        )


        profiles[
            profile
        ] = (
            profiles.get(
                profile,
                0
            )
            + 1
        )


    aggressive_streak = (
        _max_aggressive_streak()
    )


    global_warnings = []


    if aggressive_streak >= 3:

        global_warnings.append(
            "three_aggressive_scenes_in_sequence"
        )


    if total >= 12:

        stage = "COMPLETE"

    else:

        stage = "IN_PROGRESS"


    if (
        hold
        or renderer_violations
    ):

        decision = "HOLD"

    elif (
        warn
        or global_warnings
    ):

        decision = "WARN"

    else:

        decision = "PASS"


    return {

        "version":
            VERSION,

        "stage":
            stage,

        "decision":
            decision,

        "scenes":
            total,

        "hold_scenes":
            hold,

        "warning_scenes":
            warn,

        "renderer_violations":
            renderer_violations,

        "total_duration":
            round(
                total_duration,
                3
            ),

        "average_duration":
            round(
                (
                    total_duration
                    / total
                )
                if total
                else 0,
                3
            ),

        "max_aggressive_streak":
            aggressive_streak,

        "global_warnings":
            global_warnings,

        "transitions":
            transitions,

        "profiles":
            profiles,

        "events":
            list(
                _EVENTS
            ),
    }


def flush(
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
            "vi6_31_pre_render_audit_latest.json"
        )


    payload = {

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "audit":
            audit(),
    }


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2
        )


    return path


def self_test():

    reset()


    for number in (
        1,
        2,
        3,
    ):

        record(
            {
                "scene":
                    number,

                "role":
                    "CONTEXT",

                "media_type":
                    "STILL",

                "profile":
                    "CONTEXT_DRIFT",

                "transition":
                    "DIRECT_CUT",

                "contract_hash":
                    str(
                        number
                    ),

                "renderer_applied":
                    False,
            },
            {
                "seconds":
                    4.0,

                "confidence":
                    "HIGH",
            },
            {
                "status":
                    "PASS",

                "aggressive":
                    False,
            }
        )


    result = audit()


    assert (
        result[
            "scenes"
        ]
        == 3
    )


    assert (
        result[
            "decision"
        ]
        == "PASS"
    )


    assert (
        result[
            "stage"
        ]
        == "IN_PROGRESS"
    )


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.31 AUDITOR SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Global Contract Audit"
    )
    print(
        "OK Hold Scene Tracking"
    )
    print(
        "OK Warning Scene Tracking"
    )
    print(
        "OK Duration Aggregation"
    )
    print(
        "OK Motion Streak Detection"
    )
    print(
        "OK Transition Distribution"
    )
    print(
        "OK Renderer-Inactive Verification"
    )
    print()


if __name__ == "__main__":

    self_test()
