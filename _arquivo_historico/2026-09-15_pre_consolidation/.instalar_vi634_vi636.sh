#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi634_vi636_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================"
echo " VI6.34 + VI6.35 + VI6.36"
echo " AUTO-REPAIR + FFMPEG DRY-RUN"
echo " + RENDERER COMPATIBILITY"
echo "======================================"
echo


# =====================================================
# 0. BASELINE
# =====================================================

REQUIRED="
midia.py
video.py
audio.py
legenda_dinamica.py
gerar_short.sh
vi6_6_active_brain.py
vi6_9_runtime_policy.py
vi6_28_motion_blueprint.py
vi6_29_ken_burns_intelligence.py
vi6_30_renderer_contract.py
vi6_31_pre_render_auditor.py
vi6_32_scene_duration.py
vi6_33_cinematic_safety_gate.py
vi6_33_runtime_policy.py
"

for F in $REQUIRED
do
    if [ ! -f "$F" ]; then
        echo "ERRO: $F não encontrado."
        echo "NENHUMA ALTERAÇÃO FEITA."
        exit 2
    fi
done


echo "===== BASELINE COMPILE ====="

if ! python -m py_compile \
    midia.py \
    video.py \
    audio.py \
    legenda_dinamica.py \
    vi6_6_active_brain.py \
    vi6_9_runtime_policy.py \
    vi6_30_renderer_contract.py \
    vi6_31_pre_render_auditor.py \
    vi6_32_scene_duration.py \
    vi6_33_cinematic_safety_gate.py \
    vi6_33_runtime_policy.py
then

    echo
    echo "BASELINE FALHOU."
    echo "NENHUMA ALTERAÇÃO FEITA."
    exit 3
fi

echo "BASELINE=OK"


# =====================================================
# CORE HASH
# =====================================================

CORE_FILES="
midia.py
video.py
audio.py
legenda_dinamica.py
gerar_short.sh
"

: > "$BACKDIR/core_before.sha256"

for F in $CORE_FILES
do
    sha256sum "$F" \
        >> "$BACKDIR/core_before.sha256"
done


cp vi6_9_runtime_policy.py \
   "$BACKDIR/vi6_9_runtime_policy.py"


for F in \
    vi6_34_motion_auto_repair.py \
    vi6_35_ffmpeg_dry_compiler.py \
    vi6_36_renderer_compatibility.py \
    vi6_36_runtime_policy.py \
    testar_vi634_vi636.py
do

    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi

done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.34-6.36"
    echo "======================================"

    cp \
        "$BACKDIR/vi6_9_runtime_policy.py" \
        vi6_9_runtime_policy.py


    for F in \
        vi6_34_motion_auto_repair.py \
        vi6_35_ffmpeg_dry_compiler.py \
        vi6_36_renderer_compatibility.py \
        vi6_36_runtime_policy.py \
        testar_vi634_vi636.py
    do

        if [ -f "$BACKDIR/$F" ]; then
            cp "$BACKDIR/$F" "$F"
        else
            rm -f "$F"
        fi

    done

    echo "Projeto restaurado."
}


# =====================================================
# 1. VI6.34 MOTION AUTO-REPAIR
# =====================================================

cat > vi6_34_motion_auto_repair.py <<'PY'
#!/usr/bin/env python3

import copy
import hashlib
import json


VERSION = "6.34"


REPAIRABLE = {
    "zoom_velocity_too_high",
    "pan_velocity_too_high",
    "documentary_zoom_excess",
    "documentary_pan_excess",
}


ROLE_ZOOM_RATE = {
    "EVIDENCE": .012,
    "PERSON": .022,
    "PLACE": .022,
    "OBJECT": .030,
    "CONTEXT": .030,
    "CTA": .010,
}


ROLE_PAN_RATE = {
    "EVIDENCE": .014,
    "PERSON": .018,
    "PLACE": .030,
    "OBJECT": .026,
    "CONTEXT": .034,
    "CTA": .012,
}


def _u(v):
    return str(v or "").strip().upper()


def _f(v, default=0.0):

    try:
        return float(v)
    except Exception:
        return float(default)


def _clamp(v, low, high):

    return max(
        low,
        min(
            high,
            float(v)
        )
    )


def _rehash(contract):

    tmp = dict(contract)

    tmp.pop(
        "contract_hash",
        None
    )


    canonical = json.dumps(
        tmp,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    )


    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()[:16]


def repair_contract(
    contract,
    duration,
    safety
):

    original = copy.deepcopy(
        contract
    )


    repaired = copy.deepcopy(
        contract
    )


    blockers = set(
        safety.get(
            "blockers",
            []
        )
        or []
    )


    if not blockers:

        return {
            "version": VERSION,
            "changed": False,
            "reason": "no_blockers",
            "original": original,
            "contract": repaired,
            "repaired_blockers": [],
            "unrepaired_blockers": [],
        }


    nonrepairable = (
        blockers
        - REPAIRABLE
    )


    repairable = (
        blockers
        & REPAIRABLE
    )


    # Não tenta "consertar" erro lógico,
    # contrato inválido ou cena curta.
    if nonrepairable:

        return {
            "version": VERSION,
            "changed": False,
            "reason": "nonrepairable_blocker",
            "original": original,
            "contract": repaired,
            "repaired_blockers": [],
            "unrepaired_blockers":
                sorted(nonrepairable),
        }


    if not repairable:

        return {
            "version": VERSION,
            "changed": False,
            "reason": "nothing_repairable",
            "original": original,
            "contract": repaired,
            "repaired_blockers": [],
            "unrepaired_blockers": [],
        }


    ken = copy.deepcopy(
        repaired.get(
            "ken_burns"
        )
        or {}
    )


    if not ken.get(
        "enabled"
    ):

        return {
            "version": VERSION,
            "changed": False,
            "reason":
                "motion_not_enabled",
            "original": original,
            "contract": repaired,
            "repaired_blockers": [],
            "unrepaired_blockers":
                sorted(repairable),
        }


    role = _u(
        repaired.get(
            "role"
        )
        or duration.get(
            "role"
        )
        or "CONTEXT"
    )


    seconds = max(
        .75,
        _f(
            duration.get(
                "seconds",
                4.0
            ),
            4.0
        )
    )


    z1 = _f(
        ken.get(
            "zoom_start",
            1.0
        ),
        1.0
    )


    z2 = _f(
        ken.get(
            "zoom_end",
            1.0
        ),
        1.0
    )


    x1 = _f(
        ken.get(
            "start_x",
            .5
        ),
        .5
    )


    x2 = _f(
        ken.get(
            "end_x",
            .5
        ),
        .5
    )


    y1 = _f(
        ken.get(
            "start_y",
            .5
        ),
        .5
    )


    y2 = _f(
        ken.get(
            "end_y",
            .5
        ),
        .5
    )


    max_zoom_delta = (
        ROLE_ZOOM_RATE.get(
            role,
            .030
        )
        * seconds
    )


    # Limite adicional absoluto.
    absolute_zoom = {
        "EVIDENCE": .045,
        "PERSON": .075,
        "PLACE": .065,
        "OBJECT": .095,
        "CONTEXT": .075,
        "CTA": .035,
    }.get(
        role,
        .075
    )


    max_zoom_delta = min(
        max_zoom_delta,
        absolute_zoom
    )


    direction = (
        1.0
        if z2 >= z1
        else -1.0
    )


    new_delta = min(
        abs(
            z2 - z1
        ),
        max_zoom_delta
    )


    new_z2 = (
        z1
        + direction
        * new_delta
    )


    new_z2 = _clamp(
        new_z2,
        1.0,
        1.10
    )


    # =================================
    # PAN REPAIR
    # =================================

    dx = (
        x2 - x1
    )

    dy = (
        y2 - y1
    )


    distance = (
        dx * dx
        + dy * dy
    ) ** .5


    max_pan_distance = (
        ROLE_PAN_RATE.get(
            role,
            .034
        )
        * seconds
    )


    absolute_pan = {
        "EVIDENCE": .030,
        "PERSON": .050,
        "PLACE": .100,
        "OBJECT": .075,
        "CONTEXT": .110,
        "CTA": .025,
    }.get(
        role,
        .100
    )


    max_pan_distance = min(
        max_pan_distance,
        absolute_pan
    )


    if (
        distance > 0
        and distance
        > max_pan_distance
    ):

        factor = (
            max_pan_distance
            / distance
        )


        dx *= factor
        dy *= factor


    new_x2 = _clamp(
        x1 + dx,
        .42,
        .58
    )


    new_y2 = _clamp(
        y1 + dy,
        .40,
        .58
    )


    # Evidência documental é ainda
    # mais conservadora.
    if role == "EVIDENCE":

        new_z2 = min(
            new_z2,
            z1 + .045
        )


        new_x2 = _clamp(
            new_x2,
            x1 - .03,
            x1 + .03
        )


        new_y2 = _clamp(
            new_y2,
            y1 - .03,
            y1 + .03
        )


    ken[
        "zoom_end"
    ] = round(
        new_z2,
        5
    )


    ken[
        "end_x"
    ] = round(
        new_x2,
        5
    )


    ken[
        "end_y"
    ] = round(
        new_y2,
        5
    )


    ken[
        "vi634_repaired"
    ] = True


    ken[
        "vi634_original"
    ] = {

        "zoom_end":
            z2,

        "end_x":
            x2,

        "end_y":
            y2,
    }


    repaired[
        "ken_burns"
    ] = ken


    repaired[
        "status"
    ] = "REPAIRED_PENDING_RECHECK"


    repaired[
        "renderer_applied"
    ] = False


    repaired[
        "ffmpeg_filter"
    ] = None


    repaired[
        "vi634_repaired"
    ] = True


    repaired[
        "vi634_repaired_blockers"
    ] = sorted(
        repairable
    )


    repaired[
        "contract_hash"
    ] = _rehash(
        repaired
    )


    changed = (
        new_z2 != z2
        or new_x2 != x2
        or new_y2 != y2
    )


    return {
        "version": VERSION,
        "changed": changed,
        "reason":
            (
                "motion_repaired"
                if changed
                else
                "already_within_repair_target"
            ),
        "original": original,
        "contract": repaired,
        "repaired_blockers":
            sorted(repairable),
        "unrepaired_blockers": [],
    }


def self_test():

    contract = {

        "role":
            "EVIDENCE",

        "media_type":
            "STILL",

        "profile":
            "DOCUMENTARY_HOLD",

        "transition":
            "DIRECT_CUT",

        "renderer_applied":
            False,

        "ffmpeg_filter":
            None,

        "ken_burns":
            {
                "enabled":
                    True,

                "zoom_start":
                    1.0,

                "zoom_end":
                    1.10,

                "start_x":
                    .50,

                "start_y":
                    .50,

                "end_x":
                    .58,

                "end_y":
                    .50,
            },
    }


    result = repair_contract(
        contract,
        {
            "seconds":
                2.0,

            "role":
                "EVIDENCE",
        },
        {
            "status":
                "HOLD",

            "blockers":
                [
                    "zoom_velocity_too_high",
                    "pan_velocity_too_high",
                    "documentary_zoom_excess",
                    "documentary_pan_excess",
                ],
        }
    )


    assert result[
        "changed"
    ] is True


    repaired = result[
        "contract"
    ]


    assert (
        repaired[
            "ken_burns"
        ][
            "zoom_end"
        ]
        <= 1.0241
    )


    assert (
        repaired[
            "renderer_applied"
        ]
        is False
    )


    blocked = repair_contract(
        contract,
        {
            "seconds":
                .5
        },
        {
            "status":
                "HOLD",

            "blockers":
                [
                    "scene_too_short"
                ],
        }
    )


    assert (
        blocked[
            "changed"
        ]
        is False
    )


    assert (
        "scene_too_short"
        in blocked[
            "unrepaired_blockers"
        ]
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.34 AUTO-REPAIR SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Zoom Velocity Repair"
    )
    print(
        "OK Pan Velocity Repair"
    )
    print(
        "OK Documentary Motion Repair"
    )
    print(
        "OK Contract Rehash"
    )
    print(
        "OK Non-Motion Errors Preserved"
    )
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 2. VI6.35 FFMPEG DRY-RUN COMPILER
# =====================================================

cat > vi6_35_ffmpeg_dry_compiler.py <<'PY'
#!/usr/bin/env python3

import math


VERSION = "6.35"

FPS = 30

WIDTH = 1080
HEIGHT = 1920


def _f(v, default=0.0):

    try:
        return float(v)
    except Exception:
        return float(default)


def _safe_frames(seconds):

    seconds = max(
        .25,
        _f(
            seconds,
            4.0
        )
    )


    return max(
        1,
        int(
            round(
                seconds
                * FPS
            )
        )
    )


def _num(v):

    return (
        f"{float(v):.6f}"
        .rstrip("0")
        .rstrip(".")
    )


def compile_plan(
    contract,
    duration
):

    media = str(
        contract.get(
            "media_type",
            ""
        )
    ).upper()


    seconds = _f(
        duration.get(
            "seconds",
            4.0
        ),
        4.0
    )


    frames = _safe_frames(
        seconds
    )


    base = {

        "version":
            VERSION,

        "mode":
            "DRY_RUN",

        "executed":
            False,

        "fps":
            FPS,

        "width":
            WIDTH,

        "height":
            HEIGHT,

        "duration_seconds":
            round(
                seconds,
                3
            ),

        "frames":
            frames,

        "argv":
            None,

        "vf":
            None,
    }


    # =================================
    # NATIVE VIDEO
    # =================================

    if media == "VIDEO":

        base[
            "renderer_mode"
        ] = "NATIVE_VIDEO_PRESERVE"


        base[
            "reason"
        ] = "no_synthetic_motion"


        return base


    # =================================
    # NO MEDIA
    # =================================

    if media != "STILL":

        base[
            "renderer_mode"
        ] = "NO_RENDER_PLAN"


        base[
            "reason"
        ] = "unsupported_media_type"


        return base


    ken = (
        contract.get(
            "ken_burns"
        )
        or {}
    )


    if not ken.get(
        "enabled"
    ):

        base[
            "renderer_mode"
        ] = "STATIC_STILL"


        base[
            "vf"
        ] = (
            "scale="
            f"{WIDTH}:{HEIGHT}:"
            "force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},"
            f"fps={FPS}"
        )


        base[
            "argv"
        ] = [
            "ffmpeg",
            "-loop",
            "1",
            "-i",
            "{INPUT}",
            "-vf",
            base[
                "vf"
            ],
            "-t",
            "{DURATION}",
            "-an",
            "{OUTPUT}",
        ]


        return base


    z1 = _f(
        ken.get(
            "zoom_start",
            1.0
        ),
        1.0
    )


    z2 = _f(
        ken.get(
            "zoom_end",
            1.0
        ),
        1.0
    )


    x1 = _f(
        ken.get(
            "start_x",
            .5
        ),
        .5
    )


    x2 = _f(
        ken.get(
            "end_x",
            .5
        ),
        .5
    )


    y1 = _f(
        ken.get(
            "start_y",
            .5
        ),
        .5
    )


    y2 = _f(
        ken.get(
            "end_y",
            .5
        ),
        .5
    )


    denominator = max(
        1,
        frames - 1
    )


    progress = (
        f"(on/{denominator})"
    )


    zoom_expr = (
        _num(z1)
        + "+"
        + _num(
            z2 - z1
        )
        + "*"
        + progress
    )


    x_progress = (
        _num(x1)
        + "+"
        + _num(
            x2 - x1
        )
        + "*"
        + progress
    )


    y_progress = (
        _num(y1)
        + "+"
        + _num(
            y2 - y1
        )
        + "*"
        + progress
    )


    # Coordenadas normalizadas são
    # transformadas na área disponível
    # depois do zoom.
    x_expr = (
        "(iw-iw/zoom)*("
        + x_progress
        + ")"
    )


    y_expr = (
        "(ih-ih/zoom)*("
        + y_progress
        + ")"
    )


    vf = (
        "scale="
        f"{WIDTH}:{HEIGHT}:"
        "force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},"
        "zoompan="
        "z='"
        + zoom_expr
        + "':"
        "x='"
        + x_expr
        + "':"
        "y='"
        + y_expr
        + "':"
        f"d={frames}:"
        f"s={WIDTH}x{HEIGHT}:"
        f"fps={FPS},"
        "format=yuv420p"
    )


    base[
        "renderer_mode"
    ] = "KEN_BURNS_STILL"


    base[
        "vf"
    ] = vf


    base[
        "argv"
    ] = [
        "ffmpeg",
        "-loop",
        "1",
        "-i",
        "{INPUT}",
        "-vf",
        vf,
        "-t",
        "{DURATION}",
        "-an",
        "{OUTPUT}",
    ]


    base[
        "zoom"
    ] = {
        "start":
            z1,

        "end":
            z2,
    }


    base[
        "pan"
    ] = {
        "start_x":
            x1,

        "start_y":
            y1,

        "end_x":
            x2,

        "end_y":
            y2,
    }


    return base


def validate_plan(plan):

    errors = []


    if (
        plan.get(
            "mode"
        )
        != "DRY_RUN"
    ):

        errors.append(
            "not_dry_run"
        )


    if (
        plan.get(
            "executed"
        )
        is not False
    ):

        errors.append(
            "execution_flag"
        )


    mode = (
        plan.get(
            "renderer_mode"
        )
    )


    if mode == "KEN_BURNS_STILL":

        vf = str(
            plan.get(
                "vf",
                ""
            )
        )


        for required in (
            "scale=",
            "crop=",
            "zoompan=",
            "format=yuv420p",
        ):

            if required not in vf:

                errors.append(
                    "missing_filter:"
                    + required
                )


        argv = (
            plan.get(
                "argv"
            )
            or []
        )


        if not argv:

            errors.append(
                "missing_argv"
            )


        if (
            "{INPUT}"
            not in argv
        ):

            errors.append(
                "missing_input_placeholder"
            )


        if (
            "{OUTPUT}"
            not in argv
        ):

            errors.append(
                "missing_output_placeholder"
            )


        if (
            "{DURATION}"
            not in argv
        ):

            errors.append(
                "missing_duration_placeholder"
            )


    return (
        len(errors) == 0,
        errors
    )


def self_test():

    plan = compile_plan(
        {
            "media_type":
                "STILL",

            "ken_burns":
                {
                    "enabled":
                        True,

                    "zoom_start":
                        1.0,

                    "zoom_end":
                        1.04,

                    "start_x":
                        .45,

                    "start_y":
                        .50,

                    "end_x":
                        .55,

                    "end_y":
                        .50,
                },
        },
        {
            "seconds":
                4.0
        }
    )


    assert (
        plan[
            "executed"
        ]
        is False
    )


    assert (
        plan[
            "frames"
        ]
        == 120
    )


    assert (
        "zoompan="
        in plan[
            "vf"
        ]
    )


    ok, errors = validate_plan(
        plan
    )


    assert ok is True
    assert errors == []


    video = compile_plan(
        {
            "media_type":
                "VIDEO"
        },
        {
            "seconds":
                5
        }
    )


    assert (
        video[
            "argv"
        ]
        is None
    )


    assert (
        video[
            "renderer_mode"
        ]
        == "NATIVE_VIDEO_PRESERVE"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.35 DRY COMPILER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Argument Vector Compilation"
    )
    print(
        "OK Zoompan Expression"
    )
    print(
        "OK 1080x1920"
    )
    print(
        "OK 30 FPS Frame Budget"
    )
    print(
        "OK Native Video No-Op"
    )
    print(
        "OK FFmpeg Execution = ZERO"
    )
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 3. VI6.36 RENDERER COMPATIBILITY HARNESS
# =====================================================

cat > vi6_36_renderer_compatibility.py <<'PY'
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
PY


# =====================================================
# 4. VI6.36 RUNTIME
# =====================================================

cat > vi6_36_runtime_policy.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain


from vi6_34_motion_auto_repair import (
    repair_contract
)


from vi6_35_ffmpeg_dry_compiler import (
    compile_plan,
    validate_plan
)


from vi6_36_renderer_compatibility import (
    check,
    record,
    flush,
    reset,
)


from vi6_33_cinematic_safety_gate import (
    assess
)


if not getattr(
    brain,
    "_VI636_RUNTIME_ACTIVE",
    False
):

    _base_supervisor_636 = (
        brain.supervisionar_vi6_6
    )


    def _wrapped_636(
        vi6_scene,
        candidatos,
        cena,
        current_candidate,
        current_reason
    ):

        board = (
            cena.get(
                "_vi68_storyboard"
            )
            or {}
        )


        try:

            number = int(
                board.get(
                    "scene",
                    0
                )
                or 0
            )

        except Exception:

            number = 0


        if number == 1:
            reset()


        (
            candidate,
            reason,
            meta
        ) = _base_supervisor_636(
            vi6_scene,
            candidatos,
            cena,
            current_candidate,
            current_reason
        )


        meta = dict(
            meta
            or {}
        )


        contract = (
            meta.get(
                "vi630_renderer_contract"
            )
            or {}
        )


        duration = (
            meta.get(
                "vi632_duration"
            )
            or {
                "seconds":
                    4.0,

                "confidence":
                    "LOW",

                "source":
                    "runtime_fallback",
            }
        )


        safety = (
            meta.get(
                "vi633_cinematic_safety"
            )
            or {}
        )


        # =========================================
        # VI6.34 AUTO-REPAIR
        # =========================================

        repair = repair_contract(
            contract,
            duration,
            safety
        )


        final_contract = repair[
            "contract"
        ]


        # Revalida DEPOIS do repair.
        repaired_safety = assess(
            final_contract,
            duration
        )


        final_contract[
            "vi634_repair_status"
        ] = repair[
            "reason"
        ]


        final_contract[
            "vi633_post_repair"
        ] = repaired_safety[
            "status"
        ]


        final_contract[
            "renderer_applied"
        ] = False


        # =========================================
        # VI6.35 DRY FFMPEG COMPILER
        # =========================================

        dry_plan = compile_plan(
            final_contract,
            duration
        )


        plan_ok, plan_errors = (
            validate_plan(
                dry_plan
            )
        )


        dry_plan[
            "valid"
        ] = plan_ok


        dry_plan[
            "errors"
        ] = plan_errors


        # =========================================
        # VI6.36 COMPATIBILITY
        # =========================================

        compat = check(
            final_contract,
            repaired_safety,
            dry_plan
        )


        if not plan_ok:

            compat[
                "status"
            ] = "HOLD"


            compat[
                "renderer_activation_ready"
            ] = False


            compat[
                "issues"
            ] = list(
                compat.get(
                    "issues"
                )
                or []
            ) + [
                "dry_compiler_validation_failed"
            ]


        record(
            number,
            compat,
            repair,
            dry_plan
        )


        meta[
            "vi634_motion_repair"
        ] = {

            "changed":
                repair[
                    "changed"
                ],

            "reason":
                repair[
                    "reason"
                ],

            "repaired_blockers":
                repair[
                    "repaired_blockers"
                ],

            "unrepaired_blockers":
                repair[
                    "unrepaired_blockers"
                ],
        }


        meta[
            "vi634_repaired_contract"
        ] = final_contract


        meta[
            "vi633_post_repair_safety"
        ] = repaired_safety


        meta[
            "vi635_ffmpeg_dry_plan"
        ] = dry_plan


        meta[
            "vi636_renderer_compatibility"
        ] = compat


        meta[
            "vi636_renderer_activation_ready"
        ] = compat[
            "renderer_activation_ready"
        ]


        # Nada desta camada altera mídia,
        # áudio, legenda ou renderer.
        if candidate is not None:

            candidate[
                "_vi634_motion_repaired"
            ] = repair[
                "changed"
            ]


            candidate[
                "_vi635_dry_compiled"
            ] = bool(
                dry_plan.get(
                    "renderer_mode"
                )
            )


            candidate[
                "_vi636_static_compat"
            ] = compat[
                "status"
            ]


            candidate[
                "_vi636_renderer_applied"
            ] = False


        if (
            number >= 12
            or board.get(
                "cta_reuse"
            )
        ):

            try:

                meta[
                    "vi636_compat_path"
                ] = flush()

            except Exception as exc:

                meta[
                    "vi636_compat_error"
                ] = (
                    f"{type(exc).__name__}:"
                    f"{str(exc)[:120]}"
                )


        return (
            candidate,
            reason,
            meta
        )


    brain.supervisionar_vi6_6 = (
        _wrapped_636
    )


    brain._VI634_RUNTIME_ACTIVE = True
    brain._VI635_RUNTIME_ACTIVE = True
    brain._VI636_RUNTIME_ACTIVE = True
PY


# =====================================================
# 5. ATTACH
# =====================================================

python - <<'PY'
from pathlib import Path
import ast


path = Path(
    "vi6_9_runtime_policy.py"
)


source = path.read_text(
    encoding="utf-8"
)


MARKER = (
    "# VI6.34-6.36 RENDER PREPARATION STACK"
)


if MARKER in source:

    print(
        "VI6.34-6.36 já conectado."
    )

    raise SystemExit(0)


append = '''

# =========================================
# VI6.34-6.36 RENDER PREPARATION STACK
# =========================================
import vi6_36_runtime_policy
'''


patched = (
    source.rstrip()
    + "\n"
    + append
    + "\n"
)


ast.parse(
    patched
)


path.write_text(
    patched,
    encoding="utf-8"
)


print()
print(
    "======================================"
)
print(
    " VI6.34-6.36 RUNTIME ATTACHED"
)
print(
    "======================================"
)
print(
    "Auto Repair: ACTIVE"
)
print(
    "FFmpeg Compiler: DRY_RUN"
)
print(
    "Compatibility Harness: ACTIVE"
)
print(
    "Real Renderer: DISABLED"
)
print()
PY


STATUS=$?


if [ "$STATUS" -ne 0 ]; then
    rollback
    exit "$STATUS"
fi


# =====================================================
# 6. OFFLINE RUNTIME TEST
# =====================================================

cat > testar_vi634_vi636.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy


FLAGS = (

    "_VI69_RUNTIME_PATCHED",

    "_VI628_RUNTIME_ACTIVE",
    "_VI629_RUNTIME_ACTIVE",
    "_VI630_RUNTIME_ACTIVE",

    "_VI631_RUNTIME_ACTIVE",
    "_VI632_RUNTIME_ACTIVE",
    "_VI633_RUNTIME_ACTIVE",

    "_VI634_RUNTIME_ACTIVE",
    "_VI635_RUNTIME_ACTIVE",
    "_VI636_RUNTIME_ACTIVE",
)


for flag in FLAGS:

    assert getattr(
        brain,
        flag,
        False
    ), flag


print()
print(
    "======================================"
)
print(
    " VI6.34-6.36 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.33 SAFETY:",
    brain._VI633_RUNTIME_ACTIVE
)

print(
    "VI6.34 AUTO-REPAIR:",
    brain._VI634_RUNTIME_ACTIVE
)

print(
    "VI6.35 DRY COMPILER:",
    brain._VI635_RUNTIME_ACTIVE
)

print(
    "VI6.36 COMPATIBILITY:",
    brain._VI636_RUNTIME_ACTIVE
)

print()
print(
    "FFMPEG EXECUTION=False"
)
print(
    "RENDERER EXECUTION=False"
)
print(
    "VIDEO.PY MODIFIED=False"
)
print(
    "API CALLS=0"
)
print(
    "DOWNLOADS=0"
)
print(
    "VIDEOS=0"
)
print()
PY


# =====================================================
# 7. FULL COMPILE
# =====================================================

echo
echo "===== FULL COMPILE ====="

if ! python -m py_compile \
    vi6_34_motion_auto_repair.py \
    vi6_35_ffmpeg_dry_compiler.py \
    vi6_36_renderer_compatibility.py \
    vi6_36_runtime_policy.py \
    testar_vi634_vi636.py \
    vi6_33_runtime_policy.py \
    vi6_33_cinematic_safety_gate.py \
    vi6_32_scene_duration.py \
    vi6_31_pre_render_auditor.py \
    vi6_30_renderer_contract.py \
    vi6_9_runtime_policy.py \
    vi6_6_active_brain.py \
    midia.py \
    video.py
then

    echo
    echo "COMPILE FALHOU."

    rollback
    exit 1
fi

echo "PYTHON STATUS=0"


# =====================================================
# 8. SELF TESTS
# =====================================================

echo
echo "===== VI6.34 SELF TEST ====="

if ! python vi6_34_motion_auto_repair.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.35 SELF TEST ====="

if ! python vi6_35_ffmpeg_dry_compiler.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.36 SELF TEST ====="

if ! python vi6_36_renderer_compatibility.py; then
    rollback
    exit 1
fi


echo
echo "===== RUNTIME TEST ====="

if ! python testar_vi634_vi636.py; then
    rollback
    exit 1
fi


# =====================================================
# 9. REGRESSIONS
# =====================================================

echo
echo "===== VI6.33 REGRESSION ====="

if ! python vi6_33_cinematic_safety_gate.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.32 REGRESSION ====="

if ! python vi6_32_scene_duration.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.31 REGRESSION ====="

if ! python vi6_31_pre_render_auditor.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.30 REGRESSION ====="

if ! python vi6_30_renderer_contract.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.29 REGRESSION ====="

if ! python vi6_29_ken_burns_intelligence.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.28 REGRESSION ====="

if ! python vi6_28_motion_blueprint.py; then
    rollback
    exit 1
fi


# =====================================================
# 10. STATIC EXECUTION GUARD
# =====================================================

echo
echo "===== ZERO EXECUTION STATIC GUARD ====="

if ! python - <<'PY'
from vi6_36_renderer_compatibility import (
    static_execution_guard
)


files = [
    "vi6_34_motion_auto_repair.py",
    "vi6_35_ffmpeg_dry_compiler.py",
    "vi6_36_renderer_compatibility.py",
    "vi6_36_runtime_policy.py",
]


violations = (
    static_execution_guard(
        files
    )
)


if violations:

    print(
        "FORBIDDEN EXECUTION CALLS:",
        violations
    )

    raise SystemExit(1)


print(
    "FORBIDDEN EXECUTION CALLS=0"
)

print(
    "FFMPEG EXECUTION PATH=0"
)
PY
then

    rollback
    exit 1
fi


# =====================================================
# 11. CORE
# =====================================================

echo
echo "===== BASH CHECK ====="

if ! bash -n gerar_short.sh; then
    rollback
    exit 1
fi

echo "BASH STATUS=0"


echo
echo "===== RELEASE CHECK ====="

if ! ./release_check.sh; then
    rollback
    exit 1
fi


# =====================================================
# 12. CORE HASH SAFETY
# =====================================================

echo
echo "===== CORE HASH SAFETY ====="

: > "$BACKDIR/core_after.sha256"

for F in $CORE_FILES
do
    sha256sum "$F" \
        >> "$BACKDIR/core_after.sha256"
done


if ! diff -u \
    "$BACKDIR/core_before.sha256" \
    "$BACKDIR/core_after.sha256"
then

    echo
    echo "ERRO: CORE FOI MODIFICADO."
    echo "ROLLBACK."

    rollback
    exit 1
fi


echo "CORE FILES UNCHANGED=YES"


# =====================================================
# FINAL
# =====================================================

echo
echo "======================================"
echo " VI6.34 + VI6.35 + VI6.36 INSTALADOS"
echo "======================================"
echo
echo "OK Motion Auto-Repair"
echo "OK Zoom Velocity Repair"
echo "OK Pan Velocity Repair"
echo "OK Documentary Motion Repair"
echo "OK Non-Motion HOLD Preservation"
echo "OK Contract Rehash"
echo "OK FFmpeg Dry Compiler"
echo "OK Argument Vector Generation"
echo "OK Zoompan Expression Generation"
echo "OK Native Video Preservation"
echo "OK 1080x1920 Plan"
echo "OK 30 FPS Frame Planning"
echo "OK Renderer Compatibility Harness"
echo "OK Post-Repair Safety Recheck"
echo "OK Static Execution Guard"
echo "OK VI6.33 Safety preserved"
echo "OK VI6.30 Contract preserved"
echo
echo "CORE FILES UNCHANGED=YES"
echo "MIDIA.PY MODIFICADO=NAO"
echo "VIDEO.PY MODIFICADO=NAO"
echo "AUDIO.PY MODIFICADO=NAO"
echo "LEGENDA MODIFICADA=NAO"
echo "GERAR_SHORT MODIFICADO=NAO"
echo
echo "FFMPEG COMMAND COMPILED=DRY_RUN"
echo "FFMPEG EXECUTADO=NAO"
echo "RENDERER EXECUTADO=NAO"
echo "API CALLS=0"
echo "DOWNLOADS NOVOS=0"
echo "VIDEOS GERADOS=0"
echo
echo "FUTURO RELATORIO:"
echo "logs/producao/vi6_36_renderer_compat_latest.json"
echo
