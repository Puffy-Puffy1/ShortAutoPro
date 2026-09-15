#!/usr/bin/env python3

from vi8_66_query_variant_generator import (
    generate
)

from vi8_67_query_diversity_guard import (
    evaluate as diversity
)

from vi8_68_search_contract import (
    build as contract
)

VERSION = "8.69"


def compile_plan(
    strategy_items
):
    plans = []

    for item in (
        strategy_items
        or []
    ):
        if item.get(
            "skip_search"
        ):
            continue

        if not item.get(
            "worthwhile"
        ):
            continue

        queries = generate(
            item.get(
                "search_query"
            )
            or "",
            item.get(
                "category"
            ),
            item.get(
                "ideal_shot"
            )
        )

        query_audit = diversity(
            queries
        )

        plan = contract(
            item.get(
                "scene"
            ),
            item.get(
                "category"
            ),
            item.get(
                "ideal_shot"
            ),
            item.get(
                "priority_score"
            ),
            queries
        )

        plan[
            "query_diversity"
        ] = query_audit

        plans.append(
            plan
        )

    plans.sort(
        key=lambda x:
            float(
                x.get(
                    "priority",
                    0
                )
            ),
        reverse=True
    )

    return {
        "version": VERSION,
        "plans": plans,
        "count": len(plans),
    }


def self_test():
    result = compile_plan([
        {
            "scene": 5,
            "category":
                "DOCUMENT",
            "ideal_shot":
                "close_up",
            "priority_score":
                80,
            "search_query":
                "ransom note",
            "skip_search":
                False,
            "worthwhile":
                True,
        }
    ])

    assert result[
        "count"
    ] == 1

    print(
        "VI8.69 SEARCH PLAN COMPILER=PASS"
    )


if __name__ == "__main__":
    self_test()
