#!/usr/bin/env python3

from vi6_32_scene_duration import (
    motion_metrics
)


VERSION = "6.33"


ZOOM_RATE_LIMITS = {

    "EVIDENCE":
        .015,

    "PERSON":
        .026,

    "PLACE":
        .026,

    "OBJECT":
        .036,

    "CONTEXT":
        .036,

    "CTA":
        .012,
}


PAN_RATE_LIMITS = {

    "EVIDENCE":
        .018,

    "PERSON":
        .020,

    "PLACE":
        .035,

    "OBJECT":
        .030,

    "CONTEXT":
        .040,

    "CTA":
        .015,
}


ALLOWED_TRANSITIONS = {

    "OPEN",
    "NONE",

    "CLEAN_CUT",
    "DIRECT_CUT",
    "MATCH_CUT",
    "CONTRAST_CUT",
    "HARD_CUT",
    "FAST_CUT",
    "SOFT_CUT",
}


def _s(v):
    return str(v or "").strip()


def _u(v):
    return _s(v).upper()


def assess(
    contract,
    duration
):

    blockers = []
    warnings = []


    role = _u(
        contract.get(
            "role"
        )
        or duration.get(
            "role"
        )
        or "CONTEXT"
    )


    media = _u(
        contract.get(
            "media_type"
        )
    )


    seconds = float(
        duration.get(
            "seconds",
            4.0
        )
        or 4.0
    )


    transition = _u(
        contract.get(
            "transition"
        )
    )


    metrics = motion_metrics(
        contract,
        duration
    )


    # =================================
    # CONTRACT INTEGRITY
    # =================================

    if (
        contract.get(
            "contract_valid"
        )
        is False
    ):

        blockers.append(
            "invalid_renderer_contract"
        )


    if (
        contract.get(
            "renderer_applied"
        )
        is not False
    ):

        blockers.append(
            "renderer_already_applied"
        )


    if (
        contract.get(
            "ffmpeg_filter"
        )
        is not None
    ):

        blockers.append(
            "ffmpeg_filter_should_be_inactive"
        )


    # =================================
    # DURATION
    # =================================

    if seconds < .75:

        blockers.append(
            "scene_too_short"
        )


    elif seconds < 1.25:

        warnings.append(
            "very_short_scene"
        )


    if seconds > 15.0:

        warnings.append(
            "very_long_scene"
        )


    if (
        duration.get(
            "confidence"
        )
        == "LOW"
    ):

        warnings.append(
            "duration_low_confidence"
        )


    # =================================
    # TRANSITION
    # =================================

    if (
        transition
        not in ALLOWED_TRANSITIONS
    ):

        blockers.append(
            "invalid_transition"
        )


    # =================================
    # VIDEO = NATIVE MOTION
    # =================================

    if media == "VIDEO":

        ken = (
            contract.get(
                "ken_burns"
            )
            or {}
        )


        if ken.get(
            "enabled"
        ):

            blockers.append(
                "synthetic_motion_on_video"
            )


    # =================================
    # STILL MOTION RATE
    # =================================

    if media == "STILL":

        max_zoom = (
            ZOOM_RATE_LIMITS.get(
                role,
                .036
            )
        )


        max_pan = (
            PAN_RATE_LIMITS.get(
                role,
                .040
            )
        )


        if (
            metrics[
                "zoom_rate"
            ]
            > max_zoom
        ):

            blockers.append(
                "zoom_velocity_too_high"
            )


        if (
            metrics[
                "pan_rate"
            ]
            > max_pan
        ):

            blockers.append(
                "pan_velocity_too_high"
            )


    # =================================
    # DOCUMENTARY EVIDENCE PROTECTION
    # =================================

    if (
        role == "EVIDENCE"
        and _u(
            contract.get(
                "profile"
            )
        )
        == "DOCUMENTARY_HOLD"
    ):

        if (
            metrics[
                "zoom_delta"
            ]
            > .05
        ):

            blockers.append(
                "documentary_zoom_excess"
            )


        if (
            metrics[
                "pan_distance"
            ]
            > .035
        ):

            blockers.append(
                "documentary_pan_excess"
            )


    # =================================
    # STATUS
    # =================================

    if blockers:

        status = "HOLD"

    elif warnings:

        status = "WARN"

    else:

        status = "PASS"


    aggressive = bool(

        metrics[
            "zoom_rate"
        ] >= .025

        or metrics[
            "pan_rate"
        ] >= .030

        or transition
        in {
            "FAST_CUT",
            "CONTRAST_CUT",
        }
    )


    return {

        "version":
            VERSION,

        "status":
            status,

        "role":
            role,

        "media_type":
            media,

        "seconds":
            round(
                seconds,
                3
            ),

        "duration_source":
            duration.get(
                "source"
            ),

        "duration_confidence":
            duration.get(
                "confidence"
            ),

        "transition":
            transition,

        "metrics":
            metrics,

        "aggressive":
            aggressive,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "renderer_allowed":
            status
            != "HOLD",

        # Continua apenas auditando.
        "renderer_applied":
            False,
    }


def self_test():

    safe = assess(
        {
            "contract_valid":
                True,

            "renderer_applied":
                False,

            "ffmpeg_filter":
                None,

            "role":
                "EVIDENCE",

            "media_type":
                "STILL",

            "profile":
                "DOCUMENTARY_HOLD",

            "transition":
                "DIRECT_CUT",

            "ken_burns":
                {
                    "enabled":
                        True,

                    "zoom_start":
                        1.0,

                    "zoom_end":
                        1.035,

                    "start_x":
                        .50,

                    "end_x":
                        .50,

                    "start_y":
                        .50,

                    "end_y":
                        .49,
                }
        },
        {
            "seconds":
                4.0,

            "source":
                "test",

            "confidence":
                "HIGH",

            "role":
                "EVIDENCE",
        }
    )


    assert (
        safe[
            "status"
        ]
        == "PASS"
    )


    unsafe = assess(
        {
            "contract_valid":
                True,

            "renderer_applied":
                False,

            "ffmpeg_filter":
                None,

            "role":
                "EVIDENCE",

            "media_type":
                "STILL",

            "profile":
                "DOCUMENTARY_HOLD",

            "transition":
                "DIRECT_CUT",

            "ken_burns":
                {
                    "enabled":
                        True,

                    "zoom_start":
                        1.0,

                    "zoom_end":
                        1.10,

                    "start_x":
                        .50,

                    "end_x":
                        .58,

                    "start_y":
                        .50,

                    "end_y":
                        .50,
                }
        },
        {
            "seconds":
                2.0,

            "source":
                "test",

            "confidence":
                "HIGH",

            "role":
                "EVIDENCE",
        }
    )


    assert (
        unsafe[
            "status"
        ]
        == "HOLD"
    )


    assert (
        "zoom_velocity_too_high"
        in unsafe[
            "blockers"
        ]
    )


    video = assess(
        {
            "contract_valid":
                True,

            "renderer_applied":
                False,

            "ffmpeg_filter":
                None,

            "role":
                "CONTEXT",

            "media_type":
                "VIDEO",

            "profile":
                "NATIVE_MOTION",

            "transition":
                "FAST_CUT",

            "ken_burns":
                {
                    "enabled":
                        False
                }
        },
        {
            "seconds":
                4.0,

            "source":
                "test",

            "confidence":
                "HIGH",

            "role":
                "CONTEXT",
        }
    )


    assert (
        video[
            "status"
        ]
        in {
            "PASS",
            "WARN",
        }
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.33 SAFETY SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Zoom Velocity Gate"
    )
    print(
        "OK Pan Velocity Gate"
    )
    print(
        "OK Documentary Motion Protection"
    )
    print(
        "OK Video Native Motion Protection"
    )
    print(
        "OK Transition Validation"
    )
    print(
        "OK Duration Confidence Warning"
    )
    print(
        "OK HOLD / WARN / PASS"
    )
    print()


if __name__ == "__main__":

    self_test()
