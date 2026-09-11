#!/usr/bin/env python3

from vi6_25_visual_sequence import (
    sequence_intent,
    recent_media_types,
)


VERSION = "6.26"


def _s(v):
    return str(v or "").strip()


def _u(v):
    return _s(v).upper()


def _f(
    v,
    default=0.0
):

    try:
        return float(v)

    except Exception:
        return float(default)


def candidate_media_type(
    item
):

    raw = _s(
        item.get(
            "tipo"
        )
        or item.get(
            "type"
        )
    ).lower()


    if any(
        marker in raw
        for marker in (
            "video",
            "vídeo",
            "mp4",
        )
    ):

        return "VIDEO"


    if any(
        marker in raw
        for marker in (
            "foto",
            "photo",
            "image",
            "imagem",
            "jpg",
            "jpeg",
            "png",
        )
    ):

        return "STILL"


    return "UNKNOWN"


def adjust(
    result,
    item,
    scene
):

    if result is None:
        return None


    result = dict(
        result
    )


    plan = sequence_intent(
        scene
    )


    media = candidate_media_type(
        item
    )


    classe = _u(
        result.get(
            "class"
        )
    )


    semantic = _f(
        result.get(
            "semantic"
        )
    )


    truth = bool(
        result.get(
            "truth_ok",
            False
        )
    )


    score = _f(
        result.get(
            "score"
        )
    )


    adjustment = 0.0


    # =================================
    # MOTION WHERE MOTION HELPS
    # =================================

    if (
        media == "VIDEO"
        and plan[
            "motion_need"
        ] == "HIGH"
        and semantic >= 58
    ):

        adjustment += 6.0


    elif (
        media == "VIDEO"
        and plan[
            "motion_need"
        ] == "MEDIUM"
        and semantic >= 58
    ):

        adjustment += 3.0


    # =================================
    # DOCUMENTARY STILL IS A FEATURE
    # NOT A FAILURE
    # =================================

    if (
        media == "STILL"
        and classe
        == "REAL_DOCUMENTARY"
        and truth
    ):

        if plan[
            "role"
        ] in {
            "EVIDENCE",
            "PERSON",
            "PLACE",
        }:

            adjustment += 7.0


        else:

            adjustment += 3.0


    # =================================
    # DON'T FORCE VIDEO INTO EVIDENCE
    # =================================

    if (
        media == "VIDEO"
        and plan[
            "role"
        ] in {
            "EVIDENCE",
            "PERSON",
        }
    ):

        if classe == "SAFE_CONTEXT":

            adjustment -= 7.0


    # =================================
    # MOTION FATIGUE
    # =================================

    recent = recent_media_types(
        2
    )


    if (
        media == "VIDEO"
        and len(recent) >= 2
        and all(
            value == "VIDEO"
            for value in recent
        )
    ):

        adjustment -= 6.0


    # =================================
    # STATIC FATIGUE
    # =================================

    if (
        media == "VIDEO"
        and plan[
            "role"
        ] == "CONTEXT"
        and semantic >= 60
        and len(recent) >= 2
        and all(
            value == "STILL"
            for value in recent
        )
    ):

        adjustment += 4.0


    # =================================
    # UNKNOWN MEDIA
    # =================================

    if media == "UNKNOWN":

        adjustment -= 2.0


    result[
        "score"
    ] = round(
        score
        + adjustment,
        3
    )


    reasons = list(
        result.get(
            "reasons",
            []
        )
        or []
    )


    if adjustment > 0:

        reasons.append(
            "vi626_motion_sequence_boost"
        )


    elif adjustment < 0:

        reasons.append(
            "vi626_motion_sequence_penalty"
        )


    result[
        "reasons"
    ] = reasons


    result[
        "vi625_intent"
    ] = plan[
        "intent"
    ]


    result[
        "vi625_motion_need"
    ] = plan[
        "motion_need"
    ]


    result[
        "vi626_media_type"
    ] = media


    result[
        "vi626_adjustment"
    ] = round(
        adjustment,
        3
    )


    return result


def self_test():

    from vi6_25_visual_sequence import (
        reset,
        record_choice,
    )


    reset()


    scene = {

        "retrieval_role_6_7":
            "EVIDENCE",

        "_vi68_storyboard":
            {
                "scene": 3,
                "rhythm": "SETUP"
            }
    }


    doc = adjust(
        {
            "score": 70,
            "class":
                "REAL_DOCUMENTARY",
            "truth_ok": True,
            "semantic": 70,
            "reasons": [],
        },
        {
            "tipo": "foto"
        },
        scene
    )


    stock_video = adjust(
        {
            "score": 70,
            "class":
                "SAFE_CONTEXT",
            "truth_ok": True,
            "semantic": 70,
            "reasons": [],
        },
        {
            "tipo": "video"
        },
        scene
    )


    assert (
        doc[
            "score"
        ] > 70
    )


    assert (
        stock_video[
            "score"
        ] < 70
    )


    record_choice(
        {
            "_vi68_storyboard":
                {
                    "scene": 1
                }
        },
        {
            "tipo": "video"
        }
    )


    record_choice(
        {
            "_vi68_storyboard":
                {
                    "scene": 2
                }
        },
        {
            "tipo": "video"
        }
    )


    context = adjust(
        {
            "score": 70,
            "class":
                "SAFE_CONTEXT",
            "truth_ok": True,
            "semantic": 70,
            "reasons": [],
        },
        {
            "tipo": "video"
        },
        {
            "retrieval_role_6_7":
                "CONTEXT",

            "_vi68_storyboard":
                {
                    "scene": 3,
                    "rhythm":
                        "ESCALATION"
                }
        }
    )


    assert (
        context[
            "vi626_adjustment"
        ] <= 6
    )


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.26 MOTION SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Documentary Still Boost"
    )
    print(
        "OK Context Motion Boost"
    )
    print(
        "OK Evidence Stock Video Penalty"
    )
    print(
        "OK Motion Fatigue Guard"
    )
    print(
        "OK Static Fatigue Recovery"
    )
    print()


if __name__ == "__main__":

    self_test()
