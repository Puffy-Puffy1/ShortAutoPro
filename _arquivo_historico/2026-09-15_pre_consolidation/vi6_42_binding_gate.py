#!/usr/bin/env python3

import argparse
import json
import os

from datetime import datetime


from vi6_35_ffmpeg_dry_compiler import (
    compile_plan
)

from vi6_37_renderer_shadow_adapter import (
    inspect_renderer
)

from vi6_38_filter_validator import (
    validate as validate_filter
)

from vi6_40_controlled_renderer_bridge import (
    build_shadow_request
)

from vi6_41_ffmpeg_null_probe import (
    load_latest
)


VERSION = "6.42.3"


REPORT = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_42_binding_gate_latest.json"
)


def sample_meta():

    contract = {

        "media_type":
            "STILL",

        "role":
            "CONTEXT",

        "profile":
            "CONTEXT_DRIFT",

        "renderer_applied":
            False,

        "ken_burns":
            {
                "enabled":
                    True,

                "zoom_start":
                    1.0,

                "zoom_end":
                    1.04,

                "start_x":
                    .46,

                "start_y":
                    .50,

                "end_x":
                    .54,

                "end_y":
                    .50,
            },
    }


    dry = compile_plan(
        contract,
        {
            "seconds":
                4.0
        }
    )


    return {

        "vi634_repaired_contract":
            contract,

        "vi635_ffmpeg_dry_plan":
            dry,

        "vi633_post_repair_safety":
            {
                "status":
                    "PASS"
            },

        "vi636_renderer_compatibility":
            {
                "status":
                    "STATIC_PASS"
            },
    }


def evaluate(
    adapter,
    bridge,
    static_filter,
    probe
):

    blockers = []

    warnings = []


    primary = (
        adapter.get(
            "primary_scene_renderer"
        )
        or {}
    )


    if (
        adapter.get(
            "status"
        )
        != "SHADOW_READY"
    ):

        blockers.append(
            "renderer_shadow_map_hold"
        )


    if (
        bridge.get(
            "status"
        )
        != "SHADOW_READY"
    ):

        blockers.append(
            "controlled_bridge_hold"
        )


    if (
        static_filter.get(
            "status"
        )
        != "PASS"
    ):

        blockers.append(
            "static_filter_hold"
        )


    if probe is None:

        blockers.append(
            "real_ffmpeg_probe_missing"
        )


    elif (
        probe.get(
            "status"
        )
        != "PASS"
    ):

        blockers.append(
            "real_ffmpeg_probe_hold"
        )


    elif (
        probe.get(
            "video_file_created"
        )
        is not False
    ):

        blockers.append(
            "null_probe_created_video"
        )


    if (
        adapter.get(
            "architecture"
        )
        != "MODULE_LEVEL_PIPELINE"
    ):

        blockers.append(
            "unexpected_architecture"
        )


    if (
        primary.get(
            "role"
        )
        != "SCENE_RENDER_PRIMARY"
    ):

        blockers.append(
            "primary_role_not_proven"
        )


    confidence = float(
        primary.get(
            "score",
            0
        )
        or 0
    )


    if confidence < 100:

        blockers.append(
            "primary_confidence_low"
        )


    if not primary.get(
        "zoompan_lines"
    ):

        blockers.append(
            "primary_zoompan_not_proven"
        )


    if not primary.get(
        "vf_lines"
    ):

        blockers.append(
            "primary_vf_not_proven"
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

        "renderer_architecture":
            adapter.get(
                "architecture"
            ),

        "renderer_kind":
            primary.get(
                "kind"
            ),

        "renderer_role":
            primary.get(
                "role"
            ),

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
        "renderer_function":
            None,

        "renderer_line_start":
            primary.get(
                "execution_line"
            ),

        "renderer_line_end":
            primary.get(
                "execution_line"
            ),

        "renderer_confidence":
            confidence,

        "video_sha256":
            adapter.get(
                "file_sha256"
            ),

        "real_ffmpeg_probe":
            (
                probe.get(
                    "status"
                )
                if probe
                else None
            ),

        "real_ffmpeg_return_code":
            (
                probe.get(
                    "return_code"
                )
                if probe
                else None
            ),

        "binding_authorized":
            False,

        "binding_performed":
            False,

        "renderer_active":
            False,

        "next_stage_allowed":
            status
            in {
                "READY_FOR_CONTROLLED_BINDING",
                "READY_WITH_WARNINGS",
            },
    }


def evaluate_real():

    adapter = inspect_renderer(
        "video.py"
    )


    meta = sample_meta()


    bridge = build_shadow_request(
        meta,
        adapter
    )


    static_filter = validate_filter(
        meta[
            "vi635_ffmpeg_dry_plan"
        ]
    )


    probe = load_latest()


    return evaluate(
        adapter,
        bridge,
        static_filter,
        probe
    )


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

                "gate":
                    result,
            },
            f,
            ensure_ascii=False,
            indent=2
        )


    return REPORT


def self_test():

    adapter = {

        "status":
            "SHADOW_READY",

        "architecture":
            "MODULE_LEVEL_PIPELINE",

        "file_sha256":
            "x",

        "primary_scene_renderer":
            {
                "kind":
                    "MODULE_LEVEL_RENDERER",

                "role":
                    "SCENE_RENDER_PRIMARY",

                "execution_line":
                    970,

                "stage_start":
                    800,

                "stage_end":
                    970,

                "score":
                    130,

                "zoompan_lines":
                    [850],

                "vf_lines":
                    [890],
            },
    }


    result = evaluate(
        adapter,
        {
            "status":
                "SHADOW_READY"
        },
        {
            "status":
                "PASS"
        },
        {
            "status":
                "PASS",

            "return_code":
                0,

            "video_file_created":
                False,
        }
    )


    assert (
        result[
            "status"
        ]
        == "READY_FOR_CONTROLLED_BINDING"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.42.3 GATE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Module Architecture"
    )
    print(
        "OK Stage Confidence"
    )
    print(
        "OK Existing Real FFmpeg Probe"
    )
    print()


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--real",
        action="store_true"
    )

    args = parser.parse_args()


    self_test()


    if not args.real:
        return


    result = evaluate_real()

    path = save(
        result
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.42.3 REAL GATE"
    )
    print(
        "======================================"
    )


    print(
        "STATUS:",
        result.get(
            "status"
        )
    )


    print(
        "ARCHITECTURE:",
        result.get(
            "renderer_architecture"
        )
    )


    print(
        "PRIMARY LINE:",
        result.get(
            "renderer_execution_line"
        )
    )


    print(
        "PRIMARY STAGE:",
        result.get(
            "renderer_stage_start"
        ),
        "-",
        result.get(
            "renderer_stage_end"
        )
    )


    print(
        "CONFIDENCE:",
        result.get(
            "renderer_confidence"
        )
    )


    print(
        "FFMPEG PROBE:",
        result.get(
            "real_ffmpeg_probe"
        )
    )


    print(
        "NEXT STAGE:",
        result.get(
            "next_stage_allowed"
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


if __name__ == "__main__":
    main()
