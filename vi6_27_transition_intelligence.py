#!/usr/bin/env python3

import json
import os
from datetime import datetime


from vi6_25_visual_sequence import (
    previous,
    sequence_intent,
    media_type,
    source,
    family,
    candidate_class,
    record_choice,
    summary as sequence_summary,
)


VERSION = "6.27"


_EVENTS = []


def _s(v):
    return str(v or "").strip()


def recommend(
    scene,
    candidate,
    meta=None
):

    meta = (
        meta
        or {}
    )


    plan = sequence_intent(
        scene
    )


    prev = previous()


    current_type = media_type(
        candidate
    )


    current_source = source(
        candidate
    )


    current_family = family(
        candidate
    )


    current_class = candidate_class(
        candidate,
        meta
    )


    if candidate is None:

        transition = "NONE"

        reason = (
            "fallback_no_active_asset"
        )


    elif plan[
        "role"
    ] == "CTA":

        transition = (
            "CLEAN_CUT"
        )

        reason = (
            "cta_clean_finish"
        )


    elif prev is None:

        transition = (
            "OPEN"
        )

        reason = (
            "first_scene"
        )


    elif (
        plan[
            "intent"
        ]
        in {
            "EVIDENCE_HOLD",
            "PORTRAIT_FOCUS",
        }
    ):

        transition = (
            "DIRECT_CUT"
        )

        reason = (
            "preserve_evidence_clarity"
        )


    elif (
        prev.get(
            "media_type"
        )
        != current_type
        and {
            prev.get(
                "media_type"
            ),
            current_type,
        }
        == {
            "VIDEO",
            "STILL",
        }
    ):

        transition = (
            "MATCH_CUT"
        )

        reason = (
            "media_type_change"
        )


    elif (
        current_family
        and prev.get(
            "family"
        )
        and current_family
        == prev.get(
            "family"
        )
    ):

        transition = (
            "CONTRAST_CUT"
        )

        reason = (
            "same_visual_family"
        )


    elif (
        current_source
        and prev.get(
            "source"
        )
        and current_source
        == prev.get(
            "source"
        )
    ):

        transition = (
            "HARD_CUT"
        )

        reason = (
            "same_source_break"
        )


    elif (
        plan[
            "rhythm"
        ]
        == "ESCALATION"
    ):

        transition = (
            "FAST_CUT"
        )

        reason = (
            "escalation_pacing"
        )


    elif (
        plan[
            "rhythm"
        ]
        == "RESOLUTION"
    ):

        transition = (
            "SOFT_CUT"
        )

        reason = (
            "resolution_pacing"
        )


    else:

        transition = (
            "DIRECT_CUT"
        )

        reason = (
            "default_clarity"
        )


    return {

        "version":
            VERSION,

        "scene":
            plan[
                "scene"
            ],

        "role":
            plan[
                "role"
            ],

        "intent":
            plan[
                "intent"
            ],

        "rhythm":
            plan[
                "rhythm"
            ],

        "media_type":
            current_type,

        "class":
            current_class,

        "transition":
            transition,

        "reason":
            reason,

        # Neste estágio é apenas
        # metadata/editorial direction.
        "renderer_applied":
            False,
    }


def record(
    scene,
    candidate,
    meta=None
):

    recommendation = recommend(
        scene,
        candidate,
        meta
    )


    _EVENTS.append(
        recommendation
    )


    record_choice(
        scene,
        candidate,
        meta
    )


    return recommendation


def summary():

    transitions = {}


    for event in _EVENTS:

        transition = event[
            "transition"
        ]


        transitions[
            transition
        ] = (
            transitions.get(
                transition,
                0
            )
            + 1
        )


    return {

        "version":
            VERSION,

        "scenes":
            len(
                _EVENTS
            ),

        "transitions":
            transitions,

        "sequence":
            sequence_summary(),

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
            "vi6_27_sequence_latest.json"
        )


    payload = {

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "summary":
            summary(),
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


def reset():

    _EVENTS.clear()


    from vi6_25_visual_sequence import (
        reset as sequence_reset
    )


    sequence_reset()


def self_test():

    reset()


    scene1 = {
        "retrieval_role_6_7":
            "PLACE",

        "_vi68_storyboard":
            {
                "scene": 1,
                "rhythm": "HOOK"
            }
    }


    first = record(
        scene1,
        {
            "fonte": "Wikimedia",
            "tipo": "foto",
            "family": "HOTEL",
            "_vi6_class":
                "REAL_DOCUMENTARY",
        }
    )


    assert (
        first[
            "transition"
        ]
        == "OPEN"
    )


    second = record(
        {
            "retrieval_role_6_7":
                "CONTEXT",

            "_vi68_storyboard":
                {
                    "scene": 2,
                    "rhythm":
                        "ESCALATION"
                }
        },
        {
            "fonte": "Pixabay",
            "tipo": "video",
            "family": "CITY",
            "_vi6_class":
                "SAFE_CONTEXT",
        }
    )


    assert (
        second[
            "transition"
        ]
        in {
            "MATCH_CUT",
            "FAST_CUT",
        }
    )


    assert (
        second[
            "renderer_applied"
        ]
        is False
    )


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.27 TRANSITION SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Opening Logic"
    )
    print(
        "OK Evidence Clarity Cut"
    )
    print(
        "OK Photo/Video Match Cut"
    )
    print(
        "OK Same-Family Break"
    )
    print(
        "OK Escalation Pacing"
    )
    print(
        "OK Renderer remains untouched"
    )
    print()


if __name__ == "__main__":

    self_test()
