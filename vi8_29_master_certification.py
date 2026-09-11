#!/usr/bin/env python3

VERSION = "8.29"


def evaluate(
    readiness,
    safety,
    cinematic_score
):
    blockers = (
        readiness.get(
            "blockers"
        )
        or []
    )

    warnings = (
        readiness.get(
            "warnings"
        )
        or []
    )

    safety_ok = (
        safety.get(
            "status"
        )
        == "LOCKED_SAFE"
    )

    if not safety_ok:
        blockers = list(
            blockers
        ) + [
            "activation_safety_not_locked"
        ]

    blockers = sorted(
        set(blockers)
    )

    if blockers:
        status = "HOLD"

    elif (
        readiness.get(
            "status"
        )
        == "READY_FOR_MEDIA_INTEGRATION_PREVIEW"
        and float(
            cinematic_score
            or 0
        ) >= 85
    ):
        status = (
            "CINEMATIC_MEDIA_SHADOW_CERTIFIED"
        )

    else:
        status = (
            "CINEMATIC_MEDIA_SHADOW_SAFE"
        )

    return {
        "version":
            VERSION,

        "status":
            status,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "shadow_certified":
            (
                status
                == "CINEMATIC_MEDIA_SHADOW_CERTIFIED"
            ),

        "real_media_activation":
            False,

        "full_active_authorized":
            False,
    }


def self_test():
    result = evaluate(
        {
            "status":
                "READY_FOR_MEDIA_INTEGRATION_PREVIEW",
            "blockers": [],
            "warnings": [],
        },
        {
            "status":
                "LOCKED_SAFE"
        },
        94
    )

    assert (
        result[
            "shadow_certified"
        ]
        is True
    )

    print(
        "VI8.29 MASTER CERTIFICATION=PASS"
    )


if __name__ == "__main__":
    self_test()
