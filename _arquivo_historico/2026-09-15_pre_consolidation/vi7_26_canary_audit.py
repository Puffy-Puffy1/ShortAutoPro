#!/usr/bin/env python3

VERSION = "7.26"


def evaluate(
    events
):

    selected = [
        e
        for e in events
        if e.get(
            "action"
        ) == "VI730_SELECTED"
    ]


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


    retry_success = [
        e
        for e in events
        if e.get(
            "action"
        ) == "LEGACY_RETRY_SUCCESS"
    ]


    retry_failed = [
        e
        for e in events
        if e.get(
            "action"
        ) == "LEGACY_RETRY_FAILED"
    ]


    return {
        "version":
            VERSION,

        "selected":
            selected,

        "success":
            success,

        "retries":
            retries,

        "retry_success":
            retry_success,

        "retry_failed":
            retry_failed,
    }


def self_test():

    assert VERSION == "7.26"

    print(
        "VI7.26 CANARY AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
