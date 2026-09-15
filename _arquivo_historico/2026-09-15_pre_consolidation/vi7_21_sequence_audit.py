#!/usr/bin/env python3

from vi7_13_motion_catalog import (
    info
)


VERSION = "7.21"


def audit(events):

    selected = [
        e
        for e in events
        if e.get(
            "action"
        ) == "VI730_SELECTED"
    ]


    scenes = [
        e.get("scene")
        for e in selected
        if isinstance(
            e.get("scene"),
            int
        )
    ]


    profiles = [
        e.get("profile")
        for e in selected
        if e.get("profile")
    ]


    roles = [
        e.get("role")
        for e in selected
        if e.get("role")
    ]


    blockers = []
    warnings = []


    if len(
        set(scenes)
    ) != len(scenes):

        blockers.append(
            "duplicate_scene_selection"
        )


    if len(scenes) > 9:

        blockers.append(
            "adaptive_limit_exceeded"
        )


    if any(
        x in {
            1,
            12,
        }
        for x in scenes
    ):

        blockers.append(
            "protected_scene_selected"
        )


    # exact profile repetition
    for a, b in zip(
        profiles,
        profiles[1:]
    ):

        if a == b:

            blockers.append(
                "consecutive_identical_profile"
            )


    # strong motion repetition
    for a, b in zip(
        profiles,
        profiles[1:]
    ):

        if (
            info(a).get(
                "energy"
            ) == 3
            and info(b).get(
                "energy"
            ) == 3
        ):

            warnings.append(
                "consecutive_strong_motion"
            )


    # detect 3 adjacent selected scenes
    triples = []

    ordered = sorted(
        scenes
    )

    for i in range(
        len(ordered) - 2
    ):

        if (
            ordered[i + 1]
            == ordered[i] + 1
            and ordered[i + 2]
            == ordered[i] + 2
        ):

            triples.append(
                ordered[
                    i:i + 3
                ]
            )


    if triples:

        blockers.append(
            "three_adjacent_vi7_scenes"
        )


    return {
        "version":
            VERSION,

        "status":
            (
                "HOLD"
                if blockers
                else (
                    "PASS_WITH_WARNINGS"
                    if warnings
                    else "PASS"
                )
            ),

        "scenes":
            ordered,

        "profiles":
            profiles,

        "roles":
            roles,

        "unique_profiles":
            len(
                set(
                    profiles
                )
            ),

        "adjacent_triples":
            triples,

        "blockers":
            sorted(
                set(
                    blockers
                )
            ),

        "warnings":
            sorted(
                set(
                    warnings
                )
            ),
    }


def self_test():

    assert (
        audit(
            []
        )["status"]
        == "PASS"
    )

    print(
        "VI7.21 SEQUENCE AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
