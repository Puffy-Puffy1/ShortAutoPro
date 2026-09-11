#!/usr/bin/env python3

VERSION = "7.79"

def evaluate(plans):
    blockers = []
    warnings = []

    safe = [
        item
        for item in plans
        if item.get("status") == "PASS"
    ]

    average_quality = (
        sum(
            float(
                item.get(
                    "quality_score",
                    0
                )
            )
            for item in plans
        ) / len(plans)
        if plans
        else 0.0
    )

    mismatches = [
        item.get("scene")
        for item in plans
        if not item.get(
            "shot_match",
            False
        )
    ]

    risky = [
        item.get("scene")
        for item in plans
        if (
            item.get("risk")
            or {}
        ).get("status") == "HOLD"
    ]

    if len(safe) < 8:
        blockers.append(
            "too_few_safe_scene_plans"
        )

    if risky:
        blockers.append(
            "visual_risk_hold_present"
        )

    if average_quality < 75:
        warnings.append(
            "visual_quality_average_low"
        )

    if len(mismatches) >= 4:
        warnings.append(
            "shot_language_mismatch"
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
        "safe_scene_count":
            len(safe),
        "average_quality":
            round(
                average_quality,
                2
            ),
        "shot_mismatch_scenes":
            mismatches,
        "risk_hold_scenes":
            risky,
        "blockers":
            blockers,
        "warnings":
            warnings,
    }

def self_test():
    result = evaluate([
        {
            "scene": i,
            "status": "PASS",
            "quality_score": 90,
            "shot_match": True,
            "risk": {
                "status": "PASS"
            },
        }
        for i in range(1, 13)
    ])

    assert result["status"] == "PASS"
    assert result["safe_scene_count"] == 12

    print(
        "VI7.79 VISUAL QUALITY GATE=PASS"
    )

if __name__ == "__main__":
    self_test()
