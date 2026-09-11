#!/usr/bin/env python3

VERSION = "6.55"


def evaluate(
    event
):

    event = dict(
        event
        or {}
    )


    branch = event.get(
        "branch"
    )


    status = event.get(
        "status"
    )


    blockers = []


    if branch == "VIDEO":

        if (
            status
            != "NATIVE_VIDEO_PRESERVE"
        ):

            blockers.append(
                "video_not_native_preserve"
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

        "native_video_preserved":
            (
                branch != "VIDEO"
                or status
                == "NATIVE_VIDEO_PRESERVE"
            ),

        "blockers":
            blockers,

        "command_mutated":
            False,
    }


def self_test():

    assert (
        evaluate(
            {
                "branch":
                    "VIDEO",

                "status":
                    "NATIVE_VIDEO_PRESERVE",
            }
        )[
            "status"
        ]
        == "PASS"
    )


    print(
        "VI6.55 NATIVE VIDEO GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
