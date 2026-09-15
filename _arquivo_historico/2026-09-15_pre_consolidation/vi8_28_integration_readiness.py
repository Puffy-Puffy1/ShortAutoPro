#!/usr/bin/env python3

VERSION = "8.28"


def evaluate(
    cinematic,
    selection_audit,
    regression,
    change_plan
):
    blockers = []
    warnings = []

    blockers.extend(
        cinematic.get(
            "blockers"
        )
        or []
    )

    blockers.extend(
        selection_audit.get(
            "blockers"
        )
        or []
    )

    blockers.extend(
        regression.get(
            "blockers"
        )
        or []
    )

    warnings.extend(
        cinematic.get(
            "warnings"
        )
        or []
    )

    warnings.extend(
        selection_audit.get(
            "warnings"
        )
        or []
    )

    warnings.extend(
        regression.get(
            "warnings"
        )
        or []
    )

    planned = int(
        change_plan.get(
            "planned_change_count",
            0
        )
        or 0
    )

    if planned == 0:
        warnings.append(
            "no_media_changes_selected"
        )

    blockers = sorted(
        set(blockers)
    )

    warnings = sorted(
        set(warnings)
    )

    if blockers:
        status = "HOLD"

    elif planned > 0:
        status = (
            "READY_FOR_MEDIA_INTEGRATION_PREVIEW"
        )

    else:
        status = (
            "SAFE_NO_CHANGE_REQUIRED"
        )

    return {
        "version":
            VERSION,

        "status":
            status,

        "planned_changes":
            planned,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "real_media_mutation":
            False,

        "renderer_activation":
            False,
    }


def self_test():
    result = evaluate(
        {
            "blockers": [],
            "warnings": [],
        },
        {
            "blockers": [],
            "warnings": [],
        },
        {
            "blockers": [],
            "warnings": [],
        },
        {
            "planned_change_count": 2
        }
    )

    assert (
        result["status"]
        == "READY_FOR_MEDIA_INTEGRATION_PREVIEW"
    )

    print(
        "VI8.28 INTEGRATION READINESS=PASS"
    )


if __name__ == "__main__":
    self_test()
