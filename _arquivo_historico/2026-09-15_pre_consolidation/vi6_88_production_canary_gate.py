#!/usr/bin/env python3

from vi6_81_visual_approval import (
    get as approval
)


VERSION = "6.88"


def evaluate():

    a = approval()

    blockers = []


    if a.get(
        "status"
    ) != "APPROVED":

        blockers.append(
            "visual_not_approved"
        )


    if not a.get(
        "approved_for_runtime_canary"
    ):

        blockers.append(
            "runtime_canary_not_approved"
        )


    if a.get(
        "approved_for_full_active"
    ):

        blockers.append(
            "full_active_must_remain_locked"
        )


    return {

        "version":
            VERSION,

        "status":
            (
                "CANARY_ALLOWED"
                if not blockers
                else "HOLD"
            ),

        "scene":
            a.get(
                "scene"
            ),

        "profile":
            a.get(
                "profile"
            ),

        "blockers":
            blockers,

        "full_active":
            False,
    }


def self_test():

    result = evaluate()

    assert (
        result["status"]
        == "CANARY_ALLOWED"
    )

    print(
        "VI6.88 PRODUCTION CANARY GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
