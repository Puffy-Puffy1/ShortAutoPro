#!/usr/bin/env python3

from vi8_42_scene_lookup import (
    by_number
)

from vi8_43_real_category_resolver import (
    resolve
)

from vi8_45_real_candidate_enricher import (
    enrich
)

from vi8_46_real_vs_virtual_ranker import (
    rank
)

from vi8_47_real_media_gap import (
    evaluate as gap_eval
)

VERSION = "8.48"


def build(
    scenes,
    grouped
):
    lookup = by_number(
        scenes
    )

    scene_groups = (
        grouped.get("scenes")
        or {}
    )

    plans = []

    previous_winners = []

    for number in range(
        1,
        13
    ):
        scene = (
            lookup.get(number)
            or {}
        )

        category = resolve(
            scene
        )

        raw_real = (
            scene_groups.get(
                number
            )
            or []
        )

        real_candidates = [
            enrich(
                item,
                scene,
                category
            )
            for item
            in raw_real
        ]

        ranking = rank(
            scene,
            category,
            real_candidates,
            previous_winners
        )

        gap = gap_eval(
            ranking
        )

        winner = ranking.get(
            "winner"
        )

        if winner:
            candidate = (
                winner.get(
                    "candidate"
                )
                or {}
            )

            previous_winners.append(
                candidate
            )

        plans.append({
            "scene":
                number,

            "category":
                category,

            "query":
                scene.get(
                    "query"
                ),

            "real_candidate_count":
                len(
                    real_candidates
                ),

            "ranking":
                ranking,

            "gap":
                gap,
        })

    return {
        "version":
            VERSION,

        "scenes":
            plans,
    }


def self_test():
    assert VERSION == "8.48"

    print(
        "VI8.48 REAL SCENE RANKING PLAN=PASS"
    )


if __name__ == "__main__":
    self_test()
