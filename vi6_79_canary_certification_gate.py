#!/usr/bin/env python3

VERSION = "6.79"


def evaluate(
    render,
    comparison,
    artifacts,
    rollback
):

    blockers = []

    warnings = []


    if render.get(
        "status"
    ) != "RENDERED":

        blockers.append(
            "twin_render_failed"
        )


    if comparison.get(
        "status"
    ) == "HOLD":

        blockers.append(
            "technical_comparison_hold"
        )


    warnings.extend(
        comparison.get(
            "warnings"
        )
        or []
    )


    if artifacts.get(
        "status"
    ) != "PASS":

        blockers.append(
            "preview_artifacts_missing"
        )


    if rollback.get(
        "failure_action"
    ) != (
        "RENDER_SAME_SCENE_"
        "WITH_LEGACY_FILTER"
    ):

        blockers.append(
            "rollback_contract_invalid"
        )


    status = (
        "HOLD"
        if blockers
        else (
            "TECHNICALLY_CERTIFIED_WITH_WARNINGS"
            if warnings
            else "TECHNICALLY_CERTIFIED"
        )
    )


    return {
        "version": VERSION,

        "status": status,

        "blockers": blockers,

        "warnings": warnings,

        "human_visual_review_required":
            True,

        # Technical certification is not
        # yet production activation.
        "runtime_canary_authorized":
            False,

        "active_renderer":
            False,
    }


def self_test():

    result = evaluate(
        {
            "status": "RENDERED"
        },

        {
            "status": "PASS",
            "warnings": [],
        },

        {
            "status": "PASS"
        },

        {
            "failure_action":
                "RENDER_SAME_SCENE_"
                "WITH_LEGACY_FILTER"
        },
    )


    assert (
        result["status"]
        == "TECHNICALLY_CERTIFIED"
    )


    assert (
        result[
            "runtime_canary_authorized"
        ]
        is False
    )


    print(
        "VI6.79 CANARY CERTIFICATION=PASS"
    )


if __name__ == "__main__":
    self_test()
