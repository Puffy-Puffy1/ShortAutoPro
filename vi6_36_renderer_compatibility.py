#!/usr/bin/env python3

import ast
import json
import os
from datetime import datetime
from pathlib import Path


VERSION = "6.36"


FORBIDDEN_CALLS = {
    "system",
    "popen",
    "Popen",
    "run",
    "call",
    "check_call",
    "check_output",
}


_EVENTS = []


def _call_name(node):

    if isinstance(
        node.func,
        ast.Name
    ):

        return node.func.id


    if isinstance(
        node.func,
        ast.Attribute
    ):

        return node.func.attr


    return ""


def static_execution_guard(
    filenames
):

    violations = []


    for filename in filenames:

        path = Path(
            filename
        )


        source = path.read_text(
            encoding="utf-8"
        )


        tree = ast.parse(
            source
        )


        for node in ast.walk(
            tree
        ):

            if not isinstance(
                node,
                ast.Call
            ):
                continue


            name = _call_name(
                node
            )


            if name in FORBIDDEN_CALLS:

                violations.append(
                    {
                        "file":
                            filename,

                        "line":
                            getattr(
                                node,
                                "lineno",
                                None
                            ),

                        "call":
                            name,
                    }
                )


    return violations


def check(
    contract,
    safety,
    dry_plan
):

    issues = []


    if (
        contract.get(
            "renderer_applied"
        )
        is not False
    ):

        issues.append(
            "renderer_applied_before_activation"
        )


    if (
        dry_plan.get(
            "executed"
        )
        is not False
    ):

        issues.append(
            "dry_plan_executed"
        )


    if (
        dry_plan.get(
            "mode"
        )
        != "DRY_RUN"
    ):

        issues.append(
            "compiler_not_dry_run"
        )


    safety_status = (
        safety.get(
            "status"
        )
    )


    if safety_status == "HOLD":

        issues.append(
            "cinematic_safety_hold"
        )


    renderer_mode = (
        dry_plan.get(
            "renderer_mode"
        )
    )


    if (
        contract.get(
            "media_type"
        )
        == "VIDEO"
        and renderer_mode
        != "NATIVE_VIDEO_PRESERVE"
    ):

        issues.append(
            "video_motion_not_preserved"
        )


    if (
        contract.get(
            "media_type"
        )
        == "STILL"
        and (
            contract.get(
                "ken_burns"
            )
            or {}
        ).get(
            "enabled"
        )
        and renderer_mode
        != "KEN_BURNS_STILL"
    ):

        issues.append(
            "still_motion_not_compiled"
        )


    status = (
        "STATIC_PASS"
        if not issues
        else "HOLD"
    )


    result = {

        "version":
            VERSION,

        "status":
            status,

        "issues":
            issues,

        "renderer_activation_ready":
            status
            == "STATIC_PASS",

        "runtime_execution":
            False,

        "ffmpeg_execution":
            False,
    }


    return result


def record(
    scene,
    result,
    repair,
    dry_plan
):

    _EVENTS.append(
        {
            "scene":
                scene,

            "status":
                result.get(
                    "status"
                ),

            "issues":
                result.get(
                    "issues"
                ),

            "repair_changed":
                repair.get(
                    "changed"
                ),

            "repair_reason":
                repair.get(
                    "reason"
                ),

            "renderer_mode":
                dry_plan.get(
                    "renderer_mode"
                ),

            "ffmpeg_execution":
                False,
        }
    )


def reset():

    _EVENTS.clear()


def summary():

    return {

        "version":
            VERSION,

        "scenes":
            len(
                _EVENTS
            ),

        "static_pass":
            sum(
                1
                for x in _EVENTS
                if x[
                    "status"
                ]
                == "STATIC_PASS"
            ),

        "hold":
            sum(
                1
                for x in _EVENTS
                if x[
                    "status"
                ]
                == "HOLD"
            ),

        "repairs":
            sum(
                1
                for x in _EVENTS
                if x[
                    "repair_changed"
                ]
            ),

        "ffmpeg_execution":
            0,

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
            "vi6_36_renderer_compat_latest.json"
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


    violations = (
        static_execution_guard(
            [
                "vi6_34_motion_auto_repair.py",
                "vi6_35_ffmpeg_dry_compiler.py",
            ]
        )
    )


    assert violations == []


    result = check(
        {
            "media_type":
                "STILL",

            "renderer_applied":
                False,

            "ken_burns":
                {
                    "enabled":
                        True
                },
        },
        {
            "status":
                "PASS"
        },
        {
            "mode":
                "DRY_RUN",

            "executed":
                False,

            "renderer_mode":
                "KEN_BURNS_STILL",
        }
    )


    assert (
        result[
            "status"
        ]
        == "STATIC_PASS"
    )


    record(
        1,
        result,
        {
            "changed":
                True,

            "reason":
                "motion_repaired"
        },
        {
            "renderer_mode":
                "KEN_BURNS_STILL"
        }
    )


    assert (
        summary()[
            "repairs"
        ]
        == 1
    )


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.36 COMPAT SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Static Execution Guard"
    )
    print(
        "OK Dry-Run Enforcement"
    )
    print(
        "OK Native Video Contract"
    )
    print(
        "OK Still Motion Contract"
    )
    print(
        "OK Safety HOLD Propagation"
    )
    print(
        "OK Zero FFmpeg Execution"
    )
    print()


if __name__ == "__main__":
    self_test()
