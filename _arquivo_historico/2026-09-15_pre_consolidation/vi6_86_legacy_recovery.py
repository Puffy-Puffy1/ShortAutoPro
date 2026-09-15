#!/usr/bin/env python3

VERSION = "6.86"


def recover(
    original_command,
    reason
):

    return {

        "version":
            VERSION,

        "status":
            "RECOVERED_TO_LEGACY",

        "reason":
            reason,

        "command":
            original_command,

        "same_object":
            True,

        "global_abort":
            False,
    }


def self_test():

    command = [
        "ffmpeg"
    ]


    result = recover(
        command,
        "test"
    )


    assert (
        result["command"]
        is command
    )


    print(
        "VI6.86 LEGACY RECOVERY=PASS"
    )


if __name__ == "__main__":
    self_test()
