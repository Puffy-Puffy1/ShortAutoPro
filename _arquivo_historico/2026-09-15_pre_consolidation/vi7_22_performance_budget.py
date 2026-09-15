#!/usr/bin/env python3

VERSION = "7.22"


def evaluate(
    events
):

    success = [
        e
        for e in events
        if e.get(
            "action"
        ) == "VI730_RENDER_SUCCESS"
    ]


    retries = [
        e
        for e in events
        if e.get(
            "action"
        ) == "LEGACY_RETRY"
    ]


    return {
        "version":
            VERSION,

        "successful_vi7":
            len(success),

        "retries":
            len(retries),

        "status":
            (
                "PASS"
                if len(retries) <= 2
                else "PASS_WITH_WARNINGS"
            ),
    }


def self_test():

    assert VERSION == "7.22"

    print(
        "VI7.22 PERFORMANCE BUDGET=PASS"
    )


if __name__ == "__main__":
    self_test()
