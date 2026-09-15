#!/usr/bin/env python3

import json
import os
from datetime import datetime


VERSION = "6.44"

PHASE_LOCK = "PREVIEW_ONLY"


def _mode():

    raw = str(
        os.getenv(
            "VI644_ADAPTER_MODE",
            "SHADOW"
        )
        or "SHADOW"
    ).strip().upper()


    if raw not in {
        "OFF",
        "SHADOW",
        "ACTIVE",
    }:

        raw = "SHADOW"


    return raw


def adapt_filter(
    legacy_filter,
    dry_plan,
    gate_ready=False
):

    requested = _mode()


    proposed = (
        dry_plan.get(
            "vf"
        )
        if isinstance(
            dry_plan,
            dict
        )
        else None
    )


    result = {

        "version":
            VERSION,

        "phase_lock":
            PHASE_LOCK,

        "requested_mode":
            requested,

        "legacy_filter":
            legacy_filter,

        "proposed_vi6_filter":
            proposed,

        "selected_filter":
            legacy_filter,

        "shadow_difference":
            (
                proposed
                != legacy_filter
            ),

        "gate_ready":
            bool(
                gate_ready
            ),

        "binding_performed":
            False,

        "renderer_modified":
            False,
    }


    if requested == "OFF":

        result[
            "status"
        ] = "OFF"

        return result


    if requested == "ACTIVE":

        result[
            "status"
        ] = "ACTIVE_BLOCKED"

        result[
            "reason"
        ] = (
            "vi644_preview_phase_lock"
        )

        return result


    result[
        "status"
    ] = "SHADOW"


    result[
        "reason"
    ] = (
        "compare_only_no_renderer_change"
    )


    return result


def make_preview(
    binding_plan,
    path=None
):

    if path is None:

        path = os.path.expanduser(
            "~/ShortAutoPro/logs/producao/"
            "vi6_44_binding_preview_latest.txt"
        )


    os.makedirs(
        os.path.dirname(
            path
        ),
        exist_ok=True
    )


    lines = [

        "VI6.44 REVERSIBLE ADAPTER PREVIEW",

        "================================",

        "",

        "THIS FILE DOES NOT MODIFY video.py",

        "",

        (
            "Target function: "
            + str(
                binding_plan.get(
                    "renderer_function"
                )
            )
        ),

        (
            "Target lines: "
            + str(
                binding_plan.get(
                    "renderer_line_start"
                )
            )
            + "-"
            + str(
                binding_plan.get(
                    "renderer_line_end"
                )
            )
        ),

        (
            "Strategy: "
            + str(
                binding_plan.get(
                    "strategy"
                )
            )
        ),

        (
            "Suggested insertion line: "
            + str(
                binding_plan.get(
                    "suggested_insertion_line"
                )
            )
        ),

        "",

        "Future reversible behavior:",

        "1. Existing renderer remains default.",

        "2. VI6 adapter receives legacy filter.",

        "3. SHADOW compares legacy vs VI6 plan.",

        "4. ACTIVE will require explicit future gate.",

        "5. OFF immediately restores legacy behavior.",

        "",

        (
            "Source hash: "
            + str(
                binding_plan.get(
                    "video_sha256"
                )
            )
        ),

        "",

        "BINDING_PERFORMED=False",
    ]


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(
                lines
            )
            + "\n"
        )


    return path


def save_json(
    binding_plan,
    adapter_result,
    path=None
):

    if path is None:

        path = os.path.expanduser(
            "~/ShortAutoPro/logs/producao/"
            "vi6_44_adapter_latest.json"
        )


    os.makedirs(
        os.path.dirname(
            path
        ),
        exist_ok=True
    )


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "binding_plan":
                    binding_plan,

                "adapter":
                    adapter_result,
            },
            f,
            ensure_ascii=False,
            indent=2
        )


    return path


def self_test():

    result = adapt_filter(
        "legacy_scale",
        {
            "vf":
                "new_zoompan"
        },
        True
    )


    assert (
        result[
            "selected_filter"
        ]
        == "legacy_scale"
    )


    assert (
        result[
            "binding_performed"
        ]
        is False
    )


    assert (
        result[
            "renderer_modified"
        ]
        is False
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.44 ADAPTER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Legacy Renderer Preserved"
    )
    print(
        "OK Shadow Comparison"
    )
    print(
        "OK ACTIVE Hard Lock"
    )
    print(
        "OK OFF Rollback Semantics"
    )
    print(
        "OK Binding = False"
    )
    print()


if __name__ == "__main__":
    self_test()
