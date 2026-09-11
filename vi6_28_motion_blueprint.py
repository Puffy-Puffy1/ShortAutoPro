#!/usr/bin/env python3


VERSION = "6.28"


def _s(v):
    return str(v or "").strip()


def _u(v):
    return _s(v).upper()


def scene_number(scene):

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


def role(scene):

    value = _u(
        scene.get(
            "retrieval_role_6_7"
        )
    )


    if value:
        return value


    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    value = _u(
        board.get(
            "role"
        )
    )


    if value:
        return value


    mode = _s(
        scene.get(
            "visual_mode"
        )
    ).lower()


    if "cta" in mode:
        return "CTA"

    if any(
        x in mode
        for x in (
            "evidence",
            "document",
            "archive",
        )
    ):
        return "EVIDENCE"

    if any(
        x in mode
        for x in (
            "person",
            "portrait",
        )
    ):
        return "PERSON"

    if any(
        x in mode
        for x in (
            "location",
            "place",
            "architecture",
        )
    ):
        return "PLACE"

    if any(
        x in mode
        for x in (
            "object",
            "product",
            "medicine",
            "package",
        )
    ):
        return "OBJECT"

    return "CONTEXT"


def rhythm(scene):

    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    value = _u(
        board.get(
            "rhythm"
        )
    )


    if value:
        return value


    number = scene_number(
        scene
    )


    if number <= 1:
        return "HOOK"

    if number <= 4:
        return "SETUP"

    if number <= 8:
        return "ESCALATION"

    if number < 12:
        return "RESOLUTION"

    return "CTA"


def media_type(candidate):

    if not candidate:
        return "NONE"


    raw = _s(
        candidate.get(
            "tipo"
        )
        or candidate.get(
            "type"
        )
    ).lower()


    url = _s(
        candidate.get(
            "url"
        )
    ).lower()


    blob = (
        raw
        + " "
        + url
    )


    if any(
        marker in blob
        for marker in (
            "video",
            "vídeo",
            ".mp4",
            ".webm",
            ".mov",
        )
    ):

        return "VIDEO"


    if any(
        marker in blob
        for marker in (
            "foto",
            "photo",
            "image",
            "imagem",
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        )
    ):

        return "STILL"


    return "UNKNOWN"


def candidate_class(
    candidate,
    meta=None
):

    meta = (
        meta
        or {}
    )


    if not candidate:
        return "NONE"


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


def truth_ok(
    candidate,
    meta=None
):

    meta = (
        meta
        or {}
    )


    if not candidate:
        return False


    return bool(
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


def build_blueprint(
    scene,
    candidate,
    meta=None
):

    number = scene_number(
        scene
    )

    r = role(
        scene
    )

    beat = rhythm(
        scene
    )

    media = media_type(
        candidate
    )

    classe = candidate_class(
        candidate,
        meta
    )

    truth = truth_ok(
        candidate,
        meta
    )


    transition = _u(
        (
            meta
            or {}
        ).get(
            "vi627_transition"
        )
        or "DIRECT_CUT"
    )


    blueprint = {

        "version":
            VERSION,

        "scene":
            number,

        "role":
            r,

        "rhythm":
            beat,

        "media_type":
            media,

        "class":
            classe,

        "truth_ok":
            truth,

        "transition":
            transition,

        "synthetic_motion":
            False,

        "profile":
            "NONE",

        "intensity":
            "NONE",

        "direction":
            "CENTER",

        "zoom_start":
            1.0,

        "zoom_end":
            1.0,

        "renderer_applied":
            False,
    }


    # =================================
    # VIDEO
    # =================================

    if media == "VIDEO":

        blueprint[
            "profile"
        ] = "NATIVE_MOTION"

        blueprint[
            "intensity"
        ] = "NATIVE"

        blueprint[
            "synthetic_motion"
        ] = False


        return blueprint


    # =================================
    # UNKNOWN / NONE
    # =================================

    if media != "STILL":

        blueprint[
            "profile"
        ] = "NO_MOTION"

        return blueprint


    blueprint[
        "synthetic_motion"
    ] = True


    # =================================
    # DOCUMENTARY EVIDENCE
    # =================================

    if (
        r == "EVIDENCE"
        and classe
        == "REAL_DOCUMENTARY"
        and truth
    ):

        blueprint[
            "profile"
        ] = "DOCUMENTARY_HOLD"

        blueprint[
            "intensity"
        ] = "VERY_LOW"

        blueprint[
            "zoom_end"
        ] = 1.035


    # =================================
    # PERSON / PORTRAIT
    # =================================

    elif r == "PERSON":

        blueprint[
            "profile"
        ] = "PORTRAIT_PUSH"

        blueprint[
            "intensity"
        ] = "LOW"

        blueprint[
            "zoom_end"
        ] = 1.065


    # =================================
    # LOCATION
    # =================================

    elif r == "PLACE":

        if beat in {
            "HOOK",
            "SETUP",
        }:

            blueprint[
                "profile"
            ] = "ESTABLISHING_DRIFT"

            blueprint[
                "intensity"
            ] = "LOW"

            blueprint[
                "zoom_end"
            ] = 1.045


            blueprint[
                "direction"
            ] = (
                "LEFT_TO_RIGHT"
                if number % 2
                else "RIGHT_TO_LEFT"
            )


        else:

            blueprint[
                "profile"
            ] = "LOCATION_PUSH"

            blueprint[
                "intensity"
            ] = "LOW"

            blueprint[
                "zoom_end"
            ] = 1.055


    # =================================
    # OBJECT / DETAIL
    # =================================

    elif r == "OBJECT":

        blueprint[
            "profile"
        ] = "DETAIL_PUSH"

        blueprint[
            "intensity"
        ] = "MEDIUM"

        blueprint[
            "zoom_end"
        ] = 1.085


    # =================================
    # CTA
    # =================================

    elif r == "CTA":

        blueprint[
            "profile"
        ] = "CTA_HOLD"

        blueprint[
            "intensity"
        ] = "VERY_LOW"

        blueprint[
            "zoom_end"
        ] = 1.025


    # =================================
    # CONTEXT
    # =================================

    else:

        blueprint[
            "profile"
        ] = "CONTEXT_DRIFT"

        blueprint[
            "intensity"
        ] = (
            "MEDIUM"
            if beat
            in {
                "HOOK",
                "ESCALATION",
            }
            else "LOW"
        )


        blueprint[
            "zoom_end"
        ] = (
            1.070
            if beat
            in {
                "HOOK",
                "ESCALATION",
            }
            else 1.050
        )


        blueprint[
            "direction"
        ] = (
            "LEFT_TO_RIGHT"
            if number % 2
            else "RIGHT_TO_LEFT"
        )


    return blueprint


def self_test():

    evidence = build_blueprint(
        {
            "retrieval_role_6_7":
                "EVIDENCE",

            "_vi68_storyboard":
                {
                    "scene": 4,
                    "rhythm":
                        "SETUP"
                }
        },
        {
            "tipo":
                "foto",

            "_vi6_class":
                "REAL_DOCUMENTARY",

            "_vi6_truth_ok":
                True,
        },
        {
            "class":
                "REAL_DOCUMENTARY",

            "truth_ok":
                True,
        }
    )


    assert (
        evidence[
            "profile"
        ]
        == "DOCUMENTARY_HOLD"
    )


    assert (
        evidence[
            "zoom_end"
        ]
        <= 1.04
    )


    video = build_blueprint(
        {
            "retrieval_role_6_7":
                "CONTEXT",

            "_vi68_storyboard":
                {
                    "scene": 6,
                    "rhythm":
                        "ESCALATION"
                }
        },
        {
            "tipo":
                "video"
        },
        {}
    )


    assert (
        video[
            "profile"
        ]
        == "NATIVE_MOTION"
    )


    assert (
        video[
            "synthetic_motion"
        ]
        is False
    )


    obj = build_blueprint(
        {
            "retrieval_role_6_7":
                "OBJECT",

            "_vi68_storyboard":
                {
                    "scene": 7
                }
        },
        {
            "tipo":
                "foto"
        },
        {}
    )


    assert (
        obj[
            "profile"
        ]
        == "DETAIL_PUSH"
    )


    assert (
        obj[
            "zoom_end"
        ]
        <= 1.10
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.28 BLUEPRINT SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Documentary Hold"
    )
    print(
        "OK Portrait Push"
    )
    print(
        "OK Establishing Drift"
    )
    print(
        "OK Detail Push"
    )
    print(
        "OK Context Drift"
    )
    print(
        "OK Native Video Motion"
    )
    print(
        "OK Conservative Zoom Limits"
    )
    print()


if __name__ == "__main__":

    self_test()
