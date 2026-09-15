#!/usr/bin/env python3

VERSION = "8.79"


def evaluate(
    architecture,
    candidates,
    recovery_lock
):
    blockers = []
    warnings = []

    if recovery_lock.get(
        "active_allowed"
    ):
        blockers.append(
            "source_recovery_not_locked"
        )

    if candidates.get(
        "count",
        0
    ) == 0:
        warnings.append(
            "no_safe_search_candidate_detected"
        )

    module_count = int(
        architecture.get(
            "module_count",
            0
        )
        or 0
    )

    if module_count == 0:
        warnings.append(
            "no_search_related_modules_detected"
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

        "blockers":
            blockers,

        "warnings":
            warnings,

        "network_execution":
            False,

        "integration_execution":
            False,
    }


def self_test():
    result = evaluate(
        {
            "module_count": 1
        },
        {
            "count": 1
        },
        {
            "active_allowed":
                False
        }
    )

    assert (
        result["status"]
        == "PASS"
    )

    print(
        "VI8.79 SEARCH ARCHITECTURE SAFETY GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
