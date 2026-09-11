#!/usr/bin/env python3

from vi7_13_motion_catalog import (
    info,
    pool
)

from vi7_14_adaptive_state import (
    last_profiles
)


VERSION = "7.15"


def choose(role):

    candidates = list(
        pool(
            role
        )
    )


    if not candidates:
        return None


    recent = last_profiles(
        2
    )


    last = (
        recent[-1]
        if recent
        else None
    )


    last_info = (
        info(last)
        if last
        else {}
    )


    for candidate in candidates:

        cinfo = info(
            candidate
        )


        # Do not repeat exact profile.
        if candidate in recent:
            continue


        # Do not repeat strong energy consecutively.
        if (
            last_info.get(
                "energy"
            ) == 3
            and cinfo.get(
                "energy"
            ) == 3
        ):
            continue


        # Avoid same lateral direction twice.
        if (
            last_info
            and cinfo.get(
                "direction"
            ) in {
                "LEFT",
                "RIGHT",
            }
            and cinfo.get(
                "direction"
            )
            == last_info.get(
                "direction"
            )
        ):
            continue


        return candidate


    # Controlled fallback:
    # choose first profile different from immediate last.
    for candidate in candidates:

        if candidate != last:
            return candidate


    return candidates[0]


def self_test():

    assert choose(
        "CONTEXT"
    )

    print(
        "VI7.15 MOTION PLANNER=PASS"
    )


if __name__ == "__main__":
    self_test()
