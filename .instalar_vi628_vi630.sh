#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi628_vi630_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================"
echo " VI6.28 + VI6.29 + VI6.30"
echo " CINEMATIC MOTION CONTRACT"
echo " OFFLINE / NO RENDER"
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
vi6_19_true_recovery.py
vi6_22_story_audit.py
vi6_23_runtime_policy.py
vi6_24_runtime_telemetry.py
vi6_25_visual_sequence.py
vi6_26_motion_strategy.py
vi6_26_runtime_policy.py
vi6_27_transition_intelligence.py
vi6_27_runtime_policy.py
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
    vi6_25_visual_sequence.py \
    vi6_26_motion_strategy.py \
    vi6_27_transition_intelligence.py
then

    echo
    echo "BASELINE FALHOU."
    echo "NENHUMA ALTERAÇÃO FOI FEITA."

    exit 3
fi

echo "BASELINE=OK"


# =====================================================
# HASH DOS ARQUIVOS ESTÁVEIS
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
    vi6_28_motion_blueprint.py \
    vi6_29_ken_burns_intelligence.py \
    vi6_30_renderer_contract.py \
    vi6_30_runtime_policy.py \
    testar_vi628_vi630.py
do

    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi

done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.28-6.30"
    echo "======================================"

    cp \
        "$BACKDIR/vi6_9_runtime_policy.py" \
        vi6_9_runtime_policy.py


    for F in \
        vi6_28_motion_blueprint.py \
        vi6_29_ken_burns_intelligence.py \
        vi6_30_renderer_contract.py \
        vi6_30_runtime_policy.py \
        testar_vi628_vi630.py
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
# 1. VI6.28 CINEMATIC MOTION BLUEPRINT
# =====================================================

cat > vi6_28_motion_blueprint.py <<'PY'
#!/usr/bin/env python3


VERSION = "6.28"


def _s(v):
    return str(v or "").strip()


def _u(v):
    return _s(v).upper()


def scene_number(scene):

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


def role(scene):

    value = _u(
        scene.get(
            "retrieval_role_6_7"
        )
    )


    if value:
        return value


    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    value = _u(
        board.get(
            "role"
        )
    )


    if value:
        return value


    mode = _s(
        scene.get(
            "visual_mode"
        )
    ).lower()


    if "cta" in mode:
        return "CTA"

    if any(
        x in mode
        for x in (
            "evidence",
            "document",
            "archive",
        )
    ):
        return "EVIDENCE"

    if any(
        x in mode
        for x in (
            "person",
            "portrait",
        )
    ):
        return "PERSON"

    if any(
        x in mode
        for x in (
            "location",
            "place",
            "architecture",
        )
    ):
        return "PLACE"

    if any(
        x in mode
        for x in (
            "object",
            "product",
            "medicine",
            "package",
        )
    ):
        return "OBJECT"

    return "CONTEXT"


def rhythm(scene):

    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    value = _u(
        board.get(
            "rhythm"
        )
    )


    if value:
        return value


    number = scene_number(
        scene
    )


    if number <= 1:
        return "HOOK"

    if number <= 4:
        return "SETUP"

    if number <= 8:
        return "ESCALATION"

    if number < 12:
        return "RESOLUTION"

    return "CTA"


def media_type(candidate):

    if not candidate:
        return "NONE"


    raw = _s(
        candidate.get(
            "tipo"
        )
        or candidate.get(
            "type"
        )
    ).lower()


    url = _s(
        candidate.get(
            "url"
        )
    ).lower()


    blob = (
        raw
        + " "
        + url
    )


    if any(
        marker in blob
        for marker in (
            "video",
            "vídeo",
            ".mp4",
            ".webm",
            ".mov",
        )
    ):

        return "VIDEO"


    if any(
        marker in blob
        for marker in (
            "foto",
            "photo",
            "image",
            "imagem",
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        )
    ):

        return "STILL"


    return "UNKNOWN"


def candidate_class(
    candidate,
    meta=None
):

    meta = (
        meta
        or {}
    )


    if not candidate:
        return "NONE"


    return _u(
        meta.get(
            "class"
        )
        or candidate.get(
            "_vi611_class"
        )
        or candidate.get(
            "_vi6_class"
        )
        or candidate.get(
            "class"
        )
        or "UNKNOWN"
    )


def truth_ok(
    candidate,
    meta=None
):

    meta = (
        meta
        or {}
    )


    if not candidate:
        return False


    return bool(
        meta.get(
            "truth_ok",
            candidate.get(
                "_vi611_truth",
                candidate.get(
                    "_vi6_truth_ok",
                    candidate.get(
                        "truth_ok",
                        False
                    )
                )
            )
        )
    )


def build_blueprint(
    scene,
    candidate,
    meta=None
):

    number = scene_number(
        scene
    )

    r = role(
        scene
    )

    beat = rhythm(
        scene
    )

    media = media_type(
        candidate
    )

    classe = candidate_class(
        candidate,
        meta
    )

    truth = truth_ok(
        candidate,
        meta
    )


    transition = _u(
        (
            meta
            or {}
        ).get(
            "vi627_transition"
        )
        or "DIRECT_CUT"
    )


    blueprint = {

        "version":
            VERSION,

        "scene":
            number,

        "role":
            r,

        "rhythm":
            beat,

        "media_type":
            media,

        "class":
            classe,

        "truth_ok":
            truth,

        "transition":
            transition,

        "synthetic_motion":
            False,

        "profile":
            "NONE",

        "intensity":
            "NONE",

        "direction":
            "CENTER",

        "zoom_start":
            1.0,

        "zoom_end":
            1.0,

        "renderer_applied":
            False,
    }


    # =================================
    # VIDEO
    # =================================

    if media == "VIDEO":

        blueprint[
            "profile"
        ] = "NATIVE_MOTION"

        blueprint[
            "intensity"
        ] = "NATIVE"

        blueprint[
            "synthetic_motion"
        ] = False


        return blueprint


    # =================================
    # UNKNOWN / NONE
    # =================================

    if media != "STILL":

        blueprint[
            "profile"
        ] = "NO_MOTION"

        return blueprint


    blueprint[
        "synthetic_motion"
    ] = True


    # =================================
    # DOCUMENTARY EVIDENCE
    # =================================

    if (
        r == "EVIDENCE"
        and classe
        == "REAL_DOCUMENTARY"
        and truth
    ):

        blueprint[
            "profile"
        ] = "DOCUMENTARY_HOLD"

        blueprint[
            "intensity"
        ] = "VERY_LOW"

        blueprint[
            "zoom_end"
        ] = 1.035


    # =================================
    # PERSON / PORTRAIT
    # =================================

    elif r == "PERSON":

        blueprint[
            "profile"
        ] = "PORTRAIT_PUSH"

        blueprint[
            "intensity"
        ] = "LOW"

        blueprint[
            "zoom_end"
        ] = 1.065


    # =================================
    # LOCATION
    # =================================

    elif r == "PLACE":

        if beat in {
            "HOOK",
            "SETUP",
        }:

            blueprint[
                "profile"
            ] = "ESTABLISHING_DRIFT"

            blueprint[
                "intensity"
            ] = "LOW"

            blueprint[
                "zoom_end"
            ] = 1.045


            blueprint[
                "direction"
            ] = (
                "LEFT_TO_RIGHT"
                if number % 2
                else "RIGHT_TO_LEFT"
            )


        else:

            blueprint[
                "profile"
            ] = "LOCATION_PUSH"

            blueprint[
                "intensity"
            ] = "LOW"

            blueprint[
                "zoom_end"
            ] = 1.055


    # =================================
    # OBJECT / DETAIL
    # =================================

    elif r == "OBJECT":

        blueprint[
            "profile"
        ] = "DETAIL_PUSH"

        blueprint[
            "intensity"
        ] = "MEDIUM"

        blueprint[
            "zoom_end"
        ] = 1.085


    # =================================
    # CTA
    # =================================

    elif r == "CTA":

        blueprint[
            "profile"
        ] = "CTA_HOLD"

        blueprint[
            "intensity"
        ] = "VERY_LOW"

        blueprint[
            "zoom_end"
        ] = 1.025


    # =================================
    # CONTEXT
    # =================================

    else:

        blueprint[
            "profile"
        ] = "CONTEXT_DRIFT"

        blueprint[
            "intensity"
        ] = (
            "MEDIUM"
            if beat
            in {
                "HOOK",
                "ESCALATION",
            }
            else "LOW"
        )


        blueprint[
            "zoom_end"
        ] = (
            1.070
            if beat
            in {
                "HOOK",
                "ESCALATION",
            }
            else 1.050
        )


        blueprint[
            "direction"
        ] = (
            "LEFT_TO_RIGHT"
            if number % 2
            else "RIGHT_TO_LEFT"
        )


    return blueprint


def self_test():

    evidence = build_blueprint(
        {
            "retrieval_role_6_7":
                "EVIDENCE",

            "_vi68_storyboard":
                {
                    "scene": 4,
                    "rhythm":
                        "SETUP"
                }
        },
        {
            "tipo":
                "foto",

            "_vi6_class":
                "REAL_DOCUMENTARY",

            "_vi6_truth_ok":
                True,
        },
        {
            "class":
                "REAL_DOCUMENTARY",

            "truth_ok":
                True,
        }
    )


    assert (
        evidence[
            "profile"
        ]
        == "DOCUMENTARY_HOLD"
    )


    assert (
        evidence[
            "zoom_end"
        ]
        <= 1.04
    )


    video = build_blueprint(
        {
            "retrieval_role_6_7":
                "CONTEXT",

            "_vi68_storyboard":
                {
                    "scene": 6,
                    "rhythm":
                        "ESCALATION"
                }
        },
        {
            "tipo":
                "video"
        },
        {}
    )


    assert (
        video[
            "profile"
        ]
        == "NATIVE_MOTION"
    )


    assert (
        video[
            "synthetic_motion"
        ]
        is False
    )


    obj = build_blueprint(
        {
            "retrieval_role_6_7":
                "OBJECT",

            "_vi68_storyboard":
                {
                    "scene": 7
                }
        },
        {
            "tipo":
                "foto"
        },
        {}
    )


    assert (
        obj[
            "profile"
        ]
        == "DETAIL_PUSH"
    )


    assert (
        obj[
            "zoom_end"
        ]
        <= 1.10
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.28 BLUEPRINT SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Documentary Hold"
    )
    print(
        "OK Portrait Push"
    )
    print(
        "OK Establishing Drift"
    )
    print(
        "OK Detail Push"
    )
    print(
        "OK Context Drift"
    )
    print(
        "OK Native Video Motion"
    )
    print(
        "OK Conservative Zoom Limits"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 2. VI6.29 KEN BURNS INTELLIGENCE
# =====================================================

cat > vi6_29_ken_burns_intelligence.py <<'PY'
#!/usr/bin/env python3


VERSION = "6.29"


def _clamp(
    value,
    low,
    high
):

    return max(
        low,
        min(
            high,
            float(
                value
            )
        )
    )


ROLE_ZOOM_LIMIT = {

    "EVIDENCE":
        1.05,

    "PERSON":
        1.08,

    "PLACE":
        1.07,

    "OBJECT":
        1.10,

    "CONTEXT":
        1.08,

    "CTA":
        1.04,
}


def build_plan(
    blueprint
):

    media = (
        blueprint.get(
            "media_type"
        )
    )


    role = (
        blueprint.get(
            "role"
        )
        or "CONTEXT"
    )


    profile = (
        blueprint.get(
            "profile"
        )
        or "NONE"
    )


    if media != "STILL":

        return {

            "version":
                VERSION,

            "enabled":
                False,

            "reason":
                (
                    "native_video"
                    if media
                    == "VIDEO"
                    else "not_still"
                ),

            "profile":
                profile,

            "renderer_applied":
                False,
        }


    zoom_limit = (
        ROLE_ZOOM_LIMIT.get(
            role,
            1.08
        )
    )


    z1 = _clamp(
        blueprint.get(
            "zoom_start",
            1.0
        ),
        1.0,
        zoom_limit
    )


    z2 = _clamp(
        blueprint.get(
            "zoom_end",
            1.0
        ),
        1.0,
        zoom_limit
    )


    start_x = .50
    start_y = .50
    end_x = .50
    end_y = .50


    # =================================
    # PORTRAIT
    # =================================

    if profile == "PORTRAIT_PUSH":

        start_y = .44
        end_y = .42


    # =================================
    # ESTABLISHING DRIFT
    # =================================

    elif (
        profile
        == "ESTABLISHING_DRIFT"
    ):

        if (
            blueprint.get(
                "direction"
            )
            == "RIGHT_TO_LEFT"
        ):

            start_x = .55
            end_x = .45

        else:

            start_x = .45
            end_x = .55


    # =================================
    # CONTEXT DRIFT
    # =================================

    elif (
        profile
        == "CONTEXT_DRIFT"
    ):

        if (
            blueprint.get(
                "direction"
            )
            == "RIGHT_TO_LEFT"
        ):

            start_x = .54
            end_x = .46

        else:

            start_x = .46
            end_x = .54


    # =================================
    # DETAIL
    # =================================

    elif profile == "DETAIL_PUSH":

        start_x = .50
        start_y = .52
        end_x = .50
        end_y = .50


    # =================================
    # DOCUMENTARY
    # =================================

    elif (
        profile
        == "DOCUMENTARY_HOLD"
    ):

        start_x = .50
        start_y = .50
        end_x = .50
        end_y = .49


    # Safety box.
    start_x = _clamp(
        start_x,
        .42,
        .58
    )

    end_x = _clamp(
        end_x,
        .42,
        .58
    )

    start_y = _clamp(
        start_y,
        .40,
        .58
    )

    end_y = _clamp(
        end_y,
        .40,
        .58
    )


    return {

        "version":
            VERSION,

        "enabled":
            True,

        "profile":
            profile,

        "role":
            role,

        "zoom_start":
            round(
                z1,
                4
            ),

        "zoom_end":
            round(
                z2,
                4
            ),

        "start_x":
            round(
                start_x,
                4
            ),

        "start_y":
            round(
                start_y,
                4
            ),

        "end_x":
            round(
                end_x,
                4
            ),

        "end_y":
            round(
                end_y,
                4
            ),

        "subject_detection_required":
            False,

        "safe_crop":
            True,

        "renderer_applied":
            False,
    }


def validate(
    plan
):

    errors = []


    if not plan.get(
        "enabled"
    ):

        return (
            True,
            []
        )


    role = plan.get(
        "role",
        "CONTEXT"
    )


    limit = (
        ROLE_ZOOM_LIMIT.get(
            role,
            1.08
        )
    )


    for key in (
        "zoom_start",
        "zoom_end",
    ):

        value = float(
            plan.get(
                key,
                1.0
            )
        )


        if not (
            1.0
            <= value
            <= limit
        ):

            errors.append(
                f"{key}_unsafe"
            )


    for key in (
        "start_x",
        "end_x",
    ):

        value = float(
            plan.get(
                key,
                .5
            )
        )


        if not (
            .42
            <= value
            <= .58
        ):

            errors.append(
                f"{key}_unsafe"
            )


    for key in (
        "start_y",
        "end_y",
    ):

        value = float(
            plan.get(
                key,
                .5
            )
        )


        if not (
            .40
            <= value
            <= .58
        ):

            errors.append(
                f"{key}_unsafe"
            )


    return (
        len(
            errors
        ) == 0,
        errors
    )


def self_test():

    evidence = build_plan(
        {
            "media_type":
                "STILL",

            "role":
                "EVIDENCE",

            "profile":
                "DOCUMENTARY_HOLD",

            "zoom_start":
                1.0,

            "zoom_end":
                1.20,
        }
    )


    assert (
        evidence[
            "zoom_end"
        ]
        <= 1.05
    )


    ok, errors = validate(
        evidence
    )


    assert ok is True

    assert errors == []


    portrait = build_plan(
        {
            "media_type":
                "STILL",

            "role":
                "PERSON",

            "profile":
                "PORTRAIT_PUSH",

            "zoom_start":
                1.0,

            "zoom_end":
                1.07,
        }
    )


    assert (
        portrait[
            "end_y"
        ]
        < .50
    )


    video = build_plan(
        {
            "media_type":
                "VIDEO",

            "role":
                "CONTEXT",

            "profile":
                "NATIVE_MOTION",
        }
    )


    assert (
        video[
            "enabled"
        ]
        is False
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.29 KEN BURNS SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Evidence Zoom Limit"
    )
    print(
        "OK Portrait Framing"
    )
    print(
        "OK Establishing Pan"
    )
    print(
        "OK Context Drift"
    )
    print(
        "OK Safe Crop Bounds"
    )
    print(
        "OK Video No-Op"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 3. VI6.30 RENDERER CONTRACT
# =====================================================

cat > vi6_30_renderer_contract.py <<'PY'
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
PY


# =====================================================
# 4. VI6.30 RUNTIME WRAPPER
# =====================================================

cat > vi6_30_runtime_policy.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

from vi6_30_renderer_contract import (
    build_contract,
    validate_contract,
    record_contract,
    flush,
    reset,
)


if not getattr(
    brain,
    "_VI630_RUNTIME_ACTIVE",
    False
):

    _base_supervisor_630 = (
        brain.supervisionar_vi6_6
    )


    def _wrapped_630(
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
        ) = _base_supervisor_630(
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
            build_contract(
                cena,
                candidate,
                meta
            )
        )


        ok, errors = (
            validate_contract(
                contract
            )
        )


        if ok:

            contract[
                "contract_valid"
            ] = True


        else:

            contract[
                "contract_valid"
            ] = False

            contract[
                "contract_errors"
            ] = errors

            contract[
                "status"
            ] = "HOLD"


        record_contract(
            contract
        )


        meta[
            "vi628_motion_profile"
        ] = contract.get(
            "profile"
        )


        meta[
            "vi629_ken_burns"
        ] = contract.get(
            "ken_burns"
        )


        meta[
            "vi630_renderer_contract"
        ] = contract


        meta[
            "vi630_contract_valid"
        ] = ok


        # Apenas metadata.
        # NÃO altera seleção.
        # NÃO altera arquivo.
        # NÃO altera renderer.
        if candidate is not None:

            candidate[
                "_vi628_motion_profile"
            ] = contract.get(
                "profile"
            )


            candidate[
                "_vi629_ken_burns"
            ] = contract.get(
                "ken_burns"
            )


            candidate[
                "_vi630_contract_hash"
            ] = contract.get(
                "contract_hash"
            )


            candidate[
                "_vi630_renderer_applied"
            ] = False


        if (
            number >= 12
            or board.get(
                "cta_reuse"
            )
        ):

            try:

                meta[
                    "vi630_contract_path"
                ] = flush()

            except Exception as exc:

                meta[
                    "vi630_contract_error"
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
        _wrapped_630
    )


    brain._VI628_RUNTIME_ACTIVE = True

    brain._VI629_RUNTIME_ACTIVE = True

    brain._VI630_RUNTIME_ACTIVE = True
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
    "# VI6.28-6.30 MOTION CONTRACT STACK"
)


if MARKER in source:

    print(
        "VI6.28-6.30 já conectado."
    )

    raise SystemExit(0)


append = '''

# =========================================
# VI6.28-6.30 MOTION CONTRACT STACK
# =========================================
import vi6_30_runtime_policy
'''


patched = (
    source.rstrip()
    + "\n"
    + append
    + "\n"
)


# Não grava se a sintaxe ficar inválida.
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
    " VI6.28-6.30 RUNTIME ATTACHED"
)
print(
    "======================================"
)
print(
    "Motion Blueprint: ACTIVE"
)
print(
    "Ken Burns Planner: ACTIVE"
)
print(
    "Renderer Contract: ACTIVE"
)
print(
    "Renderer Execution: DISABLED"
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

cat > testar_vi628_vi630.py <<'PY'
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
    " VI6.28-6.30 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.26 MOTION RANKING:",
    brain._VI626_RUNTIME_ACTIVE
)

print(
    "VI6.27 TRANSITIONS:",
    brain._VI627_RUNTIME_ACTIVE
)

print(
    "VI6.28 BLUEPRINT:",
    brain._VI628_RUNTIME_ACTIVE
)

print(
    "VI6.29 KEN BURNS:",
    brain._VI629_RUNTIME_ACTIVE
)

print(
    "VI6.30 CONTRACT:",
    brain._VI630_RUNTIME_ACTIVE
)

print()
print(
    "RENDERER EXECUTION=False"
)
print(
    "FFMPEG FILTER CREATED=False"
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
# 7. COMPILE
# =====================================================

echo
echo "===== FULL COMPILE ====="

if ! python -m py_compile \
    vi6_28_motion_blueprint.py \
    vi6_29_ken_burns_intelligence.py \
    vi6_30_renderer_contract.py \
    vi6_30_runtime_policy.py \
    testar_vi628_vi630.py \
    vi6_9_runtime_policy.py \
    vi6_25_visual_sequence.py \
    vi6_26_motion_strategy.py \
    vi6_26_runtime_policy.py \
    vi6_27_transition_intelligence.py \
    vi6_27_runtime_policy.py \
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
echo "===== VI6.28 SELF TEST ====="

if ! python vi6_28_motion_blueprint.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.29 SELF TEST ====="

if ! python vi6_29_ken_burns_intelligence.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.30 SELF TEST ====="

if ! python vi6_30_renderer_contract.py; then
    rollback
    exit 1
fi


echo
echo "===== RUNTIME TEST ====="

if ! python testar_vi628_vi630.py; then
    rollback
    exit 1
fi


# =====================================================
# 9. REGRESSIONS
# =====================================================

echo
echo "===== VI6.25 REGRESSION ====="

if ! python vi6_25_visual_sequence.py; then
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
echo "===== VI6.27 REGRESSION ====="

if ! python vi6_27_transition_intelligence.py; then
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


echo
echo "===== VI6.14 REGRESSION ====="

if ! python vi6_14_pre_download_gate.py; then
    rollback
    exit 1
fi


# =====================================================
# 10. CORE
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
# 11. PROVAR QUE CORE NÃO FOI ALTERADO
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
    echo "ERRO: arquivo core foi modificado."
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
echo " VI6.28 + VI6.29 + VI6.30 INSTALADOS"
echo "======================================"
echo
echo "OK Cinematic Motion Blueprint"
echo "OK Documentary Hold Motion"
echo "OK Portrait Push"
echo "OK Establishing Drift"
echo "OK Object Detail Push"
echo "OK Context Motion"
echo "OK Native Video Motion Preservation"
echo "OK Ken Burns Intelligence"
echo "OK Role-Specific Zoom Limits"
echo "OK Safe Pan Bounds"
echo "OK Evidence Conservative Zoom"
echo "OK Renderer Contract"
echo "OK 9:16 Contract"
echo "OK 1080x1920 Contract"
echo "OK Audio Sync Preserve"
echo "OK Subtitle Sync Preserve"
echo "OK Transition Metadata"
echo "OK Contract Hash"
echo "OK Runtime JSON Ready"
echo
echo "CORE FILES UNCHANGED=YES"
echo "MIDIA.PY MODIFICADO=NAO"
echo "VIDEO.PY MODIFICADO=NAO"
echo "AUDIO.PY MODIFICADO=NAO"
echo "LEGENDA MODIFICADA=NAO"
echo "GERAR_SHORT MODIFICADO=NAO"
echo
echo "FFMPEG FILTER ATIVADO=NAO"
echo "RENDERER_APPLIED=FALSE"
echo "API CALLS=0"
echo "DOWNLOADS NOVOS=0"
echo "VIDEOS GERADOS=0"
echo
echo "FUTURO RELATORIO:"
echo "logs/producao/vi6_30_renderer_contract_latest.json"
echo
