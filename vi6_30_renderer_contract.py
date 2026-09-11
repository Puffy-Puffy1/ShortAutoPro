#!/usr/bin/env python3

import hashlib
import json
import os
from datetime import datetime


from vi6_28_motion_blueprint import (
    build_blueprint
)

from vi6_29_ken_burns_intelligence import (
    build_plan,
    validate as validate_ken_burns,
)


VERSION = "6.30"


_ALLOWED_TRANSITIONS = {

    "OPEN",
    "NONE",

    "CLEAN_CUT",
    "DIRECT_CUT",
    "MATCH_CUT",
    "CONTRAST_CUT",
    "HARD_CUT",
    "FAST_CUT",
    "SOFT_CUT",
}


_CONTRACTS = []


def build_contract(
    scene,
    candidate,
    meta=None
):

    meta = (
        meta
        or {}
    )


    blueprint = (
        build_blueprint(
            scene,
            candidate,
            meta
        )
    )


    ken = build_plan(
        blueprint
    )


    transition = (
        blueprint.get(
            "transition"
        )
        or "DIRECT_CUT"
    ).upper()


    if (
        transition
        not in _ALLOWED_TRANSITIONS
    ):

        transition = (
            "DIRECT_CUT"
        )


    contract = {

        "version":
            VERSION,

        "scene":
            blueprint.get(
                "scene"
            ),

        "media_type":
            blueprint.get(
                "media_type"
            ),

        "role":
            blueprint.get(
                "role"
            ),

        "rhythm":
            blueprint.get(
                "rhythm"
            ),

        "profile":
            blueprint.get(
                "profile"
            ),

        "transition":
            transition,

        "synthetic_motion":
            blueprint.get(
                "synthetic_motion",
                False
            ),

        "ken_burns":
            ken,

        "duration_mode":
            "SCENE_DURATION",

        "audio_sync":
            "PRESERVE",

        "subtitle_sync":
            "PRESERVE",

        "aspect_ratio":
            "9:16",

        "render_target":
            "1080x1920",

        # Muito importante:
        # este contrato ainda não altera
        # nenhum filtro FFmpeg.
        "ffmpeg_filter":
            None,

        "renderer_applied":
            False,

        "status":
            "PLANNED_ONLY",
    }


    canonical = json.dumps(
        contract,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":"
        )
    )


    contract[
        "contract_hash"
    ] = hashlib.sha256(
        canonical.encode(
            "utf-8"
        )
    ).hexdigest()[
        :16
    ]


    return contract


def validate_contract(
    contract
):

    errors = []


    if (
        contract.get(
            "aspect_ratio"
        )
        != "9:16"
    ):

        errors.append(
            "aspect_ratio"
        )


    if (
        contract.get(
            "render_target"
        )
        != "1080x1920"
    ):

        errors.append(
            "render_target"
        )


    if (
        contract.get(
            "audio_sync"
        )
        != "PRESERVE"
    ):

        errors.append(
            "audio_sync"
        )


    if (
        contract.get(
            "subtitle_sync"
        )
        != "PRESERVE"
    ):

        errors.append(
            "subtitle_sync"
        )


    if (
        contract.get(
            "ffmpeg_filter"
        )
        is not None
    ):

        errors.append(
            "renderer_must_remain_inactive"
        )


    if (
        contract.get(
            "renderer_applied"
        )
        is not False
    ):

        errors.append(
            "renderer_applied"
        )


    transition = (
        contract.get(
            "transition"
        )
    )


    if (
        transition
        not in _ALLOWED_TRANSITIONS
    ):

        errors.append(
            "transition"
        )


    ken = (
        contract.get(
            "ken_burns"
        )
        or {}
    )


    ok_ken, ken_errors = (
        validate_ken_burns(
            ken
        )
    )


    if not ok_ken:

        errors.extend(
            [
                "ken_burns:"
                + error

                for error
                in ken_errors
            ]
        )


    return (
        len(
            errors
        ) == 0,
        errors
    )


def record_contract(
    contract
):

    _CONTRACTS.append(
        dict(
            contract
        )
    )


def reset():

    _CONTRACTS.clear()


def summary():

    still = sum(
        1
        for item in _CONTRACTS
        if item.get(
            "media_type"
        ) == "STILL"
    )


    video = sum(
        1
        for item in _CONTRACTS
        if item.get(
            "media_type"
        ) == "VIDEO"
    )


    ken = sum(
        1
        for item in _CONTRACTS
        if (
            item.get(
                "ken_burns"
            )
            or {}
        ).get(
            "enabled"
        )
    )


    return {

        "version":
            VERSION,

        "contracts":
            len(
                _CONTRACTS
            ),

        "still":
            still,

        "video":
            video,

        "ken_burns_planned":
            ken,

        "renderer_applied":
            0,

        "contracts_detail":
            list(
                _CONTRACTS
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
            "vi6_30_renderer_contract_latest.json"
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


    scene = {

        "retrieval_role_6_7":
            "EVIDENCE",

        "_vi68_storyboard":
            {
                "scene": 5,
                "rhythm":
                    "ESCALATION"
            }
    }


    candidate = {

        "tipo":
            "foto",

        "_vi6_class":
            "REAL_DOCUMENTARY",

        "_vi6_truth_ok":
            True,
    }


    contract = build_contract(
        scene,
        candidate,
        {
            "class":
                "REAL_DOCUMENTARY",

            "truth_ok":
                True,

            "vi627_transition":
                "DIRECT_CUT",
        }
    )


    ok, errors = (
        validate_contract(
            contract
        )
    )


    assert ok is True

    assert errors == []


    assert (
        contract[
            "ffmpeg_filter"
        ]
        is None
    )


    assert (
        contract[
            "renderer_applied"
        ]
        is False
    )


    assert (
        contract[
            "audio_sync"
        ]
        == "PRESERVE"
    )


    assert (
        contract[
            "subtitle_sync"
        ]
        == "PRESERVE"
    )


    record_contract(
        contract
    )


    assert (
        summary()[
            "contracts"
        ]
        == 1
    )


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.30 CONTRACT SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK 9:16 Contract"
    )
    print(
        "OK 1080x1920 Contract"
    )
    print(
        "OK Audio Sync Preserve"
    )
    print(
        "OK Subtitle Sync Preserve"
    )
    print(
        "OK Transition Contract"
    )
    print(
        "OK Ken Burns Validation"
    )
    print(
        "OK FFmpeg remains inactive"
    )
    print()


if __name__ == "__main__":

    self_test()
