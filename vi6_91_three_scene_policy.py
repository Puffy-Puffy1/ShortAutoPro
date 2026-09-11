#!/usr/bin/env python3

VERSION = "6.91"

MAX_CANARIES = 3


# We deliberately avoid:
# scene 1  = hook
# scene 12 = CTA
#
# Zone A -> normal context
# Zone B -> later context
# Zone C -> climax area

ZONES = (
    {
        "name": "CONTEXT_A",
        "scenes": (3, 4, 5, 6),
        "profile": "HORIZONTAL_DISCOVERY",
    },

    {
        "name": "CONTEXT_B",
        "scenes": (6, 7, 8),
        "profile": "DETAIL_PUSH",
    },

    {
        "name": "CLIMAX",
        "scenes": (9, 10, 11),
        "profile": "CLIMAX_PAN",
    },
)


def policy():

    return {
        "version": VERSION,

        "max_canaries":
            MAX_CANARIES,

        "zones":
            ZONES,

        "hook_canary_allowed":
            False,

        "cta_canary_allowed":
            False,

        "video_canary_allowed":
            False,

        "full_active":
            False,
    }


def self_test():

    p = policy()

    assert p["max_canaries"] == 3
    assert p["full_active"] is False

    print(
        "VI6.91 THREE-SCENE POLICY=PASS"
    )


if __name__ == "__main__":
    self_test()
