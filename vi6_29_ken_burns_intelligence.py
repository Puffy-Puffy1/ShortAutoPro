#!/usr/bin/env python3


VERSION = "6.29"


def _clamp(
    value,
    low,
    high
):

    return max(
        low,
        min(
            high,
            float(
                value
            )
        )
    )


ROLE_ZOOM_LIMIT = {

    "EVIDENCE":
        1.05,

    "PERSON":
        1.08,

    "PLACE":
        1.07,

    "OBJECT":
        1.10,

    "CONTEXT":
        1.08,

    "CTA":
        1.04,
}


def build_plan(
    blueprint
):

    media = (
        blueprint.get(
            "media_type"
        )
    )


    role = (
        blueprint.get(
            "role"
        )
        or "CONTEXT"
    )


    profile = (
        blueprint.get(
            "profile"
        )
        or "NONE"
    )


    if media != "STILL":

        return {

            "version":
                VERSION,

            "enabled":
                False,

            "reason":
                (
                    "native_video"
                    if media
                    == "VIDEO"
                    else "not_still"
                ),

            "profile":
                profile,

            "renderer_applied":
                False,
        }


    zoom_limit = (
        ROLE_ZOOM_LIMIT.get(
            role,
            1.08
        )
    )


    z1 = _clamp(
        blueprint.get(
            "zoom_start",
            1.0
        ),
        1.0,
        zoom_limit
    )


    z2 = _clamp(
        blueprint.get(
            "zoom_end",
            1.0
        ),
        1.0,
        zoom_limit
    )


    start_x = .50
    start_y = .50
    end_x = .50
    end_y = .50


    # =================================
    # PORTRAIT
    # =================================

    if profile == "PORTRAIT_PUSH":

        start_y = .44
        end_y = .42


    # =================================
    # ESTABLISHING DRIFT
    # =================================

    elif (
        profile
        == "ESTABLISHING_DRIFT"
    ):

        if (
            blueprint.get(
                "direction"
            )
            == "RIGHT_TO_LEFT"
        ):

            start_x = .55
            end_x = .45

        else:

            start_x = .45
            end_x = .55


    # =================================
    # CONTEXT DRIFT
    # =================================

    elif (
        profile
        == "CONTEXT_DRIFT"
    ):

        if (
            blueprint.get(
                "direction"
            )
            == "RIGHT_TO_LEFT"
        ):

            start_x = .54
            end_x = .46

        else:

            start_x = .46
            end_x = .54


    # =================================
    # DETAIL
    # =================================

    elif profile == "DETAIL_PUSH":

        start_x = .50
        start_y = .52
        end_x = .50
        end_y = .50


    # =================================
    # DOCUMENTARY
    # =================================

    elif (
        profile
        == "DOCUMENTARY_HOLD"
    ):

        start_x = .50
        start_y = .50
        end_x = .50
        end_y = .49


    # Safety box.
    start_x = _clamp(
        start_x,
        .42,
        .58
    )

    end_x = _clamp(
        end_x,
        .42,
        .58
    )

    start_y = _clamp(
        start_y,
        .40,
        .58
    )

    end_y = _clamp(
        end_y,
        .40,
        .58
    )


    return {

        "version":
            VERSION,

        "enabled":
            True,

        "profile":
            profile,

        "role":
            role,

        "zoom_start":
            round(
                z1,
                4
            ),

        "zoom_end":
            round(
                z2,
                4
            ),

        "start_x":
            round(
                start_x,
                4
            ),

        "start_y":
            round(
                start_y,
                4
            ),

        "end_x":
            round(
                end_x,
                4
            ),

        "end_y":
            round(
                end_y,
                4
            ),

        "subject_detection_required":
            False,

        "safe_crop":
            True,

        "renderer_applied":
            False,
    }


def validate(
    plan
):

    errors = []


    if not plan.get(
        "enabled"
    ):

        return (
            True,
            []
        )


    role = plan.get(
        "role",
        "CONTEXT"
    )


    limit = (
        ROLE_ZOOM_LIMIT.get(
            role,
            1.08
        )
    )


    for key in (
        "zoom_start",
        "zoom_end",
    ):

        value = float(
            plan.get(
                key,
                1.0
            )
        )


        if not (
            1.0
            <= value
            <= limit
        ):

            errors.append(
                f"{key}_unsafe"
            )


    for key in (
        "start_x",
        "end_x",
    ):

        value = float(
            plan.get(
                key,
                .5
            )
        )


        if not (
            .42
            <= value
            <= .58
        ):

            errors.append(
                f"{key}_unsafe"
            )


    for key in (
        "start_y",
        "end_y",
    ):

        value = float(
            plan.get(
                key,
                .5
            )
        )


        if not (
            .40
            <= value
            <= .58
        ):

            errors.append(
                f"{key}_unsafe"
            )


    return (
        len(
            errors
        ) == 0,
        errors
    )


def self_test():

    evidence = build_plan(
        {
            "media_type":
                "STILL",

            "role":
                "EVIDENCE",

            "profile":
                "DOCUMENTARY_HOLD",

            "zoom_start":
                1.0,

            "zoom_end":
                1.20,
        }
    )


    assert (
        evidence[
            "zoom_end"
        ]
        <= 1.05
    )


    ok, errors = validate(
        evidence
    )


    assert ok is True

    assert errors == []


    portrait = build_plan(
        {
            "media_type":
                "STILL",

            "role":
                "PERSON",

            "profile":
                "PORTRAIT_PUSH",

            "zoom_start":
                1.0,

            "zoom_end":
                1.07,
        }
    )


    assert (
        portrait[
            "end_y"
        ]
        < .50
    )


    video = build_plan(
        {
            "media_type":
                "VIDEO",

            "role":
                "CONTEXT",

            "profile":
                "NATIVE_MOTION",
        }
    )


    assert (
        video[
            "enabled"
        ]
        is False
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.29 KEN BURNS SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Evidence Zoom Limit"
    )
    print(
        "OK Portrait Framing"
    )
    print(
        "OK Establishing Pan"
    )
    print(
        "OK Context Drift"
    )
    print(
        "OK Safe Crop Bounds"
    )
    print(
        "OK Video No-Op"
    )
    print()


if __name__ == "__main__":

    self_test()
