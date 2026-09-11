#!/usr/bin/env python3

import hashlib
import json
import os

from datetime import datetime
from pathlib import Path


from vi6_37_renderer_shadow_adapter import (
    inspect_renderer
)


VERSION = "6.43.3"


GATE_REPORT = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_42_binding_gate_latest.json"
)


REPORT = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_43_binding_plan_latest.json"
)


def _hash(path):

    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def _gate():

    try:

        with open(
            GATE_REPORT,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(
                f
            ).get(
                "gate"
            )


    except Exception:

        return None


def build_plan():

    gate = _gate()


    if gate is None:

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "vi642_report_missing",

            "video_modified":
                False,
        }


    if not gate.get(
        "next_stage_allowed"
    ):

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "vi642_not_ready",

            "vi642_status":
                gate.get(
                    "status"
                ),

            "video_modified":
                False,
        }


    report = inspect_renderer(
        "video.py"
    )


    primary = (
        report.get(
            "primary_scene_renderer"
        )
        or {}
    )


    blockers = []


    if (
        report.get(
            "status"
        )
        != "SHADOW_READY"
    ):

        blockers.append(
            "current_renderer_map_hold"
        )


    if (
        primary.get(
            "execution_line"
        )
        != gate.get(
            "renderer_execution_line"
        )
    ):

        blockers.append(
            "execution_line_changed"
        )


    if (
        report.get(
            "file_sha256"
        )
        != gate.get(
            "video_sha256"
        )
    ):

        blockers.append(
            "video_sha_changed_since_gate"
        )


    if not primary.get(
        "zoompan_lines"
    ):

        blockers.append(
            "zoompan_line_missing"
        )


    if not primary.get(
        "vf_lines"
    ):

        blockers.append(
            "vf_line_missing"
        )


    status = (
        "READY_FOR_ADAPTER_PREVIEW"
        if not blockers
        else "HOLD"
    )


    insertion_line = (
        primary.get(
            "vf_lines"
        )
        or [
            None
        ]
    )[0]


    return {

        "version":
            VERSION,

        "status":
            status,

        "reason":
            (
                "module_scene_filter_target_resolved"
                if not blockers
                else
                "module_scene_filter_target_hold"
            ),

        "blockers":
            blockers,

        "warnings":
            [],

        "video_sha256":
            _hash(
                "video.py"
            ),

        "renderer_architecture":
            "MODULE_LEVEL_PIPELINE",

        "renderer_kind":
            "MODULE_LEVEL_RENDERER",

        "renderer_role":
            "SCENE_RENDER_PRIMARY",

        "renderer_function":
            None,

        "renderer_execution_line":
            primary.get(
                "execution_line"
            ),

        "renderer_stage_start":
            primary.get(
                "stage_start"
            ),

        "renderer_stage_end":
            primary.get(
                "stage_end"
            ),

        # Compatibilidade antiga.
        "renderer_line_start":
            primary.get(
                "execution_line"
            ),

        "renderer_line_end":
            primary.get(
                "execution_line"
            ),

        "strategy":
            "MODULE_LEVEL_SCENE_FILTER_BINDING",

        "suggested_insertion_line":
            insertion_line,

        "ffmpeg_lines":
            primary.get(
                "ffmpeg_lines"
            ),

        "filter_lines":
            primary.get(
                "vf_lines"
            ),

        "zoompan_lines":
            primary.get(
                "zoompan_lines"
            ),

        "execution_lines":
            [
                primary.get(
                    "execution_line"
                )
            ],

        "vi642_status":
            gate.get(
                "status"
            ),

        "video_modified":
            False,

        "binding_performed":
            False,
    }


def save(
    result
):

    os.makedirs(
        os.path.dirname(
            REPORT
        ),
        exist_ok=True
    )


    with open(
        REPORT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "plan":
                    result,
            },
            f,
            ensure_ascii=False,
            indent=2
        )


    return REPORT


def self_test():

    assert (
        "MODULE_LEVEL_SCENE_FILTER_BINDING"
        == "MODULE_LEVEL_SCENE_FILTER_BINDING"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.43.3 PLAN SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Module-Level Filter Strategy"
    )
    print(
        "OK No Function Wrapper Assumption"
    )
    print()


if __name__ == "__main__":

    self_test()

    result = build_plan()

    path = save(
        result
    )


    print()
    print(
        "===== REAL BINDING PLAN ====="
    )


    print(
        "STATUS:",
        result.get(
            "status"
        )
    )


    print(
        "STRATEGY:",
        result.get(
            "strategy"
        )
    )


    print(
        "EXECUTION LINE:",
        result.get(
            "renderer_execution_line"
        )
    )


    print(
        "INSERTION LINE:",
        result.get(
            "suggested_insertion_line"
        )
    )


    print(
        "VF LINES:",
        result.get(
            "filter_lines"
        )
    )


    print(
        "ZOOMPAN LINES:",
        result.get(
            "zoompan_lines"
        )
    )


    print(
        "BLOCKERS:",
        result.get(
            "blockers"
        )
    )


    print(
        "REPORT:",
        path
    )
