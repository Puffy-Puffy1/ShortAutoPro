#!/usr/bin/env python3

VERSION = "7.08"


def audit(events):

    selected = [
        event
        for event in (
            events
            or []
        )
        if event.get(
            "action"
        ) == "VI7_SELECTED"
    ]


    scenes = sorted(
        {
            event.get(
                "scene"
            )
            for event in selected
            if isinstance(
                event.get(
                    "scene"
                ),
                int
            )
        }
    )


    profiles = [
        event.get(
            "profile"
        )
        for event in selected
        if event.get(
            "profile"
        )
    ]


    zones = [
        event.get(
            "zone"
        )
        for event in selected
        if event.get(
            "zone"
        )
    ]


    blockers = []
    warnings = []


    if len(scenes) > 6:

        blockers.append(
            "more_than_six_canaries"
        )


    if any(
        scene in {
            1,
            12,
        }
        for scene in scenes
    ):

        blockers.append(
            "hook_or_cta_selected"
        )


    # No more than two canaries per narrative zone.
    for zone in set(
        zones
    ):

        if zones.count(
            zone
        ) > 2:

            blockers.append(
                "zone_limit_exceeded:"
                + str(zone)
            )


    unique_profiles = len(
        set(
            profiles
        )
    )


    if (
        len(selected) >= 4
        and unique_profiles < 4
    ):

        warnings.append(
            "motion_profile_diversity_low"
        )


    # Avoid 3 adjacent VI7 scenes.
    triples = []


    for i in range(
        len(scenes) - 2
    ):

        if (
            scenes[i + 1]
            == scenes[i] + 1
            and scenes[i + 2]
            == scenes[i] + 2
        ):

            triples.append(
                scenes[i:i + 3]
            )


    if triples:

        warnings.append(
            "three_adjacent_canary_scenes"
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

        "selected_scenes":
            scenes,

        "selected_count":
            len(scenes),

        "profiles":
            profiles,

        "unique_profile_count":
            unique_profiles,

        "zones":
            zones,

        "adjacent_triples":
            triples,

        "blockers":
            blockers,

        "warnings":
            warnings,
    }


def self_test():

    sample = [
        {
            "scene": 3,
            "action": "VI7_SELECTED",
            "zone": "A",
            "profile": "P1",
        },

        {
            "scene": 5,
            "action": "VI7_SELECTED",
            "zone": "B",
            "profile": "P2",
        },

        {
            "scene": 9,
            "action": "VI7_SELECTED",
            "zone": "C",
            "profile": "P3",
        },
    ]


    assert (
        audit(sample)["status"]
        == "PASS"
    )

    print(
        "VI7.08 SEQUENCE AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
