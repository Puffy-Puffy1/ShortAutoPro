#!/usr/bin/env python3

import argparse
import json
import os

from datetime import datetime
from pathlib import Path


VERSION = "6.51"


BASE = Path.home() / "ShortAutoPro"


SHADOW_REPORT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_50_shadow_compare_latest.json"
)


CERT_REPORT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_45_micro_render_latest.json"
)


GATE42_REPORT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_42_binding_gate_latest.json"
)


OUTPUT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_51_canary_gate_latest.json"
)


SAFE_STATUSES = {
    "EXACT_MATCH",
    "SAFE_DIFFERENCE",
    "NATIVE_VIDEO_PRESERVE",
}


def _load(
    path,
    key
):

    try:

        with Path(
            path
        ).open(
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(
                f
            ).get(
                key
            )


    except Exception:

        return None


def evaluate(
    shadow,
    cert,
    gate42
):

    blockers = []

    warnings = []


    if gate42 is None:

        blockers.append(
            "vi642_missing"
        )


    elif not gate42.get(
        "next_stage_allowed"
    ):

        blockers.append(
            "vi642_not_ready"
        )


    if cert is None:

        blockers.append(
            "vi645_missing"
        )


    else:

        if (
            cert.get(
                "status"
            )
            != "CERTIFIED"
        ):

            blockers.append(
                "vi645_not_certified"
            )


        if (
            cert.get(
                "temporary_video_deleted"
            )
            is not True
        ):

            blockers.append(
                "vi645_cleanup_not_verified"
            )


    if shadow is None:

        blockers.append(
            "shadow_run_missing"
        )


        unique_scenes = 0

        events = []


    else:

        unique_scenes = int(
            shadow.get(
                "unique_scenes",
                0
            )
            or 0
        )


        events = (
            shadow.get(
                "events"
            )
            or []
        )


        if unique_scenes < 12:

            blockers.append(
                "shadow_requires_12_unique_scenes"
            )


        if int(
            shadow.get(
                "holds",
                0
            )
            or 0
        ) > 0:

            blockers.append(
                "shadow_contains_hold"
            )


        if int(
            shadow.get(
                "command_mutations",
                0
            )
            or 0
        ) != 0:

            blockers.append(
                "shadow_command_mutation_detected"
            )


        if int(
            shadow.get(
                "filter_replacements",
                0
            )
            or 0
        ) != 0:

            blockers.append(
                "shadow_filter_replacement_detected"
            )


        unsafe = [

            event
            for event in events

            if event.get(
                "status"
            )
            not in SAFE_STATUSES
        ]


        if unsafe:

            blockers.append(
                "unsafe_shadow_status"
            )


        scenes = sorted(
            {
                event.get(
                    "scene"
                )
                for event in events
                if isinstance(
                    event.get(
                        "scene"
                    ),
                    int
                )
            }
        )


        if (
            unique_scenes >= 12
            and scenes[:12]
            != list(
                range(
                    1,
                    13
                )
            )
        ):

            warnings.append(
                "scene_numbers_not_exact_1_to_12"
            )


    if blockers:

        if blockers == [
            "shadow_run_missing"
        ]:

            status = (
                "WAITING_FOR_SHADOW_RUN"
            )

        else:

            status = "HOLD"


    elif warnings:

        status = (
            "READY_FOR_CANARY_PATCH_WITH_WARNINGS"
        )


    else:

        status = (
            "READY_FOR_CANARY_PATCH"
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

        "unique_scenes":
            unique_scenes,

        "safe_shadow_statuses":
            sorted(
                SAFE_STATUSES
            ),

        # O gate NÃO ativa nada.
        "active_canary_authorized":
            False,

        "active_renderer":
            False,

        "next_stage_allowed":
            status
            in {
                "READY_FOR_CANARY_PATCH",
                "READY_FOR_CANARY_PATCH_WITH_WARNINGS",
            },
    }


def evaluate_real():

    shadow = _load(
        SHADOW_REPORT,
        "summary"
    )


    cert = _load(
        CERT_REPORT,
        "certification"
    )


    gate42 = _load(
        GATE42_REPORT,
        "gate"
    )


    return evaluate(
        shadow,
        cert,
        gate42
    )


def save(
    result
):

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    OUTPUT.write_text(
        json.dumps(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "gate":
                    result,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    return str(
        OUTPUT
    )


def self_test():

    shadow = {

        "unique_scenes":
            12,

        "holds":
            0,

        "command_mutations":
            0,

        "filter_replacements":
            0,

        "events":
            [
                {
                    "scene":
                        n,

                    "status":
                        (
                            "NATIVE_VIDEO_PRESERVE"
                            if n == 5
                            else "SAFE_DIFFERENCE"
                        ),
                }

                for n in range(
                    1,
                    13
                )
            ],
    }


    cert = {

        "status":
            "CERTIFIED",

        "temporary_video_deleted":
            True,
    }


    gate42 = {

        "next_stage_allowed":
            True
    }


    result = evaluate(
        shadow,
        cert,
        gate42
    )


    assert (
        result[
            "status"
        ]
        == "READY_FOR_CANARY_PATCH"
    )


    assert (
        result[
            "active_canary_authorized"
        ]
        is False
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.51 CANARY GATE: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK 12 Scene Requirement"
    )
    print(
        "OK Zero HOLD Requirement"
    )
    print(
        "OK Zero Mutation Requirement"
    )
    print(
        "OK VI6.45 Certification Requirement"
    )
    print(
        "OK Canary Still Locked"
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


    if args.real:

        result = evaluate_real()

        path = save(
            result
        )


        print()
        print(
            "===== VI6.51 REAL CANARY GATE ====="
        )


        print(
            "STATUS:",
            result.get(
                "status"
            )
        )


        print(
            "UNIQUE SCENES:",
            result.get(
                "unique_scenes"
            )
        )


        print(
            "BLOCKERS:",
            result.get(
                "blockers"
            )
        )


        print(
            "WARNINGS:",
            result.get(
                "warnings"
            )
        )


        print(
            "NEXT STAGE:",
            result.get(
                "next_stage_allowed"
            )
        )


        print(
            "ACTIVE CANARY AUTHORIZED:",
            result.get(
                "active_canary_authorized"
            )
        )


        print(
            "REPORT:",
            path
        )


if __name__ == "__main__":
    main()
