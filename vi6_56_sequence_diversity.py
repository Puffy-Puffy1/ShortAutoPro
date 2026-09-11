#!/usr/bin/env python3

VERSION = "6.56"


def audit(
    events
):

    events = sorted(
        list(
            events
            or []
        ),
        key=lambda x:
            x.get(
                "scene",
                999
            )
    )


    warnings = []

    blockers = []


    branches = [
        event.get(
            "branch"
        )
        for event in events
    ]


    # Detect excessive still/video streaks.
    longest = 0

    current = 0

    previous = None


    for branch in branches:

        if branch == previous:

            current += 1

        else:

            previous = branch

            current = 1


        longest = max(
            longest,
            current
        )


    if longest >= 6:

        warnings.append(
            "long_same_media_streak"
        )


    profiles = [

        (
            event.get(
                "mega",
                {}
            )
            .get(
                "motion",
                {}
            )
            .get(
                "profile"
            )
        )

        for event in events
    ]


    repeated_profile = 0


    for index in range(
        2,
        len(
            profiles
        )
    ):

        if (
            profiles[index]
            and profiles[index]
            == profiles[index - 1]
            == profiles[index - 2]
            and profiles[index]
            not in {
                "NATIVE"
            }
        ):

            repeated_profile += 1


    if repeated_profile >= 2:

        warnings.append(
            "repetitive_motion_profiles"
        )


    scenes = sorted(
        {
            event.get(
                "scene"
            )
            for event in events
            if isinstance(
                event.get(
                    "scene"
                ),
                int
            )
        }
    )


    if (
        len(
            events
        )
        >= 12
        and scenes
        != list(
            range(
                1,
                13
            )
        )
    ):

        blockers.append(
            "scene_sequence_not_1_to_12"
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

        "longest_media_streak":
            longest,

        "repeated_motion_profile_events":
            repeated_profile,

        "warnings":
            warnings,

        "blockers":
            blockers,
    }


def self_test():

    events = [
        {
            "scene": n,
            "branch":
                (
                    "VIDEO"
                    if n % 2
                    else "STILL"
                ),

            "mega":
                {
                    "motion":
                        {
                            "profile":
                                (
                                    "NATIVE"
                                    if n % 2
                                    else "DOCUMENTARY_DRIFT"
                                )
                        }
                },
        }

        for n in range(
            1,
            13
        )
    ]


    assert (
        audit(
            events
        )[
            "status"
        ]
        == "PASS"
    )


    print(
        "VI6.56 SEQUENCE DIVERSITY=PASS"
    )


if __name__ == "__main__":
    self_test()
