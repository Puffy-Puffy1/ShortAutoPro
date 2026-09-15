#!/usr/bin/env python3

VERSION = "8.59"


def evaluate(plan):
    items = (
        plan.get("items")
        or []
    )

    budget = (
        plan.get("budget")
        or {}
    )

    blockers = []
    warnings = []

    selected = (
        budget.get(
            "selected"
        )
        or []
    )

    for item in selected:
        if item.get(
            "skip_search"
        ):
            blockers.append(
                f"scene_{item.get('scene')}_selected_but_guarded"
            )

        if not item.get(
            "search_query"
        ):
            blockers.append(
                f"scene_{item.get('scene')}_query_missing"
            )

    high_need = [
        x
        for x in items
        if x.get(
            "need"
        )
        in {
            "HIGH",
            "CRITICAL",
        }
    ]

    if (
        high_need
        and not selected
    ):
        warnings.append(
            "high_need_but_no_search_selected"
        )

    return {
        "version": VERSION,
        "status": (
            "HOLD"
            if blockers
            else (
                "PASS_WITH_WARNINGS"
                if warnings
                else "PASS"
            )
        ),
        "selected_count":
            len(selected),
        "selected_scenes":
            budget.get(
                "selected_scenes"
            ),
        "blockers":
            blockers,
        "warnings":
            warnings,
    }


def self_test():
    result = evaluate({
        "items": [],
        "budget": {
            "selected": [],
            "selected_scenes": [],
        }
    })

    assert (
        result["status"]
        == "PASS"
    )

    print(
        "VI8.59 SEARCH STRATEGY AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
