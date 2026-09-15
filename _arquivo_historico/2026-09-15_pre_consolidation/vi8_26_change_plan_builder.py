#!/usr/bin/env python3

from vi8_23_replacement_budget import (
    allocate
)

VERSION = "8.26"


def build(merged):
    items = (
        merged.get("items")
        or []
    )

    budget_input = []

    for item in items:
        budget_input.append({
            "scene":
                item.get(
                    "scene"
                ),

            "priority_score":
                item.get(
                    "priority_score"
                ),

            "recommendation":
                item.get(
                    "recommendation"
                ),

            "confidence":
                item.get(
                    "confidence"
                ),

            "category":
                item.get(
                    "category"
                ),

            "winner_shot":
                item.get(
                    "winner_shot"
                ),

            "winner_source":
                item.get(
                    "winner_source"
                ),

            "delta":
                item.get(
                    "delta"
                ),
        })

    budget = allocate(
        budget_input
    )

    return {
        "version":
            VERSION,

        "budget":
            budget,

        "planned_changes":
            budget.get(
                "selected"
            )
            or [],

        "planned_change_count":
            budget.get(
                "selected_count"
            ),
    }


def self_test():
    result = build({
        "items": []
    })

    assert (
        result[
            "planned_change_count"
        ]
        == 0
    )

    print(
        "VI8.26 CHANGE PLAN BUILDER=PASS"
    )


if __name__ == "__main__":
    self_test()
