#!/usr/bin/env python3

VERSION = "6.59"


def decide(
    event
):

    event = dict(
        event
        or {}
    )


    blockers = (
        event.get(
            "blockers"
        )
        or []
    )


    status = event.get(
        "status"
    )


    if (
        status == "HOLD"
        or blockers
    ):

        action = (
            "FALLBACK_SINGLE_SCENE_TO_LEGACY"
        )


    else:

        action = (
            "KEEP_CURRENT_RENDER_PATH"
        )


    return {

        "version":
            VERSION,

        "status":
            "PASS",

        "recommended_action":
            action,

        # Shadow only.
        "action_executed":
            False,

        "renderer_changed":
            False,
    }


def self_test():

    assert (
        decide(
            {
                "status":
                    "HOLD"
            }
        )[
            "recommended_action"
        ]
        == "FALLBACK_SINGLE_SCENE_TO_LEGACY"
    )


    print(
        "VI6.59 SELF HEALING POLICY=PASS"
    )


if __name__ == "__main__":
    self_test()
