#!/usr/bin/env python3

VERSION = "6.54"


def assess(
    contract,
    event
):

    contract = dict(
        contract
        or {}
    )


    event = dict(
        event
        or {}
    )


    branch = contract.get(
        "branch"
    )


    duration = (
        contract.get(
            "duration_seconds"
        )
        or 0
    )


    role = contract.get(
        "role"
    )


    if branch == "VIDEO":

        profile = "NATIVE"

        zoom_budget = 0.0

        pan_budget = 0.0


    elif duration < 2.0:

        profile = "MICRO_MOTION"

        zoom_budget = .025

        pan_budget = .05


    elif role == "HOOK":

        profile = "HOOK_PUSH"

        zoom_budget = .065

        pan_budget = .12


    elif role == "CTA":

        profile = "CTA_SETTLE"

        zoom_budget = .025

        pan_budget = .06


    elif role == "CLIMAX":

        profile = "CLIMAX_DRIVE"

        zoom_budget = .055

        pan_budget = .11


    else:

        profile = "DOCUMENTARY_DRIFT"

        zoom_budget = .04

        pan_budget = .08


    proposed = event.get(
        "proposed_vi6_vf"
    )


    warnings = []


    if (
        branch == "STILL"
        and isinstance(
            proposed,
            str
        )
        and "zoompan="
        not in proposed
    ):

        warnings.append(
            "planned_still_without_zoompan"
        )


    return {

        "version":
            VERSION,

        "status":
            "PASS",

        "profile":
            profile,

        "zoom_budget":
            zoom_budget,

        "pan_budget":
            pan_budget,

        "warnings":
            warnings,

        "filter_mutated":
            False,
    }


def self_test():

    assert (
        assess(
            {
                "branch": "VIDEO",
                "duration_seconds": 4,
                "role": "CONTEXT",
            },
            {}
        )[
            "profile"
        ]
        == "NATIVE"
    )


    assert (
        assess(
            {
                "branch": "STILL",
                "duration_seconds": 1.2,
                "role": "CONTEXT",
            },
            {}
        )[
            "profile"
        ]
        == "MICRO_MOTION"
    )


    print(
        "VI6.54 MOTION INTELLIGENCE=PASS"
    )


if __name__ == "__main__":
    self_test()
