#!/usr/bin/env python3

VERSION = "6.61"


CONTEXT_PROFILES = (
    "DOCUMENTARY_DRIFT",
    "SLOW_PUSH",
    "HORIZONTAL_DISCOVERY",
    "REVERSE_DRIFT",
    "DETAIL_PUSH",
)


CLIMAX_PROFILES = (
    "CLIMAX_PUSH",
    "CLIMAX_PAN",
    "CLIMAX_LOCK",
)


def _role(event):

    return (
        event.get("mega", {})
        .get("contract", {})
        .get("role")
    )


def _legacy_profile(event):

    return (
        event.get("mega", {})
        .get("motion", {})
        .get("profile")
    )


def plan(events):

    ordered = sorted(
        list(events or []),
        key=lambda x: x.get("scene", 999)
    )


    output = []

    context_index = 0
    climax_index = 0


    for event in ordered:

        scene = event.get("scene")
        branch = event.get("branch")
        role = _role(event)
        old = _legacy_profile(event)


        if branch == "VIDEO":

            profile = "NATIVE"


        elif role == "HOOK":

            profile = "HOOK_PUSH"


        elif role == "CTA":

            profile = "CTA_SETTLE"


        elif role == "CLIMAX":

            profile = CLIMAX_PROFILES[
                climax_index
                % len(CLIMAX_PROFILES)
            ]

            climax_index += 1


        else:

            profile = CONTEXT_PROFILES[
                context_index
                % len(CONTEXT_PROFILES)
            ]

            context_index += 1


        output.append(
            {
                "scene": scene,
                "branch": branch,
                "role": role,
                "previous_profile": old,
                "recommended_profile": profile,
                "changed":
                    (
                        old is not None
                        and old != profile
                    ),
                "applied": False,
            }
        )


    repeats = 0


    profiles = [
        item["recommended_profile"]
        for item in output
    ]


    for i in range(2, len(profiles)):

        if (
            profiles[i]
            == profiles[i - 1]
            == profiles[i - 2]
            and profiles[i] != "NATIVE"
        ):

            repeats += 1


    return {
        "version": VERSION,
        "status":
            (
                "PASS"
                if repeats == 0
                else "PASS_WITH_WARNINGS"
            ),
        "triple_repeats": repeats,
        "plan": output,
        "applied": False,
    }


def self_test():

    events = []

    for n in range(1, 13):

        events.append(
            {
                "scene": n,
                "branch":
                    (
                        "VIDEO"
                        if n == 2
                        else "STILL"
                    ),
                "mega": {
                    "contract": {
                        "role":
                            (
                                "HOOK"
                                if n == 1
                                else (
                                    "CTA"
                                    if n == 12
                                    else (
                                        "CLIMAX"
                                        if n >= 9
                                        else "CONTEXT"
                                    )
                                )
                            )
                    },
                    "motion": {
                        "profile":
                            "DOCUMENTARY_DRIFT"
                    }
                }
            }
        )


    result = plan(events)

    assert result["triple_repeats"] == 0

    print("VI6.61 MOTION DIVERSITY=PASS")


if __name__ == "__main__":
    self_test()
