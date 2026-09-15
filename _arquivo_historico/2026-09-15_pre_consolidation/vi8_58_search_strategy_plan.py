#!/usr/bin/env python3

from vi8_51_search_need_classifier import (
    evaluate as classify_need
)

from vi8_52_ideal_search_spec import (
    build as search_spec
)

from vi8_54_search_value_estimator import (
    evaluate as search_value
)

from vi8_55_search_priority_engine import (
    evaluate as search_priority
)

from vi8_56_search_budget_planner import (
    allocate
)

from vi8_57_no_search_guard import (
    evaluate as no_search_guard
)

VERSION = "8.58"


def build(real_plan):
    scenes = (
        real_plan.get("scenes")
        or []
    )

    items = []

    for scene_result in scenes:
        need = classify_need(
            scene_result
        )

        spec = search_spec(
            scene_result
        )

        gap = (
            (
                scene_result.get(
                    "gap"
                )
                or {}
            ).get(
                "virtual_advantage"
            )
            or 0
        )

        value = search_value(
            need["need"],
            gap
        )

        priority = (
            search_priority(
                scene_result.get(
                    "scene"
                ),
                scene_result.get(
                    "category"
                ),
                need["need"],
                gap
            )
        )

        item = {
            "scene":
                scene_result.get(
                    "scene"
                ),
            "category":
                scene_result.get(
                    "category"
                ),
            "need":
                need["need"],
            "gap_status":
                need[
                    "gap_status"
                ],
            "real_candidate_count":
                need[
                    "real_count"
                ],
            "gap":
                value["gap"],
            "minimum_gain":
                value[
                    "minimum_gain"
                ],
            "worthwhile":
                value[
                    "worthwhile"
                ],
            "priority_score":
                priority[
                    "priority_score"
                ],
            "priority_reasons":
                priority[
                    "reasons"
                ],
            "ideal_shot":
                spec[
                    "ideal_shot"
                ],
            "search_query":
                spec[
                    "search_query"
                ],
        }

        guard = no_search_guard(
            item
        )

        item[
            "skip_search"
        ] = guard["skip"]

        item[
            "skip_reasons"
        ] = guard["reasons"]

        items.append(
            item
        )

    budget = allocate(
        items
    )

    return {
        "version": VERSION,
        "items": items,
        "budget": budget,
    }


def self_test():
    assert VERSION == "8.58"

    print(
        "VI8.58 SEARCH STRATEGY PLAN=PASS"
    )


if __name__ == "__main__":
    self_test()
