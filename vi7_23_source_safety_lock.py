#!/usr/bin/env python3

VERSION = "7.23"


def evaluate():

    return {
        "version":
            VERSION,

        "source_recovery_mode":
            "SHADOW_ONLY",

        "automatic_source_recovery":
            False,

        "renderer_may_activate_recovery":
            False,

        "status":
            "LOCKED_SAFE",
    }


def self_test():

    r = evaluate()

    assert (
        r[
            "automatic_source_recovery"
        ]
        is False
    )

    print(
        "VI7.23 SOURCE SAFETY LOCK=PASS"
    )


if __name__ == "__main__":
    self_test()
