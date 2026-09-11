#!/usr/bin/env python3

import json
import os
from datetime import datetime


VERSION = "6.39"


_EVENTS = []


def evaluate(
    adapter,
    filter_report,
    compatibility,
    safety,
    contract,
    dry_plan
):

    blockers = []
    warnings = []


    if (
        adapter.get(
            "status"
        )
        != "SHADOW_READY"
    ):

        blockers.append(
            "renderer_adapter_not_ready"
        )


    best = (
        adapter.get(
            "best"
        )
        or {}
    )


    if (
        float(
            best.get(
                "score",
                0
            )
            or 0
        )
        < 50
    ):

        blockers.append(
            "renderer_confidence_low"
        )


    if (
        filter_report.get(
            "status"
        )
        != "PASS"
    ):

        blockers.append(
            "filter_validation_failed"
        )


    if (
        compatibility.get(
            "status"
        )
        != "STATIC_PASS"
    ):

        blockers.append(
            "renderer_compatibility_hold"
        )


    if (
        safety.get(
            "status"
        )
        == "HOLD"
    ):

        blockers.append(
            "cinematic_safety_hold"
        )


    if (
        contract.get(
            "renderer_applied"
        )
        is not False
    ):

        blockers.append(
            "renderer_already_active"
        )


    if (
        dry_plan.get(
            "executed"
        )
        is not False
    ):

        blockers.append(
            "dry_plan_execution_detected"
        )


    if (
        adapter.get(
            "file_modified"
        )
        is not False
    ):

        blockers.append(
            "video_file_modified_in_shadow"
        )


    if (
        adapter.get(
            "candidate_count",
            0
        )
        > 5
    ):

        warnings.append(
            "multiple_renderer_candidates"
        )


    if blockers:

        status = "HOLD"


    elif warnings:

        status = (
            "READY_WITH_WARNINGS"
        )


    else:

        status = (
            "READY_FOR_CONTROLLED_BINDING"
        )


    return {

        "version":
            VERSION,

        "status":
            status,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "renderer_function":
            best.get(
                "function"
            ),

        "renderer_line":
            best.get(
                "line_start"
            ),

        "renderer_confidence":
            best.get(
                "score"
            ),

        # IMPORTANTE:
        # READY não significa ativado.
        "renderer_active":
            False,

        "ffmpeg_active":
            False,

        "binding_performed":
            False,

        "safe_for_next_stage":
            status
            in {
                "READY_FOR_CONTROLLED_BINDING",
                "READY_WITH_WARNINGS",
            },
    }


def record(
    scene,
    result
):

    _EVENTS.append(
        {
            "scene":
                scene,

            "status":
                result.get(
                    "status"
                ),

            "blockers":
                result.get(
                    "blockers"
                ),

            "warnings":
                result.get(
                    "warnings"
                ),

            "renderer_function":
                result.get(
                    "renderer_function"
                ),

            "renderer_line":
                result.get(
                    "renderer_line"
                ),

            "renderer_confidence":
                result.get(
                    "renderer_confidence"
                ),
        }
    )


def reset():

    _EVENTS.clear()


def summary():

    statuses = {}


    for event in _EVENTS:

        status = event[
            "status"
        ]


        statuses[
            status
        ] = (
            statuses.get(
                status,
                0
            )
            + 1
        )


    all_ready = bool(
        _EVENTS
    ) and all(
        event[
            "status"
        ]
        in {
            "READY_FOR_CONTROLLED_BINDING",
            "READY_WITH_WARNINGS",
        }
        for event in _EVENTS
    )


    return {

        "version":
            VERSION,

        "scenes":
            len(
                _EVENTS
            ),

        "statuses":
            statuses,

        "all_scenes_safe_for_next_stage":
            all_ready,

        "renderer_active":
            False,

        "ffmpeg_active":
            False,

        "events":
            list(
                _EVENTS
            ),
    }


def flush(
    path=None
):

    if path is None:

        folder = os.path.expanduser(
            "~/ShortAutoPro/logs/producao"
        )


        os.makedirs(
            folder,
            exist_ok=True
        )


        path = os.path.join(
            folder,
            "vi6_39_activation_gate_latest.json"
        )


    payload = {

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "summary":
            summary(),
    }


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2
        )


    return path


def self_test():

    reset()


    result = evaluate(
        {
            "status":
                "SHADOW_READY",

            "best":
                {
                    "function":
                        "gerar_video",

                    "line_start":
                        100,

                    "score":
                        90,
                },

            "candidate_count":
                1,

            "file_modified":
                False,
        },
        {
            "status":
                "PASS"
        },
        {
            "status":
                "STATIC_PASS"
        },
        {
            "status":
                "PASS"
        },
        {
            "renderer_applied":
                False
        },
        {
            "executed":
                False
        }
    )


    assert (
        result[
            "status"
        ]
        == "READY_FOR_CONTROLLED_BINDING"
    )


    assert (
        result[
            "renderer_active"
        ]
        is False
    )


    assert (
        result[
            "binding_performed"
        ]
        is False
    )


    record(
        1,
        result
    )


    assert (
        summary()[
            "all_scenes_safe_for_next_stage"
        ]
        is True
    )


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.39 ACTIVATION SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Shadow Adapter Requirement"
    )
    print(
        "OK Filter Validation Requirement"
    )
    print(
        "OK Compatibility Requirement"
    )
    print(
        "OK Cinematic Safety Requirement"
    )
    print(
        "OK Renderer-Inactive Requirement"
    )
    print(
        "OK Controlled-Binding Readiness"
    )
    print()


if __name__ == "__main__":

    self_test()
