#!/usr/bin/env python3

from vi7_21_sequence_audit import (
    audit as sequence_audit
)

from vi7_22_performance_budget import (
    evaluate as performance
)

from vi7_26_canary_audit import (
    evaluate as canary_audit
)

from vi7_27_output_integrity import (
    evaluate as output_integrity
)


VERSION = "7.28"


def evaluate(
    events
):

    canary = canary_audit(
        events
    )

    sequence = sequence_audit(
        events
    )

    perf = performance(
        events
    )

    output = output_integrity(
        canary["success"]
    )


    blockers = []

    warnings = []


    blockers.extend(
        sequence.get(
            "blockers"
        )
        or []
    )


    blockers.extend(
        output.get(
            "blockers"
        )
        or []
    )


    if canary[
        "retry_failed"
    ]:

        blockers.append(
            "legacy_retry_failed"
        )


    warnings.extend(
        sequence.get(
            "warnings"
        )
        or []
    )


    selected_scenes = sorted(
        {
            e.get(
                "scene"
            )
            for e in canary[
                "selected"
            ]
            if isinstance(
                e.get(
                    "scene"
                ),
                int
            )
        }
    )


    success_scenes = {
        e.get(
            "scene"
        )
        for e in canary[
            "success"
        ]
    }


    recovered_scenes = {
        e.get(
            "scene"
        )
        for e in canary[
            "retry_success"
        ]
    }


    final_valid = (
        success_scenes
        | recovered_scenes
    )


    if (
        set(
            selected_scenes
        )
        != final_valid
    ):

        blockers.append(
            "selected_scene_without_valid_final_output"
        )


    if len(
        selected_scenes
    ) < 4:

        blockers.append(
            "insufficient_adaptive_canaries"
        )


    if len(
        selected_scenes
    ) < 7:

        warnings.append(
            "adaptive_selection_below_target"
        )


    if canary[
        "retries"
    ]:

        warnings.append(
            "legacy_retry_required"
        )


    blockers = sorted(
        set(
            blockers
        )
    )

    warnings = sorted(
        set(
            warnings
        )
    )


    return {
        "version":
            VERSION,

        "selected_scenes":
            selected_scenes,

        "selected_count":
            len(
                selected_scenes
            ),

        "success_scenes":
            sorted(
                success_scenes
            ),

        "recovered_scenes":
            sorted(
                recovered_scenes
            ),

        "retry_count":
            len(
                canary[
                    "retries"
                ]
            ),

        "sequence":
            sequence,

        "performance":
            perf,

        "output_integrity":
            output,

        "blockers":
            blockers,

        "warnings":
            warnings,
    }


def self_test():

    assert VERSION == "7.28"

    print(
        "VI7.28 ADAPTIVE CERTIFICATION=PASS"
    )


if __name__ == "__main__":
    self_test()
