#!/usr/bin/env python3

VERSION = "6.52"


def evaluate(
    event
):

    event = dict(
        event
        or {}
    )


    scene = event.get(
        "scene"
    )


    blockers = []

    warnings = []


    if not isinstance(
        scene,
        int
    ):

        blockers.append(
            "scene_not_integer"
        )


    elif not (
        1 <= scene <= 12
    ):

        blockers.append(
            "scene_outside_1_12"
        )


    branch = event.get(
        "branch"
    )


    if branch not in {
        "STILL",
        "VIDEO",
    }:

        blockers.append(
            "unknown_media_branch"
        )


    duration = event.get(
        "duration_seconds"
    )


    try:

        duration = float(
            duration
        )

    except Exception:

        duration = None


    if (
        duration is None
        or duration <= 0
    ):

        blockers.append(
            "duration_invalid"
        )


    elif duration < .75:

        warnings.append(
            "very_short_scene"
        )


    return {

        "version":
            VERSION,

        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "scene":
            scene,

        "branch":
            branch,

        "duration":
            duration,

        "blockers":
            blockers,

        "warnings":
            warnings,
    }


def self_test():

    assert (
        evaluate(
            {
                "scene": 12,
                "branch": "VIDEO",
                "duration_seconds": 3.0,
            }
        )[
            "status"
        ]
        == "PASS"
    )


    assert (
        evaluate(
            {
                "scene": 0,
                "branch": "STILL",
                "duration_seconds": 3.0,
            }
        )[
            "status"
        ]
        == "HOLD"
    )


    print(
        "VI6.52 SCENE IDENTITY=PASS"
    )


if __name__ == "__main__":
    self_test()
