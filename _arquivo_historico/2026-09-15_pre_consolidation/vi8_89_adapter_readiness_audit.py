#!/usr/bin/env python3

VERSION = "8.89"


def evaluate(
    adapter_plan,
    call_contract,
    boundary
):
    blockers = []
    warnings = []

    best = (
        adapter_plan.get(
            "best"
        )
    )

    if not best:
        blockers.append(
            "no_safe_search_module"
        )

    contracts = (
        call_contract.get(
            "contracts"
        )
        or []
    )

    if not contracts:
        blockers.append(
            "no_search_contract"
        )

    review = [
        item
        for item in contracts
        if item.get(
            "status"
        )
        == "STATIC_REVIEW_REQUIRED"
    ]

    if review:
        warnings.append(
            "some_signatures_require_static_review"
        )

    if boundary.get(
        "status"
    ) != "LOCKED_SAFE":
        blockers.append(
            "side_effect_boundary_not_locked"
        )

    if blockers:
        status = "HOLD"

    elif review:
        status = (
            "READY_WITH_STATIC_REVIEW"
        )

    else:
        status = (
            "SAFE_ADAPTER_BLUEPRINT_READY"
        )

    return {
        "version": VERSION,
        "status": status,
        "blockers":
            blockers,
        "warnings":
            warnings,
        "contract_count":
            len(contracts),
        "review_count":
            len(review),
    }


def self_test():
    result = evaluate(
        {"best": {"module": "x.py"}},
        {
            "contracts": [{
                "status":
                    "READ_ONLY_SIGNATURE_ACCEPTABLE"
            }]
        },
        {
            "status":
                "LOCKED_SAFE"
        }
    )

    assert (
        result["status"]
        == "SAFE_ADAPTER_BLUEPRINT_READY"
    )

    print(
        "VI8.89 ADAPTER READINESS AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
