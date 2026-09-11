#!/usr/bin/env python3

from vi6_61_motion_diversity_planner import (
    plan
)

from vi6_63_truth_state_hardener import (
    normalize
)

from vi6_65_canary_candidate_selector import (
    select
)

from vi6_66_canary_filter_preview import (
    preview
)

from vi6_67_scene_rollback_contract import (
    build
)


events = []


for scene in range(1, 13):

    branch = (
        "VIDEO"
        if scene == 2
        else "STILL"
    )


    role = (
        "HOOK"
        if scene == 1
        else (
            "CTA"
            if scene == 12
            else (
                "CLIMAX"
                if scene in {9, 10, 11}
                else "CONTEXT"
            )
        )
    )


    events.append(
        {
            "scene": scene,
            "branch": branch,
            "duration_seconds":
                (
                    3.5
                    if scene == 6
                    else 3.0
                ),
            "status":
                (
                    "NATIVE_VIDEO_PRESERVE"
                    if branch == "VIDEO"
                    else "SAFE_DIFFERENCE"
                ),
            "blockers": [],
            "legacy_vf":
                (
                    None
                    if branch == "VIDEO"
                    else (
                        "scale=1200:2133,"
                        "zoompan=z='1.01',"
                        "format=yuv420p"
                    )
                ),
            "proposed_vi6_vf":
                (
                    None
                    if branch == "VIDEO"
                    else (
                        "scale=1080:1920,"
                        "zoompan=z='1.03',"
                        "format=yuv420p"
                    )
                ),
            "mega": {
                "contract": {
                    "role": role
                },
                "motion": {
                    "profile":
                        (
                            "NATIVE"
                            if branch == "VIDEO"
                            else "DOCUMENTARY_DRIFT"
                        )
                },
                "inter_event_wall_seconds":
                    4.0,
            },
        }
    )


motion = plan(events)

assert motion["triple_repeats"] == 0


assert normalize(None) == "UNKNOWN"
assert normalize("maybe") == "UNKNOWN"


candidate = select(events)

assert candidate["status"] == "SELECTED"

assert candidate["winner"]["scene"] not in {
    1,
    12,
}


filter_result = preview(
    candidate["winner"]
)

assert (
    filter_result["status"]
    == "PREVIEW_READY"
)

assert (
    filter_result["filter_applied"]
    is False
)


rollback = build(
    candidate["winner"]["scene"]
)

assert (
    rollback[
        "other_scenes_affected"
    ]
    is False
)


print()
print(
    "======================================================"
)
print(
    " VI6.61-6.70 MEGA INTEGRATION: PASS"
)
print(
    "======================================================"
)
print(
    "MOTION DIVERSITY=PASS"
)
print(
    "UNKNOWN TRUTH SAFETY=PASS"
)
print(
    "CANARY SELECTION=PASS"
)
print(
    "FILTER PREVIEW=PASS"
)
print(
    "PER-SCENE ROLLBACK=PASS"
)
print(
    "FILTER APPLIED=NO"
)
print(
    "ACTIVE=LOCKED"
)
