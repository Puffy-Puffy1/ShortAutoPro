#!/usr/bin/env python3

import os

from vi6_37_renderer_shadow_adapter import (
    inspect_renderer
)

from vi6_38_filter_validator import (
    validate as validate_filter
)


VERSION = "6.40.3"

PHASE_LOCK = "SHADOW_ONLY"


def _mode():

    value = str(
        os.getenv(
            "VI640_RENDERER_MODE",
            "SHADOW"
        )
        or "SHADOW"
    ).strip().upper()


    if value not in {
        "OFF",
        "SHADOW",
        "ACTIVE",
    }:

        value = "SHADOW"


    return value


def build_shadow_request(
    meta,
    adapter=None
):

    meta = dict(
        meta
        or {}
    )


    requested = _mode()


    if requested == "OFF":

        return {
            "version":
                VERSION,

            "status":
                "DISABLED",

            "ready":
                False,

            "binding_performed":
                False,
        }


    if adapter is None:

        adapter = inspect_renderer(
            "video.py"
        )


    contract = (
        meta.get(
            "vi634_repaired_contract"
        )
        or meta.get(
            "vi630_renderer_contract"
        )
        or {}
    )


    dry_plan = (
        meta.get(
            "vi635_ffmpeg_dry_plan"
        )
        or {}
    )


    safety = (
        meta.get(
            "vi633_post_repair_safety"
        )
        or meta.get(
            "vi633_cinematic_safety"
        )
        or {}
    )


    compatibility = (
        meta.get(
            "vi636_renderer_compatibility"
        )
        or {}
    )


    filter_report = validate_filter(
        dry_plan
    )


    blockers = []


    if (
        adapter.get(
            "status"
        )
        != "SHADOW_READY"
    ):

        blockers.append(
            "renderer_map_not_ready"
        )


    if (
        filter_report.get(
            "status"
        )
        != "PASS"
    ):

        blockers.append(
            "filter_not_valid"
        )


    if (
        compatibility.get(
            "status"
        )
        != "STATIC_PASS"
    ):

        blockers.append(
            "compatibility_not_pass"
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
            "renderer_already_applied"
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


    if requested == "ACTIVE":

        blockers.append(
            "active_locked"
        )


    primary = (
        adapter.get(
            "primary_scene_renderer"
        )
        or {}
    )


    status = (
        "SHADOW_READY"
        if not blockers
        else "HOLD"
    )


    return {

        "version":
            VERSION,

        "phase_lock":
            PHASE_LOCK,

        "status":
            status,

        "ready":
            status
            == "SHADOW_READY",

        "blockers":
            blockers,

        "architecture":
            adapter.get(
                "architecture"
            ),

        "target_kind":
            primary.get(
                "kind"
            ),

        "target_role":
            primary.get(
                "role"
            ),

        "target_execution_line":
            primary.get(
                "execution_line"
            ),

        "target_stage_start":
            primary.get(
                "stage_start"
            ),

        "target_stage_end":
            primary.get(
                "stage_end"
            ),

        "target_confidence":
            primary.get(
                "score"
            ),

        "video_sha256":
            adapter.get(
                "file_sha256"
            ),

        "filter_report":
            filter_report,

        "dry_plan":
            dry_plan,

        "binding_performed":
            False,

        "video_py_modified":
            False,

        "renderer_executed":
            False,
    }


def self_test():

    adapter = {

        "status":
            "SHADOW_READY",

        "architecture":
            "MODULE_LEVEL_PIPELINE",

        "file_sha256":
            "abc",

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
            }
    }


    meta = {

        "vi634_repaired_contract":
            {
                "renderer_applied":
                    False
            },

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

        "vi635_ffmpeg_dry_plan":
            {
                "mode":
                    "DRY_RUN",

                "executed":
                    False,

                "renderer_mode":
                    "NATIVE_VIDEO_PRESERVE",

                "vf":
                    None,

                "argv":
                    None,
            },
    }


    result = build_shadow_request(
        meta,
        adapter
    )


    assert (
        result[
            "status"
        ]
        == "SHADOW_READY"
    )


    assert (
        result[
            "target_execution_line"
        ]
        == 970
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.40.3 BRIDGE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Module-Level Stage Target"
    )
    print(
        "OK SHADOW Lock"
    )
    print()


if __name__ == "__main__":
    self_test()
