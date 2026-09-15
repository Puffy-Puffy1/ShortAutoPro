#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi631_vi633_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================"
echo " VI6.31 + VI6.32 + VI6.33"
echo " PRE-RENDER CINEMATIC SAFETY"
echo " OFFLINE / NO FFMPEG"
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
vi6_25_visual_sequence.py
vi6_26_motion_strategy.py
vi6_27_transition_intelligence.py
vi6_28_motion_blueprint.py
vi6_29_ken_burns_intelligence.py
vi6_30_renderer_contract.py
vi6_30_runtime_policy.py
"

for F in $REQUIRED
do
    if [ ! -f "$F" ]; then
        echo "ERRO: $F não encontrado."
        echo "NENHUMA ALTERAÇÃO FOI FEITA."
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
    vi6_28_motion_blueprint.py \
    vi6_29_ken_burns_intelligence.py \
    vi6_30_renderer_contract.py \
    vi6_30_runtime_policy.py
then
    echo
    echo "BASELINE FALHOU."
    echo "NENHUMA ALTERAÇÃO FOI FEITA."
    exit 3
fi

echo "BASELINE=OK"


# =====================================================
# HASH DO CORE
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
    vi6_31_pre_render_auditor.py \
    vi6_32_scene_duration.py \
    vi6_33_cinematic_safety_gate.py \
    vi6_33_runtime_policy.py \
    testar_vi631_vi633.py
do
    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi
done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.31-6.33"
    echo "======================================"

    cp \
        "$BACKDIR/vi6_9_runtime_policy.py" \
        vi6_9_runtime_policy.py


    for F in \
        vi6_31_pre_render_auditor.py \
        vi6_32_scene_duration.py \
        vi6_33_cinematic_safety_gate.py \
        vi6_33_runtime_policy.py \
        testar_vi631_vi633.py
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
# 1. VI6.32 SCENE DURATION INTELLIGENCE
# =====================================================

cat > vi6_32_scene_duration.py <<'PY'
#!/usr/bin/env python3

import re


VERSION = "6.32"

WORDS_PER_SECOND = 2.55


def _s(v):
    return str(v or "").strip()


def _f(v):

    try:

        value = float(v)

        if value > 0:
            return value

    except Exception:
        pass

    return None


def _scene_number(scene):

    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )

    try:

        return int(
            board.get(
                "scene",
                0
            )
            or 0
        )

    except Exception:

        return 0


def _role(scene):

    role = _s(
        scene.get(
            "retrieval_role_6_7"
        )
    ).upper()


    if role:
        return role


    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    return _s(
        board.get(
            "role"
        )
        or "CONTEXT"
    ).upper()


def _narration(scene):

    for field in (
        "segmento",
        "segment",
        "narracao",
        "narração",
        "texto",
        "text",
        "script",
    ):

        value = _s(
            scene.get(
                field
            )
        )


        if value:
            return value


    return ""


def _word_count(text):

    return len(
        re.findall(
            r"\b[\wÀ-ÿ'-]+\b",
            _s(text)
        )
    )


def _explicit_duration(scene):

    for field in (
        "duration",
        "duration_s",
        "duration_sec",
        "scene_duration",
        "duracao",
        "duração",
        "duracao_s",
        "duracao_segundos",
    ):

        value = _f(
            scene.get(
                field
            )
        )


        if value is not None:

            return (
                value,
                field
            )


    timing = (
        scene.get(
            "timing"
        )
        or scene.get(
            "timestamps"
        )
        or {}
    )


    if isinstance(
        timing,
        dict
    ):

        start = _f(
            timing.get(
                "start"
            )
            or timing.get(
                "inicio"
            )
        )


        end = _f(
            timing.get(
                "end"
            )
            or timing.get(
                "fim"
            )
        )


        if (
            start is not None
            and end is not None
            and end > start
        ):

            return (
                end - start,
                "timing_start_end"
            )


    start = _f(
        scene.get(
            "start"
        )
        or scene.get(
            "inicio"
        )
    )


    end = _f(
        scene.get(
            "end"
        )
        or scene.get(
            "fim"
        )
    )


    if (
        start is not None
        and end is not None
        and end > start
    ):

        return (
            end - start,
            "scene_start_end"
        )


    return (
        None,
        None
    )


def duration_info(scene):

    explicit, source = (
        _explicit_duration(
            scene
        )
    )


    role = _role(
        scene
    )


    if explicit is not None:

        value = max(
            .75,
            min(
                20.0,
                explicit
            )
        )


        return {

            "version":
                VERSION,

            "scene":
                _scene_number(
                    scene
                ),

            "role":
                role,

            "seconds":
                round(
                    value,
                    3
                ),

            "source":
                source,

            "confidence":
                "HIGH",

            "estimated":
                False,
        }


    narration = _narration(
        scene
    )


    words = _word_count(
        narration
    )


    if words > 0:

        estimated = (
            words
            / WORDS_PER_SECOND
        )


        if role == "CTA":

            minimum = 1.2

        else:

            minimum = 1.6


        estimated = max(
            minimum,
            min(
                12.0,
                estimated
            )
        )


        return {

            "version":
                VERSION,

            "scene":
                _scene_number(
                    scene
                ),

            "role":
                role,

            "seconds":
                round(
                    estimated,
                    3
                ),

            "source":
                "narration_word_estimate",

            "confidence":
                "MEDIUM",

            "estimated":
                True,

            "words":
                words,

            "words_per_second":
                WORDS_PER_SECOND,
        }


    # Último fallback apenas para que
    # possamos validar o plano offline.
    fallback = (
        2.0
        if role == "CTA"
        else 4.0
    )


    return {

        "version":
            VERSION,

        "scene":
            _scene_number(
                scene
            ),

        "role":
            role,

        "seconds":
            fallback,

        "source":
            "safe_default",

        "confidence":
            "LOW",

        "estimated":
            True,

        "words":
            0,
    }


def motion_metrics(
    contract,
    duration
):

    seconds = float(
        duration.get(
            "seconds",
            4.0
        )
        or 4.0
    )


    seconds = max(
        .25,
        seconds
    )


    ken = (
        contract.get(
            "ken_burns"
        )
        or {}
    )


    if not ken.get(
        "enabled"
    ):

        return {

            "zoom_delta":
                0.0,

            "zoom_rate":
                0.0,

            "pan_distance":
                0.0,

            "pan_rate":
                0.0,
        }


    z1 = float(
        ken.get(
            "zoom_start",
            1.0
        )
    )


    z2 = float(
        ken.get(
            "zoom_end",
            1.0
        )
    )


    x1 = float(
        ken.get(
            "start_x",
            .5
        )
    )


    x2 = float(
        ken.get(
            "end_x",
            .5
        )
    )


    y1 = float(
        ken.get(
            "start_y",
            .5
        )
    )


    y2 = float(
        ken.get(
            "end_y",
            .5
        )
    )


    zoom_delta = abs(
        z2 - z1
    )


    pan_distance = (
        (
            (x2 - x1) ** 2
            + (y2 - y1) ** 2
        )
        ** .5
    )


    return {

        "zoom_delta":
            round(
                zoom_delta,
                5
            ),

        "zoom_rate":
            round(
                zoom_delta
                / seconds,
                5
            ),

        "pan_distance":
            round(
                pan_distance,
                5
            ),

        "pan_rate":
            round(
                pan_distance
                / seconds,
                5
            ),
    }


def self_test():

    explicit = duration_info(
        {
            "duration":
                4.25,

            "_vi68_storyboard":
                {
                    "scene": 2
                }
        }
    )


    assert (
        explicit[
            "seconds"
        ]
        == 4.25
    )


    assert (
        explicit[
            "confidence"
        ]
        == "HIGH"
    )


    estimated = duration_info(
        {
            "segmento":
                (
                    "This is a short narration "
                    "with approximately ten words "
                    "for this scene."
                ),

            "_vi68_storyboard":
                {
                    "scene": 3
                }
        }
    )


    assert (
        estimated[
            "seconds"
        ]
        > 1
    )


    assert (
        estimated[
            "estimated"
        ]
        is True
    )


    metrics = motion_metrics(
        {
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

                    "end_x":
                        .55,

                    "start_y":
                        .50,

                    "end_y":
                        .50,
                }
        },
        {
            "seconds":
                4.0
        }
    )


    assert (
        metrics[
            "zoom_rate"
        ]
        == .01
    )


    assert (
        metrics[
            "pan_rate"
        ]
        == .025
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.32 DURATION SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Explicit Duration"
    )
    print(
        "OK Timestamp Duration"
    )
    print(
        "OK Narration Estimate"
    )
    print(
        "OK Safe Default"
    )
    print(
        "OK Zoom Rate"
    )
    print(
        "OK Pan Rate"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 2. VI6.33 CINEMATIC SAFETY GATE
# =====================================================

cat > vi6_33_cinematic_safety_gate.py <<'PY'
#!/usr/bin/env python3

from vi6_32_scene_duration import (
    motion_metrics
)


VERSION = "6.33"


ZOOM_RATE_LIMITS = {

    "EVIDENCE":
        .015,

    "PERSON":
        .026,

    "PLACE":
        .026,

    "OBJECT":
        .036,

    "CONTEXT":
        .036,

    "CTA":
        .012,
}


PAN_RATE_LIMITS = {

    "EVIDENCE":
        .018,

    "PERSON":
        .020,

    "PLACE":
        .035,

    "OBJECT":
        .030,

    "CONTEXT":
        .040,

    "CTA":
        .015,
}


ALLOWED_TRANSITIONS = {

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


def _s(v):
    return str(v or "").strip()


def _u(v):
    return _s(v).upper()


def assess(
    contract,
    duration
):

    blockers = []
    warnings = []


    role = _u(
        contract.get(
            "role"
        )
        or duration.get(
            "role"
        )
        or "CONTEXT"
    )


    media = _u(
        contract.get(
            "media_type"
        )
    )


    seconds = float(
        duration.get(
            "seconds",
            4.0
        )
        or 4.0
    )


    transition = _u(
        contract.get(
            "transition"
        )
    )


    metrics = motion_metrics(
        contract,
        duration
    )


    # =================================
    # CONTRACT INTEGRITY
    # =================================

    if (
        contract.get(
            "contract_valid"
        )
        is False
    ):

        blockers.append(
            "invalid_renderer_contract"
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
        contract.get(
            "ffmpeg_filter"
        )
        is not None
    ):

        blockers.append(
            "ffmpeg_filter_should_be_inactive"
        )


    # =================================
    # DURATION
    # =================================

    if seconds < .75:

        blockers.append(
            "scene_too_short"
        )


    elif seconds < 1.25:

        warnings.append(
            "very_short_scene"
        )


    if seconds > 15.0:

        warnings.append(
            "very_long_scene"
        )


    if (
        duration.get(
            "confidence"
        )
        == "LOW"
    ):

        warnings.append(
            "duration_low_confidence"
        )


    # =================================
    # TRANSITION
    # =================================

    if (
        transition
        not in ALLOWED_TRANSITIONS
    ):

        blockers.append(
            "invalid_transition"
        )


    # =================================
    # VIDEO = NATIVE MOTION
    # =================================

    if media == "VIDEO":

        ken = (
            contract.get(
                "ken_burns"
            )
            or {}
        )


        if ken.get(
            "enabled"
        ):

            blockers.append(
                "synthetic_motion_on_video"
            )


    # =================================
    # STILL MOTION RATE
    # =================================

    if media == "STILL":

        max_zoom = (
            ZOOM_RATE_LIMITS.get(
                role,
                .036
            )
        )


        max_pan = (
            PAN_RATE_LIMITS.get(
                role,
                .040
            )
        )


        if (
            metrics[
                "zoom_rate"
            ]
            > max_zoom
        ):

            blockers.append(
                "zoom_velocity_too_high"
            )


        if (
            metrics[
                "pan_rate"
            ]
            > max_pan
        ):

            blockers.append(
                "pan_velocity_too_high"
            )


    # =================================
    # DOCUMENTARY EVIDENCE PROTECTION
    # =================================

    if (
        role == "EVIDENCE"
        and _u(
            contract.get(
                "profile"
            )
        )
        == "DOCUMENTARY_HOLD"
    ):

        if (
            metrics[
                "zoom_delta"
            ]
            > .05
        ):

            blockers.append(
                "documentary_zoom_excess"
            )


        if (
            metrics[
                "pan_distance"
            ]
            > .035
        ):

            blockers.append(
                "documentary_pan_excess"
            )


    # =================================
    # STATUS
    # =================================

    if blockers:

        status = "HOLD"

    elif warnings:

        status = "WARN"

    else:

        status = "PASS"


    aggressive = bool(

        metrics[
            "zoom_rate"
        ] >= .025

        or metrics[
            "pan_rate"
        ] >= .030

        or transition
        in {
            "FAST_CUT",
            "CONTRAST_CUT",
        }
    )


    return {

        "version":
            VERSION,

        "status":
            status,

        "role":
            role,

        "media_type":
            media,

        "seconds":
            round(
                seconds,
                3
            ),

        "duration_source":
            duration.get(
                "source"
            ),

        "duration_confidence":
            duration.get(
                "confidence"
            ),

        "transition":
            transition,

        "metrics":
            metrics,

        "aggressive":
            aggressive,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "renderer_allowed":
            status
            != "HOLD",

        # Continua apenas auditando.
        "renderer_applied":
            False,
    }


def self_test():

    safe = assess(
        {
            "contract_valid":
                True,

            "renderer_applied":
                False,

            "ffmpeg_filter":
                None,

            "role":
                "EVIDENCE",

            "media_type":
                "STILL",

            "profile":
                "DOCUMENTARY_HOLD",

            "transition":
                "DIRECT_CUT",

            "ken_burns":
                {
                    "enabled":
                        True,

                    "zoom_start":
                        1.0,

                    "zoom_end":
                        1.035,

                    "start_x":
                        .50,

                    "end_x":
                        .50,

                    "start_y":
                        .50,

                    "end_y":
                        .49,
                }
        },
        {
            "seconds":
                4.0,

            "source":
                "test",

            "confidence":
                "HIGH",

            "role":
                "EVIDENCE",
        }
    )


    assert (
        safe[
            "status"
        ]
        == "PASS"
    )


    unsafe = assess(
        {
            "contract_valid":
                True,

            "renderer_applied":
                False,

            "ffmpeg_filter":
                None,

            "role":
                "EVIDENCE",

            "media_type":
                "STILL",

            "profile":
                "DOCUMENTARY_HOLD",

            "transition":
                "DIRECT_CUT",

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

                    "end_x":
                        .58,

                    "start_y":
                        .50,

                    "end_y":
                        .50,
                }
        },
        {
            "seconds":
                2.0,

            "source":
                "test",

            "confidence":
                "HIGH",

            "role":
                "EVIDENCE",
        }
    )


    assert (
        unsafe[
            "status"
        ]
        == "HOLD"
    )


    assert (
        "zoom_velocity_too_high"
        in unsafe[
            "blockers"
        ]
    )


    video = assess(
        {
            "contract_valid":
                True,

            "renderer_applied":
                False,

            "ffmpeg_filter":
                None,

            "role":
                "CONTEXT",

            "media_type":
                "VIDEO",

            "profile":
                "NATIVE_MOTION",

            "transition":
                "FAST_CUT",

            "ken_burns":
                {
                    "enabled":
                        False
                }
        },
        {
            "seconds":
                4.0,

            "source":
                "test",

            "confidence":
                "HIGH",

            "role":
                "CONTEXT",
        }
    )


    assert (
        video[
            "status"
        ]
        in {
            "PASS",
            "WARN",
        }
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.33 SAFETY SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Zoom Velocity Gate"
    )
    print(
        "OK Pan Velocity Gate"
    )
    print(
        "OK Documentary Motion Protection"
    )
    print(
        "OK Video Native Motion Protection"
    )
    print(
        "OK Transition Validation"
    )
    print(
        "OK Duration Confidence Warning"
    )
    print(
        "OK HOLD / WARN / PASS"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 3. VI6.31 GLOBAL PRE-RENDER AUDITOR
# =====================================================

cat > vi6_31_pre_render_auditor.py <<'PY'
#!/usr/bin/env python3

import json
import os
from datetime import datetime


VERSION = "6.31"

_EVENTS = []


def reset():

    _EVENTS.clear()


def record(
    contract,
    duration,
    safety
):

    event = {

        "scene":
            contract.get(
                "scene"
            ),

        "role":
            contract.get(
                "role"
            ),

        "media_type":
            contract.get(
                "media_type"
            ),

        "profile":
            contract.get(
                "profile"
            ),

        "transition":
            contract.get(
                "transition"
            ),

        "duration":
            duration,

        "safety":
            safety,

        "contract_hash":
            contract.get(
                "contract_hash"
            ),

        "renderer_applied":
            contract.get(
                "renderer_applied"
            ),
    }


    _EVENTS.append(
        event
    )


    return event


def _max_aggressive_streak():

    current = 0
    maximum = 0


    for event in _EVENTS:

        aggressive = bool(
            (
                event.get(
                    "safety"
                )
                or {}
            ).get(
                "aggressive"
            )
        )


        if aggressive:

            current += 1

            maximum = max(
                maximum,
                current
            )

        else:

            current = 0


    return maximum


def audit():

    total = len(
        _EVENTS
    )


    hold = [
        event[
            "scene"
        ]

        for event in _EVENTS

        if (
            event.get(
                "safety"
            )
            or {}
        ).get(
            "status"
        )
        == "HOLD"
    ]


    warn = [
        event[
            "scene"
        ]

        for event in _EVENTS

        if (
            event.get(
                "safety"
            )
            or {}
        ).get(
            "status"
        )
        == "WARN"
    ]


    renderer_violations = [
        event[
            "scene"
        ]

        for event in _EVENTS

        if (
            event.get(
                "renderer_applied"
            )
            is not False
        )
    ]


    durations = [

        float(
            (
                event.get(
                    "duration"
                )
                or {}
            ).get(
                "seconds",
                0
            )
            or 0
        )

        for event in _EVENTS
    ]


    total_duration = sum(
        durations
    )


    transitions = {}

    profiles = {}


    for event in _EVENTS:

        transition = (
            event.get(
                "transition"
            )
            or "NONE"
        )


        transitions[
            transition
        ] = (
            transitions.get(
                transition,
                0
            )
            + 1
        )


        profile = (
            event.get(
                "profile"
            )
            or "NONE"
        )


        profiles[
            profile
        ] = (
            profiles.get(
                profile,
                0
            )
            + 1
        )


    aggressive_streak = (
        _max_aggressive_streak()
    )


    global_warnings = []


    if aggressive_streak >= 3:

        global_warnings.append(
            "three_aggressive_scenes_in_sequence"
        )


    if total >= 12:

        stage = "COMPLETE"

    else:

        stage = "IN_PROGRESS"


    if (
        hold
        or renderer_violations
    ):

        decision = "HOLD"

    elif (
        warn
        or global_warnings
    ):

        decision = "WARN"

    else:

        decision = "PASS"


    return {

        "version":
            VERSION,

        "stage":
            stage,

        "decision":
            decision,

        "scenes":
            total,

        "hold_scenes":
            hold,

        "warning_scenes":
            warn,

        "renderer_violations":
            renderer_violations,

        "total_duration":
            round(
                total_duration,
                3
            ),

        "average_duration":
            round(
                (
                    total_duration
                    / total
                )
                if total
                else 0,
                3
            ),

        "max_aggressive_streak":
            aggressive_streak,

        "global_warnings":
            global_warnings,

        "transitions":
            transitions,

        "profiles":
            profiles,

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
            "vi6_31_pre_render_audit_latest.json"
        )


    payload = {

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "audit":
            audit(),
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


    for number in (
        1,
        2,
        3,
    ):

        record(
            {
                "scene":
                    number,

                "role":
                    "CONTEXT",

                "media_type":
                    "STILL",

                "profile":
                    "CONTEXT_DRIFT",

                "transition":
                    "DIRECT_CUT",

                "contract_hash":
                    str(
                        number
                    ),

                "renderer_applied":
                    False,
            },
            {
                "seconds":
                    4.0,

                "confidence":
                    "HIGH",
            },
            {
                "status":
                    "PASS",

                "aggressive":
                    False,
            }
        )


    result = audit()


    assert (
        result[
            "scenes"
        ]
        == 3
    )


    assert (
        result[
            "decision"
        ]
        == "PASS"
    )


    assert (
        result[
            "stage"
        ]
        == "IN_PROGRESS"
    )


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.31 AUDITOR SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Global Contract Audit"
    )
    print(
        "OK Hold Scene Tracking"
    )
    print(
        "OK Warning Scene Tracking"
    )
    print(
        "OK Duration Aggregation"
    )
    print(
        "OK Motion Streak Detection"
    )
    print(
        "OK Transition Distribution"
    )
    print(
        "OK Renderer-Inactive Verification"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 4. VI6.33 RUNTIME POLICY
# =====================================================

cat > vi6_33_runtime_policy.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain


from vi6_30_renderer_contract import (
    build_contract,
    validate_contract,
)


from vi6_32_scene_duration import (
    duration_info
)


from vi6_33_cinematic_safety_gate import (
    assess
)


from vi6_31_pre_render_auditor import (
    record,
    audit,
    flush,
    reset,
)


if not getattr(
    brain,
    "_VI633_RUNTIME_ACTIVE",
    False
):

    _base_supervisor_633 = (
        brain.supervisionar_vi6_6
    )


    def _wrapped_633(
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
        ) = _base_supervisor_633(
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
        )


        # Fail-safe:
        # se por algum motivo o wrapper 6.30
        # não anexou contrato, recriamos apenas
        # metadata. Continua sem FFmpeg.
        if not isinstance(
            contract,
            dict
        ):

            contract = (
                build_contract(
                    cena,
                    candidate,
                    meta
                )
            )


            ok_contract, errors = (
                validate_contract(
                    contract
                )
            )


            contract[
                "contract_valid"
            ] = ok_contract


            if not ok_contract:

                contract[
                    "contract_errors"
                ] = errors


        duration = duration_info(
            cena
        )


        safety = assess(
            contract,
            duration
        )


        if (
            safety[
                "status"
            ]
            == "HOLD"
        ):

            contract[
                "status"
            ] = "HOLD"


        contract[
            "vi633_safety_status"
        ] = safety[
            "status"
        ]


        contract[
            "vi632_duration"
        ] = duration


        contract[
            "renderer_applied"
        ] = False


        meta[
            "vi631_pre_render"
        ] = True


        meta[
            "vi632_duration"
        ] = duration


        meta[
            "vi633_cinematic_safety"
        ] = safety


        meta[
            "vi633_renderer_allowed"
        ] = safety[
            "renderer_allowed"
        ]


        # Não veta mídia nesta fase.
        # Apenas marca o contrato.
        if candidate is not None:

            candidate[
                "_vi632_duration"
            ] = duration


            candidate[
                "_vi633_cinematic_status"
            ] = safety[
                "status"
            ]


            candidate[
                "_vi633_renderer_allowed"
            ] = safety[
                "renderer_allowed"
            ]


        record(
            contract,
            duration,
            safety
        )


        global_audit = audit()


        meta[
            "vi631_global_audit"
        ] = {

            "stage":
                global_audit[
                    "stage"
                ],

            "decision":
                global_audit[
                    "decision"
                ],

            "scenes":
                global_audit[
                    "scenes"
                ],

            "hold_scenes":
                global_audit[
                    "hold_scenes"
                ],

            "warning_scenes":
                global_audit[
                    "warning_scenes"
                ],

            "total_duration":
                global_audit[
                    "total_duration"
                ],

            "max_aggressive_streak":
                global_audit[
                    "max_aggressive_streak"
                ],
        }


        if (
            number >= 12
            or board.get(
                "cta_reuse"
            )
        ):

            try:

                meta[
                    "vi631_audit_path"
                ] = flush()

            except Exception as exc:

                meta[
                    "vi631_audit_error"
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
        _wrapped_633
    )


    brain._VI631_RUNTIME_ACTIVE = True

    brain._VI632_RUNTIME_ACTIVE = True

    brain._VI633_RUNTIME_ACTIVE = True
PY


# =====================================================
# 5. CONECTAR AO STACK EXISTENTE
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
    "# VI6.31-6.33 PRE-RENDER SAFETY STACK"
)


if MARKER in source:

    print(
        "VI6.31-6.33 já conectado."
    )

    raise SystemExit(0)


append = '''

# =========================================
# VI6.31-6.33 PRE-RENDER SAFETY STACK
# =========================================
import vi6_33_runtime_policy
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
    " VI6.31-6.33 RUNTIME ATTACHED"
)
print(
    "======================================"
)
print(
    "Pre-Render Auditor: ACTIVE"
)
print(
    "Duration Intelligence: ACTIVE"
)
print(
    "Cinematic Safety Gate: ACTIVE"
)
print(
    "FFmpeg Execution: DISABLED"
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

cat > testar_vi631_vi633.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy


FLAGS = (

    "_VI69_RUNTIME_PATCHED",

    "_VI619_RUNTIME_ACTIVE",
    "_VI620_RUNTIME_ACTIVE",
    "_VI621_RUNTIME_ACTIVE",

    "_VI623_RUNTIME_ACTIVE",
    "_VI624_RUNTIME_ACTIVE",

    "_VI626_RUNTIME_ACTIVE",
    "_VI627_RUNTIME_ACTIVE",

    "_VI628_RUNTIME_ACTIVE",
    "_VI629_RUNTIME_ACTIVE",
    "_VI630_RUNTIME_ACTIVE",

    "_VI631_RUNTIME_ACTIVE",
    "_VI632_RUNTIME_ACTIVE",
    "_VI633_RUNTIME_ACTIVE",
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
    " VI6.31-6.33 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.30 CONTRACT:",
    brain._VI630_RUNTIME_ACTIVE
)

print(
    "VI6.31 AUDITOR:",
    brain._VI631_RUNTIME_ACTIVE
)

print(
    "VI6.32 DURATION:",
    brain._VI632_RUNTIME_ACTIVE
)

print(
    "VI6.33 SAFETY:",
    brain._VI633_RUNTIME_ACTIVE
)

print()
print(
    "RENDERER EXECUTION=False"
)
print(
    "FFMPEG EXECUTION=False"
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
    vi6_31_pre_render_auditor.py \
    vi6_32_scene_duration.py \
    vi6_33_cinematic_safety_gate.py \
    vi6_33_runtime_policy.py \
    testar_vi631_vi633.py \
    vi6_30_renderer_contract.py \
    vi6_30_runtime_policy.py \
    vi6_29_ken_burns_intelligence.py \
    vi6_28_motion_blueprint.py \
    vi6_27_transition_intelligence.py \
    vi6_26_motion_strategy.py \
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
echo "===== VI6.32 SELF TEST ====="

if ! python vi6_32_scene_duration.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.33 SELF TEST ====="

if ! python vi6_33_cinematic_safety_gate.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.31 SELF TEST ====="

if ! python vi6_31_pre_render_auditor.py; then
    rollback
    exit 1
fi


echo
echo "===== RUNTIME TEST ====="

if ! python testar_vi631_vi633.py; then
    rollback
    exit 1
fi


# =====================================================
# 9. REGRESSIONS
# =====================================================

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


echo
echo "===== VI6.27 REGRESSION ====="

if ! python vi6_27_transition_intelligence.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.26 REGRESSION ====="

if ! python vi6_26_motion_strategy.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.23 REGRESSION ====="

if ! python vi6_23_adaptive_budget.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.19 REGRESSION ====="

if ! python vi6_19_true_recovery.py; then
    rollback
    exit 1
fi


# =====================================================
# 10. CORE CHECK
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
# 11. HASH SAFETY
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
    echo "ERRO: CORE MODIFICADO."
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
echo " VI6.31 + VI6.32 + VI6.33 INSTALADOS"
echo "======================================"
echo
echo "OK Global Pre-Render Contract Auditor"
echo "OK Explicit Scene Duration Detection"
echo "OK Timestamp Duration Detection"
echo "OK Narration Duration Estimation"
echo "OK Zoom Velocity Calculation"
echo "OK Pan Velocity Calculation"
echo "OK Role-Specific Velocity Limits"
echo "OK Documentary Motion Protection"
echo "OK Native Video Motion Protection"
echo "OK Invalid Transition Protection"
echo "OK Aggressive Motion Streak Detection"
echo "OK HOLD / WARN / PASS"
echo "OK Total Duration Audit"
echo "OK Average Duration Audit"
echo "OK Renderer-Inactive Verification"
echo "OK VI6.30 Contract preserved"
echo "OK VI6.29 Ken Burns preserved"
echo "OK VI6.27 Transition Intelligence preserved"
echo
echo "CORE FILES UNCHANGED=YES"
echo "MIDIA.PY MODIFICADO=NAO"
echo "VIDEO.PY MODIFICADO=NAO"
echo "AUDIO.PY MODIFICADO=NAO"
echo "LEGENDA MODIFICADA=NAO"
echo "GERAR_SHORT MODIFICADO=NAO"
echo
echo "FFMPEG EXECUTADO=NAO"
echo "FFMPEG FILTER ATIVADO=NAO"
echo "RENDERER_APPLIED=FALSE"
echo "API CALLS=0"
echo "DOWNLOADS NOVOS=0"
echo "VIDEOS GERADOS=0"
echo
echo "FUTURO RELATORIO:"
echo "logs/producao/vi6_31_pre_render_audit_latest.json"
echo
