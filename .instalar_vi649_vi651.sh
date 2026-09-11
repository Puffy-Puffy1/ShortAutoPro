#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi649_vi651_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================================"
echo " VI6.49 + VI6.50 + VI6.51"
echo " REAL COMMAND MAP + SHADOW FILTER COMPARISON"
echo "======================================================"
echo


# =====================================================
# 0. BASELINE
# =====================================================

REQUIRED="
video.py
gerar_short.sh
vi6_35_ffmpeg_dry_compiler.py
vi6_38_filter_validator.py
vi6_47_renderer_switch.py
vi6_48_emergency_rollback.py
"

for F in $REQUIRED
do
    if [ ! -f "$F" ]; then
        echo "ERRO: $F não encontrado."
        exit 2
    fi
done


echo "===== BASELINE COMPILE ====="

if ! python -m py_compile \
    video.py \
    vi6_35_ffmpeg_dry_compiler.py \
    vi6_38_filter_validator.py \
    vi6_47_renderer_switch.py \
    vi6_48_emergency_rollback.py
then
    echo "BASELINE FALHOU."
    exit 3
fi

echo "BASELINE=PASS"


# =====================================================
# 1. SAFETY / BACKUP
# =====================================================

VIDEO_HASH_BEFORE="$(
    sha256sum video.py | awk '{print $1}'
)"


cp vi6_47_renderer_switch.py \
   "$BACKDIR/vi6_47_renderer_switch.py"


for F in \
    vi6_49_real_command_mapper.py \
    vi6_50_shadow_filter_comparator.py \
    vi6_51_canary_gate.py \
    testar_vi649_vi651.py
do

    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi

done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.49-6.51"
    echo "======================================"

    cp \
        "$BACKDIR/vi6_47_renderer_switch.py" \
        vi6_47_renderer_switch.py


    for F in \
        vi6_49_real_command_mapper.py \
        vi6_50_shadow_filter_comparator.py \
        vi6_51_canary_gate.py \
        testar_vi649_vi651.py
    do

        if [ -f "$BACKDIR/$F" ]; then
            cp "$BACKDIR/$F" "$F"
        else
            rm -f "$F"
        fi

    done

    echo "Rollback concluído."
}


# =====================================================
# 2. VI6.49 REAL COMMAND MAPPER
# =====================================================

cat > vi6_49_real_command_mapper.py <<'PY'
#!/usr/bin/env python3

import hashlib
import json
import os
import re


VERSION = "6.49"


def _s(value):

    return str(
        value
        if value is not None
        else ""
    )


def _float(value):

    try:
        return float(value)

    except Exception:
        return None


def _arg_value(
    command,
    flag
):

    try:

        index = command.index(
            flag
        )


        if index + 1 < len(
            command
        ):

            return command[
                index + 1
            ]


    except Exception:

        pass


    return None


def _has(
    command,
    flag
):

    try:
        return flag in command

    except Exception:
        return False


def _input_path(
    command
):

    return _arg_value(
        command,
        "-i"
    )


def _output_path(
    command
):

    if not command:
        return None


    # No renderer atual, a saída é o
    # último argumento do comando.
    value = command[-1]


    if isinstance(
        value,
        str
    ):

        return value


    return None


def infer_scene_number(
    output_path
):

    if not output_path:
        return None


    name = os.path.basename(
        str(
            output_path
        )
    )


    patterns = (

        r"(?:cena|scene)[_-]?0*(\d+)",

        r"(?:clip|frame)[_-]?0*(\d+)",

        r"[_-]0*(\d+)(?:\.[A-Za-z0-9]+)?$",
    )


    for pattern in patterns:

        match = re.search(
            pattern,
            name,
            flags=re.IGNORECASE
        )


        if match:

            try:

                number = int(
                    match.group(
                        1
                    )
                )


                if 1 <= number <= 99:
                    return number


            except Exception:
                pass


    return None


def _fps_from_filter(
    vf
):

    if not isinstance(
        vf,
        str
    ):

        return None


    match = re.search(
        r"(?:^|[,:])fps=([0-9]+(?:\.[0-9]+)?)",
        vf
    )


    if not match:
        return None


    return _float(
        match.group(
            1
        )
    )


def _frames(
    command
):

    raw = _arg_value(
        command,
        "-frames:v"
    )


    try:
        return int(raw)

    except Exception:
        return None


def _duration(
    command,
    vf
):

    # Vídeo real possui -t.
    explicit = _float(
        _arg_value(
            command,
            "-t"
        )
    )


    if (
        explicit is not None
        and explicit > 0
    ):

        return (
            explicit,
            "command_t"
        )


    # Foto possui -frames:v + fps no filtro.
    frames = _frames(
        command
    )


    fps = _fps_from_filter(
        vf
    )


    if (
        frames is not None
        and frames > 0
        and fps is not None
        and fps > 0
    ):

        return (
            frames / fps,
            "frames_over_fps"
        )


    return (
        None,
        "unknown"
    )


def _branch(
    command
):

    if (
        _has(
            command,
            "-loop"
        )
        and _arg_value(
            command,
            "-loop"
        )
        == "1"
    ):

        return "STILL"


    if _has(
        command,
        "-stream_loop"
    ):

        return "VIDEO"


    return "UNKNOWN"


def _fingerprint(
    command
):

    payload = json.dumps(
        command,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


    return hashlib.sha256(
        payload.encode(
            "utf-8"
        )
    ).hexdigest()[:16]


def map_command(
    command,
    context=None
):

    context = dict(
        context
        or {}
    )


    if not isinstance(
        command,
        list
    ):

        return {

            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "command_not_list",

            "mutated":
                False,
        }


    vf = _arg_value(
        command,
        "-vf"
    )


    branch = _branch(
        command
    )


    input_path = _input_path(
        command
    )


    output_path = _output_path(
        command
    )


    scene = infer_scene_number(
        output_path
    )


    duration, duration_source = (
        _duration(
            command,
            vf
        )
    )


    fps = _fps_from_filter(
        vf
    )


    result = {

        "version":
            VERSION,

        "status":
            "MAPPED",

        "branch":
            branch,

        "scene":
            scene,

        "input_path":
            input_path,

        "output_path":
            output_path,

        "has_vf":
            isinstance(
                vf,
                str
            ),

        "vf":
            vf,

        "has_zoompan":
            (
                isinstance(
                    vf,
                    str
                )
                and "zoompan="
                in vf
            ),

        "has_scale":
            (
                isinstance(
                    vf,
                    str
                )
                and "scale="
                in vf
            ),

        "has_crop":
            (
                isinstance(
                    vf,
                    str
                )
                and "crop="
                in vf
            ),

        "has_yuv420p":
            (
                isinstance(
                    vf,
                    str
                )
                and "format=yuv420p"
                in vf
            ),

        "frames":
            _frames(
                command
            ),

        "fps":
            fps,

        "duration_seconds":
            (
                round(
                    duration,
                    4
                )
                if duration
                is not None
                else None
            ),

        "duration_source":
            duration_source,

        "codec":
            _arg_value(
                command,
                "-c:v"
            ),

        "preset":
            _arg_value(
                command,
                "-preset"
            ),

        "crf":
            _arg_value(
                command,
                "-crf"
            ),

        "command_fingerprint":
            _fingerprint(
                command
            ),

        "context":
            context,

        "mutated":
            False,
    }


    blockers = []


    if (
        branch
        == "UNKNOWN"
    ):

        blockers.append(
            "unknown_media_branch"
        )


    if not result[
        "has_vf"
    ]:

        blockers.append(
            "vf_missing"
        )


    if (
        branch
        == "STILL"
        and not result[
            "has_zoompan"
        ]
    ):

        blockers.append(
            "still_zoompan_missing"
        )


    if (
        duration is None
        or duration <= 0
    ):

        blockers.append(
            "duration_unknown"
        )


    if blockers:

        result[
            "status"
        ] = "HOLD"


    result[
        "blockers"
    ] = blockers


    return result


def self_test():

    still = [

        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        "/tmp/image.jpg",

        "-vf",
        (
            "scale=1200:2133:"
            "force_original_aspect_ratio=increase,"
            "crop=1200:2133,"
            "zoompan=z='1.02':x='0':y='0':"
            "d=120:s=1080x1920:fps=30,"
            "setsar=1,"
            "format=yuv420p"
        ),

        "-frames:v",
        "120",

        "-an",

        "-c:v",
        "libx264",

        "-preset",
        "fast",

        "-crf",
        "20",

        "-pix_fmt",
        "yuv420p",

        "/tmp/cena_03.mp4",
    ]


    result = map_command(
        still
    )


    assert (
        result[
            "status"
        ]
        == "MAPPED"
    )


    assert (
        result[
            "branch"
        ]
        == "STILL"
    )


    assert (
        result[
            "scene"
        ]
        == 3
    )


    assert abs(
        result[
            "duration_seconds"
        ]
        - 4.0
    ) < .01


    assert (
        result[
            "has_zoompan"
        ]
        is True
    )


    video = [

        "ffmpeg",
        "-y",

        "-stream_loop",
        "-1",

        "-i",
        "/tmp/a.mp4",

        "-t",
        "4.25",

        "-vf",
        (
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "fps=30,"
            "setsar=1,"
            "format=yuv420p"
        ),

        "-an",
        "-c:v",
        "libx264",

        "/tmp/cena_04.mp4",
    ]


    result = map_command(
        video
    )


    assert (
        result[
            "branch"
        ]
        == "VIDEO"
    )


    assert (
        result[
            "scene"
        ]
        == 4
    )


    assert abs(
        result[
            "duration_seconds"
        ]
        - 4.25
    ) < .001


    print()
    print(
        "======================================"
    )
    print(
        " VI6.49 COMMAND MAPPER: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK STILL branch"
    )
    print(
        "OK VIDEO branch"
    )
    print(
        "OK Scene Number"
    )
    print(
        "OK Duration"
    )
    print(
        "OK VF Extraction"
    )
    print(
        "OK Command Fingerprint"
    )
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 3. VI6.50 SHADOW FILTER COMPARATOR
# =====================================================

cat > vi6_50_shadow_filter_comparator.py <<'PY'
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
PY


# =====================================================
# 4. VI6.51 CANARY GATE
# =====================================================

cat > vi6_51_canary_gate.py <<'PY'
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
PY


# =====================================================
# 5. UPGRADE VI6.47 SHADOW OBSERVER
# =====================================================

cat > vi6_47_renderer_switch.py <<'PY'
#!/usr/bin/env python3

import json
import os

from datetime import datetime


from vi6_48_emergency_rollback import (
    resolve_mode,
    trip,
)


VERSION = "6.47-module+6.49-6.50"


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)


LOG = os.path.join(
    BASE,
    "logs",
    "producao",
    "vi6_47_shadow_runtime_latest.json"
)


def _requested_mode():

    return str(
        os.getenv(
            "VI647_RENDERER_MODE",
            "LEGACY"
        )
        or "LEGACY"
    ).strip().upper()


def _find_vf(
    command
):

    try:

        index = command.index(
            "-vf"
        )


        if (
            index + 1
            < len(
                command
            )
        ):

            return (
                index,
                command[
                    index + 1
                ]
            )


    except Exception:

        pass


    return (
        None,
        None
    )


def _legacy_shadow_log(
    command,
    context,
    mapped=None,
    comparison=None
):

    try:

        os.makedirs(
            os.path.dirname(
                LOG
            ),
            exist_ok=True
        )


        vf_index, vf = _find_vf(
            command
        )


        payload = {

            "version":
                VERSION,

            "time":
                datetime.now().isoformat(
                    timespec="seconds"
                ),

            "mode":
                "SHADOW",

            "vf_index":
                vf_index,

            "has_vf":
                vf is not None,

            "has_zoompan":
                (
                    isinstance(
                        vf,
                        str
                    )
                    and "zoompan="
                    in vf
                ),

            "context":
                context
                or {},

            "vi649":
                mapped,

            "vi650":
                comparison,

            "legacy_command_preserved":
                True,

            "command_mutated":
                False,

            "active_renderer_used":
                False,
        }


        with open(
            LOG,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                payload,
                f,
                ensure_ascii=False,
                indent=2
            )


    except Exception:

        pass


def adapt_scene_command(
    command,
    context=None
):

    # Fail closed.
    if not isinstance(
        command,
        list
    ):

        return command


    requested = (
        _requested_mode()
    )


    try:

        mode, reason = resolve_mode(
            requested
        )


    except Exception as exc:

        trip(
            "resolve_mode:"
            + type(
                exc
            ).__name__
        )


        return command


    # =====================================
    # LEGACY
    # =====================================
    #
    # Zero análise obrigatória.
    # Zero mutação.
    # =====================================

    if mode == "LEGACY":

        return command


    # =====================================
    # SHADOW
    # =====================================
    #
    # Analisa o comando REAL.
    # Compila plano VI6.
    # Compara filtros.
    # JAMAIS troca o comando.
    # =====================================

    if mode == "SHADOW":

        mapped = None

        comparison = None


        try:

            from vi6_49_real_command_mapper import (
                map_command
            )


            mapped = map_command(
                command,
                context
            )


        except Exception as exc:

            mapped = {

                "status":
                    "HOLD",

                "reason":
                    (
                        "vi649_exception:"
                        + type(
                            exc
                        ).__name__
                    ),
            }


        try:

            if (
                mapped
                and mapped.get(
                    "status"
                )
                == "MAPPED"
            ):

                from vi6_50_shadow_filter_comparator import (
                    shadow_compare,
                    record,
                )


                comparison = shadow_compare(
                    command,
                    mapped,
                    context
                )


                record(
                    comparison
                )


        except Exception as exc:

            comparison = {

                "status":
                    "HOLD",

                "reason":
                    (
                        "vi650_exception:"
                        + type(
                            exc
                        ).__name__
                    ),

                "command_mutated":
                    False,

                "legacy_filter_replaced":
                    False,
            }


        _legacy_shadow_log(
            command,
            context,
            mapped,
            comparison
        )


        return command


    # ACTIVE continua bloqueado
    # pelo VI6.48.
    return command


def self_test():

    still = [

        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        "x.jpg",

        "-vf",
        (
            "scale=1200:2133,"
            "crop=1200:2133,"
            "zoompan=z='1.02':"
            "d=120:s=1080x1920:fps=30,"
            "format=yuv420p"
        ),

        "-frames:v",
        "120",

        "-c:v",
        "libx264",

        "cena_01.mp4",
    ]


    old = os.environ.get(
        "VI647_RENDERER_MODE"
    )


    try:

        # LEGACY
        os.environ[
            "VI647_RENDERER_MODE"
        ] = "LEGACY"


        before = list(
            still
        )


        result = adapt_scene_command(
            still
        )


        assert result is still

        assert still == before


        # ACTIVE continua LEGACY.
        os.environ[
            "VI647_RENDERER_MODE"
        ] = "ACTIVE"


        result = adapt_scene_command(
            still
        )


        assert result is still

        assert still == before


    finally:

        if old is None:

            os.environ.pop(
                "VI647_RENDERER_MODE",
                None
            )

        else:

            os.environ[
                "VI647_RENDERER_MODE"
            ] = old


    print()
    print(
        "======================================"
    )
    print(
        " VI6.47 SHADOW OBSERVER: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK LEGACY preserved"
    )
    print(
        "OK ACTIVE still blocked"
    )
    print(
        "OK Command identity preserved"
    )
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 6. INTEGRATION TEST
# =====================================================

cat > testar_vi649_vi651.py <<'PY'
#!/usr/bin/env python3

import os


from vi6_49_real_command_mapper import (
    map_command
)

from vi6_50_shadow_filter_comparator import (
    shadow_compare
)

from vi6_51_canary_gate import (
    evaluate
)

from vi6_47_renderer_switch import (
    adapt_scene_command
)


command = [

    "ffmpeg",
    "-y",

    "-loop",
    "1",

    "-i",
    "image.jpg",

    "-vf",
    (
        "scale=1200:2133:"
        "force_original_aspect_ratio=increase,"
        "crop=1200:2133,"
        "zoompan=z='1.02':x='0':y='0':"
        "d=120:s=1080x1920:fps=30,"
        "setsar=1,"
        "format=yuv420p"
    ),

    "-frames:v",
    "120",

    "-c:v",
    "libx264",

    "cena_07.mp4",
]


mapped = map_command(
    command
)


assert (
    mapped[
        "status"
    ]
    == "MAPPED"
)


assert (
    mapped[
        "scene"
    ]
    == 7
)


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
                    7,

                "fingerprint":
                    "contract7",

                "contract":
                    {
                        "scene":
                            7,

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
                                    .47,

                                "start_y":
                                    .50,

                                "end_x":
                                    .53,

                                "end_y":
                                    .50,
                            },
                    },
            }
        ],
}


comparison = shadow_compare(
    command,
    mapped,
    registry=registry
)


assert (
    comparison[
        "status"
    ]
    in {
        "EXACT_MATCH",
        "SAFE_DIFFERENCE",
    }
)


assert (
    comparison[
        "legacy_filter_replaced"
    ]
    is False
)


# =====================================
# LEGACY identity test
# =====================================

old = os.environ.get(
    "VI647_RENDERER_MODE"
)


try:

    os.environ[
        "VI647_RENDERER_MODE"
    ] = "LEGACY"


    snapshot = list(
        command
    )


    result = adapt_scene_command(
        command
    )


    assert result is command

    assert command == snapshot


finally:

    if old is None:

        os.environ.pop(
            "VI647_RENDERER_MODE",
            None
        )

    else:

        os.environ[
            "VI647_RENDERER_MODE"
        ] = old


# =====================================
# CANARY GATE synthetic test
# =====================================

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
                    "SAFE_DIFFERENCE",
            }

            for n in range(
                1,
                13
            )
        ],
}


gate = evaluate(
    shadow,

    {
        "status":
            "CERTIFIED",

        "temporary_video_deleted":
            True,
    },

    {
        "next_stage_allowed":
            True
    }
)


assert (
    gate[
        "status"
    ]
    == "READY_FOR_CANARY_PATCH"
)


assert (
    gate[
        "active_canary_authorized"
    ]
    is False
)


print()
print(
    "======================================"
)
print(
    " VI6.49-6.51 INTEGRATION: PASS"
)
print(
    "======================================"
)
print(
    "REAL COMMAND PARSING=PASS"
)
print(
    "SHADOW FILTER COMPARISON=PASS"
)
print(
    "LEGACY COMMAND IDENTITY=PASS"
)
print(
    "CANARY GATE LOGIC=PASS"
)
print(
    "ACTIVE CANARY=LOCKED"
)
print(
    "FFMPEG EXECUTED=0"
)
print(
    "VIDEO GENERATED=0"
)
PY


# =====================================================
# 7. COMPILE
# =====================================================

echo
echo "===== FULL COMPILE ====="

if ! python -m py_compile \
    vi6_49_real_command_mapper.py \
    vi6_50_shadow_filter_comparator.py \
    vi6_51_canary_gate.py \
    vi6_47_renderer_switch.py \
    testar_vi649_vi651.py \
    video.py
then

    rollback
    exit 1
fi

echo "PYTHON COMPILE=PASS"


# =====================================================
# 8. SELF TESTS
# =====================================================

echo
echo "===== VI6.49 ====="

python vi6_49_real_command_mapper.py || {
    rollback
    exit 1
}


echo
echo "===== VI6.50 ====="

python vi6_50_shadow_filter_comparator.py || {
    rollback
    exit 1
}


echo
echo "===== VI6.51 ====="

python vi6_51_canary_gate.py || {
    rollback
    exit 1
}


echo
echo "===== VI6.47 REGRESSION ====="

python vi6_47_renderer_switch.py || {
    rollback
    exit 1
}


echo
echo "===== INTEGRATION ====="

python testar_vi649_vi651.py || {
    rollback
    exit 1
}


# =====================================================
# 9. REAL CONTRACT REGISTRY DIAGNOSTIC
# =====================================================

echo
echo "===== REAL VI6.30 CONTRACT REGISTRY ====="

python - <<'PY'
from vi6_50_shadow_filter_comparator import (
    load_contracts
)


result = load_contracts()


print(
    "STATUS:",
    result.get(
        "status"
    )
)

print(
    "PATH:",
    result.get(
        "path"
    )
)

print(
    "AGE SECONDS:",
    result.get(
        "age_seconds"
    )
)

print(
    "CONTRACTS FOUND:",
    len(
        result.get(
            "contracts",
            []
        )
    )
)


scenes = sorted(
    {
        item.get(
            "scene"
        )
        for item in result.get(
            "contracts",
            []
        )
        if isinstance(
            item.get(
                "scene"
            ),
            int
        )
    }
)


print(
    "SCENES WITH CONTRACT:",
    scenes
)
PY


# =====================================================
# 10. REAL CANARY GATE
# =====================================================

echo
echo "===== VI6.51 CURRENT REAL STATUS ====="

python \
    vi6_51_canary_gate.py \
    --real


# =====================================================
# 11. VIDEO.PY MUST REMAIN UNCHANGED
# =====================================================

VIDEO_HASH_AFTER="$(
    sha256sum video.py | awk '{print $1}'
)"


echo
echo "===== VIDEO.PY HASH ====="

echo "BEFORE=$VIDEO_HASH_BEFORE"
echo "AFTER =$VIDEO_HASH_AFTER"


if [ "$VIDEO_HASH_BEFORE" != "$VIDEO_HASH_AFTER" ]; then

    echo
    echo "ERRO: video.py foi alterado."

    rollback
    exit 1
fi


echo "VIDEO.PY UNCHANGED=YES"


# =====================================================
# 12. BASH / RELEASE
# =====================================================

echo
echo "===== BASH CHECK ====="

bash -n gerar_short.sh || {
    rollback
    exit 1
}

echo "BASH STATUS=0"


echo
echo "===== RELEASE CHECK ====="

./release_check.sh || {
    rollback
    exit 1
}


# =====================================================
# FINAL
# =====================================================

echo
echo "======================================================"
echo " VI6.49 + VI6.50 + VI6.51 INSTALADOS"
echo "======================================================"
echo
echo "OK Real FFmpeg Command Mapper"
echo "OK STILL / VIDEO Branch Detection"
echo "OK Real Scene Number Detection"
echo "OK Real Duration Detection"
echo "OK Real VF Extraction"
echo "OK Command Fingerprinting"
echo "OK VI6.30 Contract Registry Reader"
echo "OK Scene-to-Contract Matching"
echo "OK VI6 Filter Shadow Compilation"
echo "OK Legacy-vs-VI6 Comparison"
echo "OK Native Video Preservation"
echo "OK 12-Scene Canary Gate"
echo "OK Zero Mutation Requirement"
echo "OK Zero Filter Replacement Requirement"
echo "OK VI6.45 Certification preserved"
echo
echo "VIDEO.PY MODIFIED=NAO"
echo "DEFAULT RENDERER=LEGACY"
echo "SHADOW FILTER REPLACEMENT=NAO"
echo "ACTIVE RENDERER=BLOCKED"
echo "ACTIVE CANARY AUTHORIZED=NAO"
echo
echo "FFMPEG EXECUTADO=NAO"
echo "VIDEO GERADO=NAO"
echo "API CALLS=0"
echo "DOWNLOADS=0"
echo
echo "FUTURE SHADOW REPORT:"
echo "logs/producao/vi6_50_shadow_compare_latest.json"
echo
echo "CANARY GATE:"
echo "logs/producao/vi6_51_canary_gate_latest.json"
echo
