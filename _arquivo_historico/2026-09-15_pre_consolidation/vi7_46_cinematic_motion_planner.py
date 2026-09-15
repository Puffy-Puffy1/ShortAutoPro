#!/usr/bin/env python3

from vi7_37_motion_safety import profiles

VERSION = "7.46"

ENERGY = {
    "MICRO_HOLD": 0,
    "FACE_SAFE_PUSH": 1,
    "SLOW_PUSH": 1,
    "DOCUMENT_SCAN": 1,
    "DETAIL_PUSH": 2,
    "MICRO_DISCOVERY": 2,
    "HORIZONTAL_DISCOVERY": 2,
    "ARCHITECTURE_DRIFT": 2,
    "REVERSE_DRIFT": 2,
}

def choose(category, narrative_energy, previous_profile=None):
    candidates = list(profiles(category))

    if not candidates:
        return None

    target = min(
        max(int(narrative_energy), 0),
        2
    )

    ranked = sorted(
        candidates,
        key=lambda profile: abs(
            ENERGY.get(profile, 1)
            - target
        )
    )

    for candidate in ranked:
        if (
            previous_profile
            and candidate == previous_profile
        ):
            continue

        return candidate

    return ranked[0]

def self_test():
    result = choose(
        "FACE",
        2
    )

    assert result in {
        "FACE_SAFE_PUSH",
        "SLOW_PUSH",
        "MICRO_HOLD",
    }

    assert (
        choose(
            "LOCATION",
            2
        )
        is not None
    )

    print(
        "VI7.46 CINEMATIC MOTION PLANNER=PASS"
    )

if __name__ == "__main__":
    self_test()
