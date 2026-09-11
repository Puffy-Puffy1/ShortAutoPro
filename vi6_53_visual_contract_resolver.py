#!/usr/bin/env python3

VERSION = "6.53"


def resolve(
    event,
    identity
):

    event = dict(
        event
        or {}
    )


    identity = dict(
        identity
        or {}
    )


    branch = identity.get(
        "branch"
    )


    scene = identity.get(
        "scene"
    )


    duration = identity.get(
        "duration"
    )


    renderer_mode = event.get(
        "renderer_mode"
    )


    role = (
        "HOOK"
        if scene == 1

        else (
            "CTA"
            if scene == 12

            else (
                "CLIMAX"
                if scene in {
                    9,
                    10,
                    11,
                }

                else "CONTEXT"
            )
        )
    )


    desired_motion = (

        "NATIVE"
        if branch == "VIDEO"

        else (
            "ENERGETIC"
            if role == "HOOK"

            else (
                "CALM"
                if role == "CTA"

                else "CINEMATIC"
            )
        )
    )


    blockers = []


    if (
        identity.get(
            "status"
        )
        != "PASS"
    ):

        blockers.append(
            "identity_hold"
        )


    if (
        branch == "VIDEO"
        and renderer_mode
        not in {
            None,
            "NATIVE_VIDEO_PRESERVE",
        }
    ):

        blockers.append(
            "video_motion_not_native"
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

        "scene":
            scene,

        "role":
            role,

        "branch":
            branch,

        "duration_seconds":
            duration,

        "desired_motion":
            desired_motion,

        "renderer_mode":
            renderer_mode,

        "blockers":
            blockers,
    }


def self_test():

    result = resolve(
        {
            "renderer_mode":
                "NATIVE_VIDEO_PRESERVE"
        },
        {
            "status":
                "PASS",

            "scene":
                12,

            "branch":
                "VIDEO",

            "duration":
                3.2,
        }
    )


    assert (
        result[
            "role"
        ]
        == "CTA"
    )


    assert (
        result[
            "status"
        ]
        == "PASS"
    )


    print(
        "VI6.53 VISUAL CONTRACT=PASS"
    )


if __name__ == "__main__":
    self_test()
