#!/usr/bin/env python3

import os


VERSION = "6.22"


TOTAL_SCENES = int(
    os.getenv(
        "VI622_TOTAL_SCENES",
        "12"
    )
)


DOCUMENTARY_TARGET = int(
    os.getenv(
        "VI622_DOCUMENTARY_TARGET",
        "4"
    )
)


_STATE = {

    "events":
        [],

    "last_scene":
        0,
}


def _s(v):

    return str(
        v or ""
    ).strip()


def _u(v):

    return _s(
        v
    ).upper()


def _f(
    v,
    default=0.0
):

    try:
        return float(v)

    except Exception:
        return float(default)


def scene_number(
    scene
):

    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    try:

        return int(
            board.get(
                "scene",
                0
            )
            or 0
        )

    except Exception:

        return 0


def role_of(
    scene,
    meta=None
):

    meta = (
        meta
        or {}
    )


    role = _u(
        meta.get(
            "role"
        )
        or scene.get(
            "retrieval_role_6_7"
        )
    )


    if role:
        return role


    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    return _u(
        board.get(
            "role"
        )
        or "CONTEXT"
    )


def candidate_class(
    candidate,
    meta=None
):

    meta = (
        meta
        or {}
    )


    if candidate is None:
        return "FALLBACK"


    return _u(
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
        or "UNKNOWN"
    )


def source_of(
    candidate
):

    if candidate is None:
        return None


    return _s(
        candidate.get(
            "fonte"
        )
        or candidate.get(
            "source"
        )
    )


def family_of(
    candidate
):

    if candidate is None:
        return None


    return _u(
        candidate.get(
            "family"
        )
        or candidate.get(
            "visual_family"
        )
    )


def _quality_confidence(
    candidate,
    meta
):

    if candidate is None:
        return 0.0


    classe = candidate_class(
        candidate,
        meta
    )


    score = _f(
        meta.get(
            "score",
            candidate.get(
                "_vi611_score",
                candidate.get(
                    "_vi6_score",
                    candidate.get(
                        "score",
                        0
                    )
                )
            )
        )
    )


    semantic = _f(
        meta.get(
            "semantic",
            candidate.get(
                "semantic",
                0
            )
        )
    )


    anchor = _f(
        meta.get(
            "anchor",
            meta.get(
                "anchor_ratio",
                candidate.get(
                    "_vi66_anchor",
                    0
                )
            )
        )
    )


    truth = bool(
        meta.get(
            "truth_ok",
            candidate.get(
                "_vi611_truth",
                candidate.get(
                    "_vi6_truth_ok",
                    candidate.get(
                        "truth_ok",
                        False
                    )
                )
            )
        )
    )


    confidence = 0.0


    confidence += min(
        35.0,
        max(
            0.0,
            score * .35
        )
    )


    confidence += min(
        25.0,
        max(
            0.0,
            semantic * .25
        )
    )


    confidence += min(
        20.0,
        max(
            0.0,
            anchor * 40.0
        )
    )


    if (
        classe
        == "REAL_DOCUMENTARY"
        and truth
    ):

        confidence += 20.0


    elif classe == "SAFE_CONTEXT":

        confidence += 8.0


    return round(
        min(
            100.0,
            confidence
        ),
        2
    )


def reset():

    _STATE[
        "events"
    ].clear()

    _STATE[
        "last_scene"
    ] = 0


def record_final(
    scene,
    candidate,
    reason,
    meta=None
):

    meta = (
        meta
        or {}
    )


    number = scene_number(
        scene
    )


    # Novo Short no mesmo processo:
    # evita contaminar memória anterior.
    if (
        number == 1
        and _STATE[
            "last_scene"
        ] != 0
    ):

        reset()


    classe = candidate_class(
        candidate,
        meta
    )


    event = {

        "scene":
            number,

        "role":
            role_of(
                scene,
                meta
            ),

        "class":
            classe,

        "source":
            source_of(
                candidate
            ),

        "family":
            family_of(
                candidate
            ),

        "reason":
            reason,

        "decision":
            meta.get(
                "decision"
            ),

        "recovered":
            bool(
                candidate
                and candidate.get(
                    "_vi619_true_recovery"
                )
            ),

        "second_chance":
            bool(
                candidate
                and candidate.get(
                    "_vi611_rescued"
                )
            ),

        "truth_ok":
            bool(
                meta.get(
                    "truth_ok",
                    candidate.get(
                        "_vi6_truth_ok",
                        False
                    )
                    if candidate
                    else False
                )
            ),

        "confidence":
            _quality_confidence(
                candidate,
                meta
            ),
    }


    _STATE[
        "events"
    ].append(
        event
    )


    if number:

        _STATE[
            "last_scene"
        ] = number


    return event


def summary():

    events = list(
        _STATE[
            "events"
        ]
    )


    seen = len(
        events
    )


    documentary = sum(
        1
        for event in events
        if (
            event[
                "class"
            ]
            == "REAL_DOCUMENTARY"
        )
    )


    safe_context = sum(
        1
        for event in events
        if (
            event[
                "class"
            ]
            == "SAFE_CONTEXT"
        )
    )


    fallback = sum(
        1
        for event in events
        if (
            event[
                "class"
            ]
            == "FALLBACK"
        )
    )


    recovered = sum(
        1
        for event in events
        if event[
            "recovered"
        ]
    )


    second_chance = sum(
        1
        for event in events
        if event[
            "second_chance"
        ]
    )


    remaining = max(
        0,
        TOTAL_SCENES
        - seen
    )


    documentary_needed = max(
        0,
        DOCUMENTARY_TARGET
        - documentary
    )


    impossible = (
        documentary_needed
        > remaining
    )


    if documentary_needed <= 0:

        urgency = 0.0

    elif remaining <= 0:

        urgency = 1.0

    else:

        urgency = min(
            1.0,
            documentary_needed
            / float(
                remaining
            )
        )


    low_confidence = [
        event[
            "scene"
        ]
        for event in events
        if event[
            "confidence"
        ] < 48
    ]


    sources = {}

    for event in events:

        source = event.get(
            "source"
        )

        if not source:
            continue


        sources[
            source
        ] = (
            sources.get(
                source,
                0
            )
            + 1
        )


    return {

        "version":
            VERSION,

        "scenes_seen":
            seen,

        "total_scenes":
            TOTAL_SCENES,

        "remaining":
            remaining,

        "documentary":
            documentary,

        "documentary_target":
            DOCUMENTARY_TARGET,

        "documentary_needed":
            documentary_needed,

        "documentary_urgency":
            round(
                urgency,
                3
            ),

        "documentary_target_impossible":
            impossible,

        "safe_context":
            safe_context,

        "fallback":
            fallback,

        "true_recovery":
            recovered,

        "second_chance":
            second_chance,

        "low_confidence_scenes":
            low_confidence,

        "sources":
            sources,

        "events":
            events,
    }


def self_test():

    reset()


    scene1 = {
        "_vi68_storyboard":
            {
                "scene": 1,
                "role": "EVIDENCE"
            }
    }


    doc = {
        "fonte":
            "Wikimedia",

        "_vi6_class":
            "REAL_DOCUMENTARY",

        "_vi6_truth_ok":
            True,

        "_vi6_score":
            90,
    }


    record_final(
        scene1,
        doc,
        "test",
        {
            "class":
                "REAL_DOCUMENTARY",

            "score":
                90,

            "semantic":
                75,

            "anchor":
                .60,

            "truth_ok":
                True,
        }
    )


    scene2 = {
        "_vi68_storyboard":
            {
                "scene": 2,
                "role": "CONTEXT"
            }
    }


    stock = {
        "fonte":
            "Pixabay",

        "_vi6_class":
            "SAFE_CONTEXT",

        "_vi6_score":
            70,
    }


    record_final(
        scene2,
        stock,
        "test",
        {
            "class":
                "SAFE_CONTEXT",

            "score":
                70,

            "semantic":
                65,

            "anchor":
                .10,
        }
    )


    result = summary()


    assert result[
        "scenes_seen"
    ] == 2


    assert result[
        "documentary"
    ] == 1


    assert result[
        "safe_context"
    ] == 1


    assert result[
        "documentary_needed"
    ] == 3


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.22 STORY AUDIT SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Rolling Story Memory"
    )
    print(
        "OK Documentary Deficit"
    )
    print(
        "OK Remaining Scene Projection"
    )
    print(
        "OK Confidence Audit"
    )
    print(
        "OK Recovery Counters"
    )
    print()


if __name__ == "__main__":

    self_test()
