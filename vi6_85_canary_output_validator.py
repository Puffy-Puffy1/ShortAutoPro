#!/usr/bin/env python3

VERSION = "6.85"


def validate_plan(
    vf,
    duration
):

    blockers = []


    if not isinstance(
        vf,
        str
    ):

        blockers.append(
            "filter_missing"
        )


    else:

        required = (
            "scale=",
            "crop=",
            "zoompan=",
            "setsar=1",
            "format=yuv420p",
        )


        for token in required:

            if token not in vf:

                blockers.append(
                    "missing_" + token
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
        or duration > 8
    ):

        blockers.append(
            "duration_invalid"
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

        "blockers":
            blockers,
    }


def self_test():

    vf = (
        "scale=1200:2133,"
        "crop=1200:2133,"
        "zoompan=z='1.01':"
        "d=90:s=1080x1920:fps=30,"
        "setsar=1,"
        "format=yuv420p"
    )


    assert (
        validate_plan(
            vf,
            3
        )["status"]
        == "PASS"
    )


    print(
        "VI6.85 OUTPUT VALIDATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
