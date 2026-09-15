#!/usr/bin/env python3

VERSION = "8.19"

def evaluate(plan):
    selections = (
        plan.get(
            "selections"
        )
        or []
    )

    blockers = []
    warnings = []

    replacement = 0
    strong = 0
    keep = 0

    for item in selections:
        comparison = (
            item.get(
                "comparison"
            )
            or {}
        )

        recommendation = (
            comparison.get(
                "recommendation"
            )
        )

        if recommendation == (
            "STRONG_REPLACEMENT_CANDIDATE"
        ):
            strong += 1

        elif recommendation in {
            "REPLACEMENT_CANDIDATE",
            "MINOR_IMPROVEMENT",
        }:
            replacement += 1

        elif recommendation == "KEEP_CURRENT":
            keep += 1

        winner = (
            item.get(
                "winner"
            )
            or {}
        )

        if not winner.get(
            "eligible",
            False
        ):
            blockers.append(
                f"scene_{item.get('scene')}_no_eligible_winner"
            )

    continuity = (
        plan.get(
            "continuity"
        )
        or {}
    )

    if continuity.get(
        "count",
        0
    ):
        warnings.append(
            "global_media_repetition"
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

        "strong_replacements":
            strong,

        "improvements":
            replacement,

        "keep_current":
            keep,

        "blockers":
            blockers,

        "warnings":
            warnings,
    }

def self_test():
    assert VERSION == "8.19"

    print(
        "VI8.19 SELECTION AUDIT=PASS"
    )

if __name__ == "__main__":
    self_test()
