#!/usr/bin/env python3

VERSION = "8.24"


def evaluate(
    vi8_cinematic,
    selection_plan,
    budget
):
    blockers = []
    warnings = []

    old_forecast = float(
        vi8_cinematic.get(
            "forecast_score",
            0
        )
        or 0
    )

    selected_count = int(
        budget.get(
            "selected_count",
            0
        )
        or 0
    )

    continuity = (
        selection_plan.get(
            "continuity"
        )
        or {}
    )

    continuity_warnings = int(
        continuity.get(
            "count",
            0
        )
        or 0
    )

    if old_forecast < 75:
        blockers.append(
            "cinematic_baseline_too_low"
        )

    if selected_count > 6:
        blockers.append(
            "replacement_budget_exceeded"
        )

    if continuity_warnings >= 4:
        warnings.append(
            "media_continuity_risk"
        )

    if (
        vi8_cinematic.get(
            "blockers"
        )
        or []
    ):
        blockers.append(
            "existing_cinematic_blocker"
        )

    return {
        "version":
            VERSION,

        "status":
            (
                "HOLD"
                if blockers
                else (
                    "PASS_WITH_WARNINGS"
                    if warnings
                    else "PASS"
                )
            ),

        "baseline_forecast":
            old_forecast,

        "planned_changes":
            selected_count,

        "blockers":
            blockers,

        "warnings":
            warnings,
    }


def self_test():
    result = evaluate(
        {
            "forecast_score": 94,
            "blockers": [],
        },
        {
            "continuity": {
                "count": 0
            }
        },
        {
            "selected_count": 4
        }
    )

    assert result["status"] == "PASS"

    print(
        "VI8.24 GLOBAL REGRESSION GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
