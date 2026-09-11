#!/usr/bin/env python3

VERSION = "7.97"

def evaluate(
    audit,
    forecast_result
):
    blockers = (
        audit.get("blockers")
        or []
    )

    warnings = (
        audit.get("warnings")
        or []
    )

    score = float(
        forecast_result.get(
            "forecast_score",
            0
        )
    )

    if blockers:
        status = "HOLD"

    elif score >= 75:
        status = (
            "READY_FOR_CONTROLLED_INTEGRATION"
        )

    else:
        status = (
            "SHADOW_TUNING_REQUIRED"
        )

    return {
        "version": VERSION,
        "status": status,
        "forecast_score": score,
        "blockers": blockers,
        "warnings": warnings,
        "runtime_activation":
            False,
        "full_active":
            False,
    }

def self_test():
    result = evaluate(
        {
            "blockers": [],
            "warnings": [],
        },
        {
            "forecast_score": 85
        }
    )

    assert (
        result["status"]
        == "READY_FOR_CONTROLLED_INTEGRATION"
    )

    print(
        "VI7.97 RELEASE CANDIDATE=PASS"
    )

if __name__ == "__main__":
    self_test()
