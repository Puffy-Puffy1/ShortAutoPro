#!/usr/bin/env python3

import hashlib
import json
import os
import re
import time

from datetime import datetime
from pathlib import Path


from vi6_35_ffmpeg_dry_compiler import (
    compile_plan
)

from vi6_38_filter_validator import (
    validate as validate_filter
)


VERSION = "6.50"


BASE = Path.home() / "ShortAutoPro"


DEFAULT_CONTRACT_REPORT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_30_renderer_contract_latest.json"
)


OUTPUT_REPORT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_50_shadow_compare_latest.json"
)


_EVENTS = {}


def _first(
    mapping,
    keys
):

    if not isinstance(
        mapping,
        dict
    ):

        return None


    for key in keys:

        if (
            key in mapping
            and mapping[
                key
            ]
            is not None
        ):

            return mapping[
                key
            ]


    return None


def _scene_number(
    mapping
):

    value = _first(
        mapping,
        (
            "scene",
            "scene_number",
            "scene_num",
            "number",
            "index",
            "cena",
        )
    )


    if isinstance(
        value,
        dict
    ):

        value = _first(
            value,
            (
                "scene",
                "number",
                "index",
            )
        )


    try:

        number = int(
            value
        )


        if 1 <= number <= 99:
            return number


    except Exception:
        pass


    return None


def _looks_like_contract(
    value
):

    if not isinstance(
        value,
        dict
    ):

        return False


    if (
        "ken_burns"
        in value
        and (
            "media_type"
            in value
            or "role"
            in value
        )
    ):

        return True


    if (
        "renderer_applied"
        in value
        and "media_type"
        in value
    ):

        return True


    return False


def _walk_contracts(
    value,
    inherited_scene=None,
    output=None
):

    if output is None:
        output = []


    if isinstance(
        value,
        dict
    ):

        scene = (
            _scene_number(
                value
            )
            or inherited_scene
        )


        if _looks_like_contract(
            value
        ):

            output.append(
                {
                    "scene":
                        scene,

                    "contract":
                        value,
                }
            )


        for key, child in value.items():

            # Algumas telemetrias guardam
            # o contrato sob esta chave.
            if (
                key
                == "vi630_renderer_contract"
                and isinstance(
                    child,
                    dict
                )
            ):

                child_scene = (
                    _scene_number(
                        child
                    )
                    or scene
                )


                output.append(
                    {
                        "scene":
                            child_scene,

                        "contract":
                            child,
                    }
                )


            _walk_contracts(
                child,
                scene,
                output
            )


    elif isinstance(
        value,
        list
    ):

        for child in value:

            _walk_contracts(
                child,
                inherited_scene,
                output
            )


    return output


def load_contracts(
    path=None
):

    if path is None:

        path = DEFAULT_CONTRACT_REPORT


    path = Path(
        path
    )


    if not path.exists():

        return {

            "status":
                "MISSING",

            "path":
                str(
                    path
                ),

            "age_seconds":
                None,

            "contracts":
                [],
        }


    try:

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )


    except Exception as exc:

        return {

            "status":
                "INVALID",

            "path":
                str(
                    path
                ),

            "error":
                type(
                    exc
                ).__name__,

            "contracts":
                [],
        }


    contracts = _walk_contracts(
        data
    )


    # Deduplica o mesmo objeto lógico.
    seen = set()

    unique = []


    for item in contracts:

        try:

            fingerprint = hashlib.sha256(
                json.dumps(
                    item[
                        "contract"
                    ],
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                ).encode(
                    "utf-8"
                )
            ).hexdigest()[:16]


        except Exception:

            fingerprint = str(
                id(
                    item[
                        "contract"
                    ]
                )
            )


        key = (
            item.get(
                "scene"
            ),
            fingerprint,
        )


        if key in seen:
            continue


        seen.add(
            key
        )


        item[
            "fingerprint"
        ] = fingerprint


        unique.append(
            item
        )


    age = max(
        0.0,
        time.time()
        - path.stat().st_mtime
    )


    max_age = float(
        os.getenv(
            "VI650_MAX_CONTRACT_AGE_SEC",
            "7200"
        )
    )


    return {

        "status":
            (
                "READY"
                if unique
                and age <= max_age
                else (
                    "STALE"
                    if unique
                    else "EMPTY"
                )
            ),

        "path":
            str(
                path
            ),

        "mtime":
            path.stat().st_mtime,

        "age_seconds":
            round(
                age,
                2
            ),

        "max_age_seconds":
            max_age,

        "contracts":
            unique,
    }


def _match_contract(
    mapped,
    registry
):

    scene = mapped.get(
        "scene"
    )


    if scene is None:

        return (
            None,
            "scene_unknown"
        )


    matches = [

        item
        for item in registry.get(
            "contracts",
            []
        )

        if item.get(
            "scene"
        )
        == scene
    ]


    if len(
        matches
    ) == 1:

        return (
            matches[0],
            "exact_scene"
        )


    if len(
        matches
    ) > 1:

        # Se houver duplicatas semânticas,
        # escolhe somente se todas apontarem
        # ao mesmo fingerprint.
        fingerprints = {
            item.get(
                "fingerprint"
            )
            for item in matches
        }


        if len(
            fingerprints
        ) == 1:

            return (
                matches[0],
                "duplicate_same_contract"
            )


        return (
            None,
            "ambiguous_scene_contract"
        )


    return (
        None,
        "scene_contract_missing"
    )


def _target_dimensions(
    vf
):

    if not isinstance(
        vf,
        str
    ):

        return False


    return (
        "1080x1920"
        in vf
        or (
            "1080:1920"
            in vf
            and "crop="
            in vf
        )
    )


def _compare(
    mapped,
    plan,
    validation
):

    branch = mapped.get(
        "branch"
    )


    legacy_vf = mapped.get(
        "vf"
    )


    renderer_mode = plan.get(
        "renderer_mode"
    )


    blockers = []

    warnings = []


    if (
        validation.get(
            "status"
        )
        != "PASS"
    ):

        blockers.append(
            "vi6_filter_invalid"
        )


    # =====================================
    # STILL
    # =====================================

    if branch == "STILL":

        if renderer_mode not in {
            "KEN_BURNS_STILL",
            "STATIC_STILL",
        }:

            blockers.append(
                "still_plan_mode_invalid"
            )


        if not mapped.get(
            "has_zoompan"
        ):

            blockers.append(
                "legacy_still_zoompan_missing"
            )


        if not _target_dimensions(
            legacy_vf
        ):

            blockers.append(
                "legacy_target_dimensions_unknown"
            )


        proposed_vf = plan.get(
            "vf"
        )


        if (
            renderer_mode
            == "KEN_BURNS_STILL"
            and (
                not isinstance(
                    proposed_vf,
                    str
                )
                or "zoompan="
                not in proposed_vf
            )
        ):

            blockers.append(
                "vi6_zoompan_missing"
            )


        if blockers:

            status = "HOLD"


        elif legacy_vf == proposed_vf:

            status = "EXACT_MATCH"


        else:

            status = "SAFE_DIFFERENCE"


            warnings.append(
                "legacy_and_vi6_filters_differ"
            )


    # =====================================
    # VIDEO
    # =====================================

    elif branch == "VIDEO":

        proposed_vf = None


        if (
            renderer_mode
            != "NATIVE_VIDEO_PRESERVE"
        ):

            blockers.append(
                "video_should_preserve_native_motion"
            )


        status = (
            "NATIVE_VIDEO_PRESERVE"
            if not blockers
            else "HOLD"
        )


    else:

        proposed_vf = plan.get(
            "vf"
        )


        blockers.append(
            "unknown_branch"
        )


        status = "HOLD"


    return {

        "status":
            status,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "legacy_vf":
            legacy_vf,

        "proposed_vi6_vf":
            proposed_vf,

        "renderer_mode":
            renderer_mode,

        "legacy_filter_replaced":
            False,

        "command_mutated":
            False,
    }


def shadow_compare(
    command,
    mapped,
    context=None,
    registry=None
):

    context = dict(
        context
        or {}
    )


    if registry is None:

        registry = load_contracts()


    base = {

        "version":
            VERSION,

        "scene":
            mapped.get(
                "scene"
            ),

        "branch":
            mapped.get(
                "branch"
            ),

        "command_fingerprint":
            mapped.get(
                "command_fingerprint"
            ),

        "contract_registry_status":
            registry.get(
                "status"
            ),

        "contract_registry_path":
            registry.get(
                "path"
            ),

        "contract_registry_age_seconds":
            registry.get(
                "age_seconds"
            ),

        "context":
            context,

        "command_mutated":
            False,

        "legacy_filter_replaced":
            False,
    }


    if registry.get(
        "status"
    ) != "READY":

        base.update(
            {

                "status":
                    "HOLD",

                "reason":
                    "contract_registry_"
                    + str(
                        registry.get(
                            "status"
                        )
                    ).lower(),

                "blockers":
                    [
                        "contract_registry_not_ready"
                    ],

                "warnings":
                    [],
            }
        )


        return base


    matched, match_reason = (
        _match_contract(
            mapped,
            registry
        )
    )


    if matched is None:

        base.update(
            {

                "status":
                    "HOLD",

                "reason":
                    match_reason,

                "blockers":
                    [
                        match_reason
                    ],

                "warnings":
                    [],
            }
        )


        return base


    contract = dict(
        matched[
            "contract"
        ]
    )


    # O mapper real é a fonte da duração.
    duration = mapped.get(
        "duration_seconds"
    )


    if (
        duration is None
        or duration <= 0
    ):

        base.update(
            {

                "status":
                    "HOLD",

                "reason":
                    "duration_missing",

                "blockers":
                    [
                        "duration_missing"
                    ],

                "warnings":
                    [],
            }
        )


        return base


    # Força somente a classificação de mídia
    # observada no comando real.
    if (
        mapped.get(
            "branch"
        )
        == "STILL"
    ):

        contract[
            "media_type"
        ] = "STILL"


    elif (
        mapped.get(
            "branch"
        )
        == "VIDEO"
    ):

        contract[
            "media_type"
        ] = "VIDEO"


    plan = compile_plan(
        contract,
        {
            "seconds":
                duration
        }
    )


    validation = validate_filter(
        plan
    )


    comparison = _compare(
        mapped,
        plan,
        validation
    )


    base.update(
        {

            "status":
                comparison[
                    "status"
                ],

            "reason":
                "shadow_comparison_complete",

            "match_reason":
                match_reason,

            "contract_scene":
                matched.get(
                    "scene"
                ),

            "contract_fingerprint":
                matched.get(
                    "fingerprint"
                ),

            "duration_seconds":
                duration,

            "legacy_vf":
                comparison.get(
                    "legacy_vf"
                ),

            "proposed_vi6_vf":
                comparison.get(
                    "proposed_vi6_vf"
                ),

            "renderer_mode":
                comparison.get(
                    "renderer_mode"
                ),

            "filter_validation_status":
                validation.get(
                    "status"
                ),

            "filter_validation_issues":
                validation.get(
                    "issues"
                ),

            "blockers":
                comparison.get(
                    "blockers"
                ),

            "warnings":
                comparison.get(
                    "warnings"
                ),

            "command_mutated":
                False,

            "legacy_filter_replaced":
                False,
        }
    )


    return base


def record(
    result
):

    key = (
        result.get(
            "scene"
        )
    )


    if key is None:

        key = (
            "unknown:"
            + str(
                result.get(
                    "command_fingerprint"
                )
            )
        )


    _EVENTS[
        str(
            key
        )
    ] = dict(
        result
    )


    flush()


def reset():

    _EVENTS.clear()


def summary():

    events = list(
        _EVENTS.values()
    )


    statuses = {}


    for event in events:

        status = str(
            event.get(
                "status"
            )
        )


        statuses[
            status
        ] = (
            statuses.get(
                status,
                0
            )
            + 1
        )


    return {

        "version":
            VERSION,

        "unique_events":
            len(
                events
            ),

        "unique_scenes":
            len(
                {
                    event.get(
                        "scene"
                    )
                    for event in events
                    if event.get(
                        "scene"
                    )
                    is not None
                }
            ),

        "statuses":
            statuses,

        "holds":
            sum(
                1
                for event in events
                if event.get(
                    "status"
                )
                == "HOLD"
            ),

        "command_mutations":
            sum(
                1
                for event in events
                if event.get(
                    "command_mutated"
                )
            ),

        "filter_replacements":
            sum(
                1
                for event in events
                if event.get(
                    "legacy_filter_replaced"
                )
            ),

        "events":
            events,
    }


def flush(
    path=OUTPUT_REPORT
):

    path = Path(
        path
    )


    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    payload = {

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "summary":
            summary(),
    }


    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    return str(
        path
    )


def self_test():

    mapped = {

        "scene":
            2,

        "branch":
            "STILL",

        "duration_seconds":
            4.0,

        "command_fingerprint":
            "abc",

        "has_zoompan":
            True,

        "vf":
            (
                "scale=1200:2133:"
                "force_original_aspect_ratio=increase,"
                "crop=1200:2133,"
                "zoompan=z='1.02':"
                "x='0':y='0':"
                "d=120:s=1080x1920:"
                "fps=30,"
                "setsar=1,"
                "format=yuv420p"
            ),
    }


    contract = {

        "scene":
            2,

        "media_type":
            "STILL",

        "role":
            "CONTEXT",

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


    registry = {

        "status":
            "READY",

        "path":
            "SELFTEST",

        "age_seconds":
            0,

        "contracts":
            [
                {
                    "scene":
                        2,

                    "contract":
                        contract,

                    "fingerprint":
                        "contract1",
                }
            ],
    }


    result = shadow_compare(
        [],
        mapped,
        registry=registry
    )


    assert (
        result[
            "status"
        ]
        in {
            "EXACT_MATCH",
            "SAFE_DIFFERENCE",
        }
    )


    assert (
        result[
            "command_mutated"
        ]
        is False
    )


    assert (
        result[
            "legacy_filter_replaced"
        ]
        is False
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.50 SHADOW COMPARATOR: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Contract Match"
    )
    print(
        "OK VI6 Filter Compilation"
    )
    print(
        "OK Structural Comparison"
    )
    print(
        "OK No Filter Replacement"
    )
    print(
        "OK No Command Mutation"
    )
    print()


if __name__ == "__main__":
    self_test()


# VI6.60 MEGA SHADOW RUNTIME HOOK
_vi650_original_record_vi660 = record


def record(
    result
):

    # Preserve VI6.50 original telemetry first.
    _vi650_original_record_vi660(
        result
    )


    # VI6.60 is strictly observational.
    # Any failure here MUST NOT affect rendering.
    try:

        from vi6_60_runtime import (
            observe as _vi660_observe
        )


        _vi660_observe(
            result
        )


    except Exception:

        pass
