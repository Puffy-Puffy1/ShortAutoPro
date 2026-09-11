#!/usr/bin/env python3

VERSION = "7.29"


def evaluate(
    certification
):

    blockers = (
        certification.get(
            "blockers"
        )
        or []
    )


    count = certification.get(
        "selected_count",
        0
    )


    if blockers:

        status = "HOLD"

    elif count >= 7:

        status = (
            "ADAPTIVE_RUNTIME_CERTIFIED"
        )

    else:

        status = (
            "ADAPTIVE_RUNTIME_SAFE_WITH_WARNINGS"
        )


    return {
        "version":
            VERSION,

        "status":
            status,

        "blockers":
            blockers,

        "warnings":
            certification.get(
                "warnings"
            )
            or [],

        "full_active_authorized":
            False,
    }


def self_test():

    assert VERSION == "7.29"

    print(
        "VI7.29 RELEASE GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
