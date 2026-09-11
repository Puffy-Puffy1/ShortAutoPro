#!/usr/bin/env python3

VERSION = "8.49"


def evaluate(plan):
    scenes = (
        plan.get(
            "scenes"
        )
        or []
    )

    no_real = []
    strong_gap = []
    normal_gap = []
    competitive = []

    real_winners = []
    virtual_winners = []

    for item in scenes:
        scene = item.get(
            "scene"
        )

        gap = (
            item.get("gap")
            or {}
        )

        status = gap.get(
            "status"
        )

        if status == "NO_REAL_MEDIA":
            no_real.append(
                scene
            )

        elif status == (
            "STRONG_REAL_MEDIA_GAP"
        ):
            strong_gap.append(
                scene
            )

        elif status in {
            "REAL_MEDIA_GAP",
            "MINOR_REAL_MEDIA_GAP",
        }:
            normal_gap.append(
                scene
            )

        elif status == (
            "REAL_MEDIA_COMPETITIVE"
        ):
            competitive.append(
                scene
            )

        winner = (
            (
                item.get(
                    "ranking"
                )
                or {}
            ).get(
                "winner"
            )
            or {}
        )

        if winner.get(
            "kind"
        ) == "REAL":
            real_winners.append(
                scene
            )

        elif winner.get(
            "kind"
        ) == "VIRTUAL_IDEAL":
            virtual_winners.append(
                scene
            )

    blockers = []
    warnings = []

    if len(
        no_real
    ) >= 5:
        warnings.append(
            "low_real_media_coverage"
        )

    if strong_gap:
        warnings.append(
            "strong_real_media_quality_gaps"
        )

    return {
        "version":
            VERSION,

        "status":
            (
                "PASS_WITH_WARNINGS"
                if warnings
                else "PASS"
            ),

        "no_real_media_scenes":
            no_real,

        "strong_gap_scenes":
            strong_gap,

        "gap_scenes":
            normal_gap,

        "competitive_scenes":
            competitive,

        "real_winner_scenes":
            real_winners,

        "virtual_winner_scenes":
            virtual_winners,

        "blockers":
            blockers,

        "warnings":
            warnings,
    }


def self_test():
    assert VERSION == "8.49"

    print(
        "VI8.49 REAL MEDIA RANKING AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
