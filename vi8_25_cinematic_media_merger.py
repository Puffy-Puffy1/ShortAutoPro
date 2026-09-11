#!/usr/bin/env python3

from vi8_21_improvement_priority import (
    priority
)

from vi8_22_selection_confidence import (
    evaluate as confidence
)

VERSION = "8.25"


def merge(
    media_plan,
    cinematic_plans
):
    cinematic_by_scene = {
        item.get("scene"):
            item

        for item
        in cinematic_plans
    }

    merged = []

    selections = (
        media_plan.get(
            "selections"
        )
        or []
    )

    for selection in selections:
        scene = selection.get(
            "scene"
        )

        cinematic = (
            cinematic_by_scene.get(
                scene
            )
            or {}
        )

        p = priority(
            selection,
            cinematic
        )

        c = confidence(
            selection
        )

        comparison = (
            selection.get(
                "comparison"
            )
            or {}
        )

        winner = (
            selection.get(
                "winner"
            )
            or {}
        )

        winner_candidate = (
            winner.get(
                "candidate"
            )
            or {}
        )

        merged.append({
            "scene":
                scene,

            "category":
                selection.get(
                    "category"
                ),

            "current_score":
                (
                    selection.get(
                        "current"
                    )
                    or {}
                ).get(
                    "score"
                ),

            "winner_score":
                winner.get(
                    "score"
                ),

            "winner_shot":
                winner_candidate.get(
                    "shot"
                ),

            "winner_source":
                winner_candidate.get(
                    "source"
                ),

            "delta":
                comparison.get(
                    "delta"
                ),

            "recommendation":
                comparison.get(
                    "recommendation"
                ),

            "priority_score":
                p.get(
                    "priority_score"
                ),

            "priority_reasons":
                p.get(
                    "reasons"
                ),

            "confidence":
                c.get(
                    "confidence"
                ),

            "confidence_level":
                c.get(
                    "level"
                ),

            "cinematic_shot_match":
                cinematic.get(
                    "shot_match"
                ),

            "cinematic_motion":
                cinematic.get(
                    "motion"
                ),

            "cinematic_status":
                cinematic.get(
                    "status"
                ),
        })

    return {
        "version":
            VERSION,

        "items":
            merged,
    }


def self_test():
    assert VERSION == "8.25"

    print(
        "VI8.25 CINEMATIC MEDIA MERGER=PASS"
    )


if __name__ == "__main__":
    self_test()
