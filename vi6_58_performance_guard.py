#!/usr/bin/env python3

VERSION = "6.58"


def estimate(
    event
):

    branch = event.get(
        "branch"
    )


    duration = event.get(
        "duration_seconds"
    )


    try:

        duration = float(
            duration
        )

    except Exception:

        duration = 0.0


    vf = event.get(
        "proposed_vi6_vf"
    )


    score = 1.0


    if branch == "STILL":

        score += 1.0


    if (
        isinstance(
            vf,
            str
        )
        and "zoompan="
        in vf
    ):

        score += .75


    if duration >= 5:

        score += .5


    return round(
        score,
        2
    )


def audit(
    events
):

    scores = [
        estimate(
            event
        )
        for event in events
    ]


    total = round(
        sum(
            scores
        ),
        2
    )


    warnings = []


    if total > 30:

        warnings.append(
            "high_render_complexity"
        )


    return {

        "version":
            VERSION,

        "status":
            (
                "PASS_WITH_WARNINGS"
                if warnings
                else "PASS"
            ),

        "estimated_complexity":
            total,

        "max_scene_complexity":
            (
                max(
                    scores
                )
                if scores
                else 0
            ),

        "warnings":
            warnings,

        "renderer_changed":
            False,
    }


def self_test():

    assert (
        estimate(
            {
                "branch":
                    "VIDEO",

                "duration_seconds":
                    3,
            }
        )
        < estimate(
            {
                "branch":
                    "STILL",

                "duration_seconds":
                    5,

                "proposed_vi6_vf":
                    "zoompan=z='1.02'",
            }
        )
    )


    print(
        "VI6.58 PERFORMANCE GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
