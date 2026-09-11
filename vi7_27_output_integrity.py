#!/usr/bin/env python3

VERSION = "7.27"


def evaluate(
    successful_events
):

    blockers = []


    for event in successful_events:

        validation = (
            event.get(
                "validation"
            )
            or {}
        )


        if validation.get(
            "status"
        ) != "PASS":

            blockers.append(
                "successful_event_without_pass_validation"
            )


        if validation.get(
            "blockers"
        ):

            blockers.append(
                "validation_contains_blockers"
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
            sorted(
                set(
                    blockers
                )
            ),
    }


def self_test():

    assert (
        evaluate(
            []
        )["status"]
        == "PASS"
    )

    print(
        "VI7.27 OUTPUT INTEGRITY=PASS"
    )


if __name__ == "__main__":
    self_test()
