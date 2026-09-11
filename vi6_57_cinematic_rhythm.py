#!/usr/bin/env python3

VERSION = "6.57"


def scene_target(
    scene
):

    if scene == 1:
        return "FAST_HOOK"

    if scene in {
        2,
        3,
        4,
    }:
        return "ACCELERATE"

    if scene in {
        5,
        6,
        7,
        8,
    }:
        return "DOCUMENTARY_FLOW"

    if scene in {
        9,
        10,
        11,
    }:
        return "CLIMAX"

    if scene == 12:
        return "CTA_SETTLE"

    return "UNKNOWN"


def audit(
    events
):

    warnings = []

    blockers = []


    for event in events:

        scene = event.get(
            "scene"
        )


        duration = event.get(
            "duration_seconds"
        )


        try:

            duration = float(
                duration
            )

        except Exception:

            blockers.append(
                "scene_duration_invalid"
            )

            continue


        target = scene_target(
            scene
        )


        if (
            target == "FAST_HOOK"
            and duration > 6.5
        ):

            warnings.append(
                "hook_may_be_slow"
            )


        if (
            target == "CTA_SETTLE"
            and duration < 1.0
        ):

            warnings.append(
                "cta_too_short"
            )


    return {

        "version":
            VERSION,

        "status":
            (
                "HOLD"
                if blockers
                else (
                    "PASS_WITH_WARNINGS"
                    if warnings
                    else "PASS"
                )
            ),

        "warnings":
            sorted(
                set(
                    warnings
                )
            ),

        "blockers":
            sorted(
                set(
                    blockers
                )
            ),
    }


def self_test():

    assert (
        scene_target(
            1
        )
        == "FAST_HOOK"
    )


    assert (
        scene_target(
            12
        )
        == "CTA_SETTLE"
    )


    print(
        "VI6.57 CINEMATIC RHYTHM=PASS"
    )


if __name__ == "__main__":
    self_test()
