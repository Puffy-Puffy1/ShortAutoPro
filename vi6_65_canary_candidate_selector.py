#!/usr/bin/env python3

from vi6_61_motion_diversity_planner import (
    plan as diversity_plan
)

from vi6_61_motion_filter_compiler import (
    compile_filter
)


VERSION = "6.65.1"


SAFE = {
    "SAFE_DIFFERENCE",
    "EXACT_MATCH",
}


def _score(event):

    scene = event.get("scene")

    duration = event.get(
        "duration_seconds"
    )

    status = event.get("status")


    try:
        duration = float(duration)
    except Exception:
        return None


    if event.get(
        "branch"
    ) != "STILL":
        return None


    if scene in {
        None,
        1,
        12,
    }:
        return None


    if status not in SAFE:
        return None


    if event.get("blockers"):
        return None


    if not (
        2.0
        <= duration
        <= 6.5
    ):
        return None


    role = (
        event.get("mega", {})
        .get("contract", {})
        .get("role")
    )


    score = 100.0


    score -= abs(
        duration - 3.5
    ) * 8.0


    if role == "CONTEXT":
        score += 15


    elif role == "CLIMAX":
        score -= 8


    if status == "SAFE_DIFFERENCE":
        score += 12


    if scene in {
        2,
        11,
    }:
        score -= 10


    interval = (
        event.get("mega", {})
        .get(
            "inter_event_wall_seconds"
        )
    )


    try:
        interval = float(interval)
    except Exception:
        interval = None


    if (
        interval is not None
        and interval > 7
    ):
        score -= 8


    return round(
        score,
        2
    )


def select(events):

    events = list(
        events
        or []
    )


    diversity = diversity_plan(
        events
    )


    profile_by_scene = {

        item.get("scene"):
            item.get(
                "recommended_profile"
            )

        for item in (
            diversity.get("plan")
            or []
        )
    }


    candidates = []


    for event in events:

        score = _score(
            event
        )


        if score is None:
            continue


        scene = event.get(
            "scene"
        )


        duration = event.get(
            "duration_seconds"
        )


        profile = profile_by_scene.get(
            scene
        )


        compiled = compile_filter(
            profile,
            duration,
            30
        )


        if compiled.get(
            "status"
        ) != "COMPILED":
            continue


        candidate = {
            "scene":
                scene,

            "score":
                score,

            "duration_seconds":
                duration,

            "status":
                event.get("status"),

            "role":
                (
                    event.get("mega", {})
                    .get("contract", {})
                    .get("role")
                ),

            "previous_motion_profile":
                (
                    event.get("mega", {})
                    .get("motion", {})
                    .get("profile")
                ),

            "recommended_motion_profile":
                profile,

            "legacy_vf":
                event.get(
                    "legacy_vf"
                ),

            # Important:
            # use actual compiled cinematic filter,
            # not VI6.50 structural dry-plan vf.
            "proposed_vi6_vf":
                compiled.get("vf"),

            "previous_dry_plan_vf":
                event.get(
                    "proposed_vi6_vf"
                ),

            "motion_compile":
                compiled,

            "command_fingerprint":
                event.get(
                    "command_fingerprint"
                ),
        }


        candidates.append(
            candidate
        )


    candidates.sort(
        key=lambda item: (
            item["score"],
            -item["scene"],
        ),
        reverse=True
    )


    winner = (
        candidates[0]
        if candidates
        else None
    )


    return {
        "version": VERSION,

        "status":
            (
                "SELECTED"
                if winner
                else "HOLD"
            ),

        "winner":
            winner,

        "candidates":
            candidates,

        "motion_diversity_status":
            diversity.get(
                "status"
            ),

        "active_authorized":
            False,
    }


def self_test():

    events = []


    for scene in range(
        1,
        13
    ):

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


        events.append(
            {
                "scene":
                    scene,

                "branch":
                    "STILL",

                "duration_seconds":
                    3.4,

                "status":
                    "SAFE_DIFFERENCE",

                "blockers":
                    [],

                "legacy_vf":
                    (
                        "scale=1200:2133,"
                        "zoompan="
                        "z='1.01':"
                        "x='0':y='0':"
                        "d=102:"
                        "s=1080x1920:"
                        "fps=30,"
                        "setsar=1,"
                        "format=yuv420p"
                    ),

                "proposed_vi6_vf":
                    (
                        "scale=1080:1920,"
                        "crop=1080:1920,"
                        "fps=30"
                    ),

                "mega": {
                    "contract": {
                        "role":
                            role
                    },

                    "motion": {
                        "profile":
                            "DOCUMENTARY_DRIFT"
                    },

                    "inter_event_wall_seconds":
                        4,
                },
            }
        )


    result = select(
        events
    )


    assert (
        result["status"]
        == "SELECTED"
    )


    winner = result[
        "winner"
    ]


    assert (
        "zoompan="
        in winner[
            "proposed_vi6_vf"
        ]
    )


    assert (
        winner[
            "previous_dry_plan_vf"
        ]
        != winner[
            "proposed_vi6_vf"
        ]
    )


    print(
        "VI6.65.1 CANARY SELECTOR=PASS"
    )


if __name__ == "__main__":
    self_test()
