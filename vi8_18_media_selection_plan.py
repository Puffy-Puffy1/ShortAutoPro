#!/usr/bin/env python3

from vi7_31_visual_ontology import (
    classify
)

from vi8_15_scene_media_selector import (
    select
)

from vi8_16_global_media_continuity import (
    evaluate as continuity
)

from vi8_17_shot_correction_engine import (
    evaluate as shot_correction
)

VERSION = "8.18"

def build(scenes):
    selections = []
    previous_winners = []

    for scene in scenes:
        category = classify(
            scene
        )

        result = select(
            scene,
            category,
            previous_winners
        )

        selections.append(
            result
        )

        winner_candidate = (
            result.get(
                "winner"
            )
            or {}
        ).get(
            "candidate"
        )

        if winner_candidate:
            previous_winners.append(
                winner_candidate
            )

    continuity_result = continuity(
        selections
    )

    shot_changes = [
        shot_correction(
            selection
        )
        for selection in selections
    ]

    return {
        "version":
            VERSION,

        "selections":
            selections,

        "continuity":
            continuity_result,

        "shot_corrections":
            shot_changes,
    }

def self_test():
    sample = [
        {
            "scene": 1,
            "segment": "house",
            "query":
                "house exterior",
            "shot_type":
                "medium",
        }
    ]

    result = build(
        sample
    )

    assert len(
        result["selections"]
    ) == 1

    print(
        "VI8.18 MEDIA SELECTION PLAN=PASS"
    )

if __name__ == "__main__":
    self_test()
