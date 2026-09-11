#!/usr/bin/env python3

VERSION = "6.84"


FAILURES = {
    "compile_failure",
    "filter_validation_failure",
    "ffmpeg_failure",
    "output_missing",
    "duration_invalid",
    "resolution_invalid",
    "unexpected_exception",
}


def decide(
    failure=None
):

    if failure is None:

        return {
            "version":
                VERSION,

            "fallback":
                False,

            "action":
                "KEEP_VI6_CANARY",
        }


    return {
        "version":
            VERSION,

        "fallback":
            True,

        "action":
            "USE_LEGACY_FOR_SAME_SCENE",

        "reason":
            failure,
    }


def self_test():

    assert (
        decide(
            "ffmpeg_failure"
        )["fallback"]
        is True
    )

    print(
        "VI6.84 CANARY FALLBACK=PASS"
    )


if __name__ == "__main__":
    self_test()
