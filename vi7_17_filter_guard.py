#!/usr/bin/env python3

VERSION = "7.17"


REQUIRED = (
    "scale=",
    "crop=",
    "zoompan=",
    "setsar=1",
    "format=yuv420p",
)


def validate(
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

        for token in REQUIRED:

            if token not in vf:

                blockers.append(
                    "missing:"
                    + token
                )


    try:
        duration = float(
            duration
        )

    except Exception:
        duration = 0


    if (
        duration <= 0
        or duration > 10
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

    assert (
        validate(
            "",
            3
        )["status"]
        == "HOLD"
    )

    print(
        "VI7.17 FILTER GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
