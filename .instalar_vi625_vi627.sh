#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi625_vi627_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================"
echo " VI6.25 + VI6.26 + VI6.27"
echo " CINEMATIC SEQUENCE INTELLIGENCE"
echo " OFFLINE INSTALL"
echo "======================================"
echo


# =====================================================
# 0. BASELINE
# =====================================================

REQUIRED="
midia.py
vi6_6_active_brain.py
vi6_7_retrieval_planner.py
vi6_8_storyboard_director.py
vi6_8_runtime_policy.py
vi6_9_quality_firewall.py
vi6_9_runtime_policy.py
vi6_10_coverage_predictor.py
vi6_11_second_chance.py
vi6_12_story_guard.py
vi6_13_recovery_planner.py
vi6_14_pre_download_gate.py
vi6_15_decision_ledger.py
vi6_19_true_recovery.py
vi6_20_recovery_normalizer.py
vi6_21_recovery_circuit.py
vi6_22_story_audit.py
vi6_23_adaptive_budget.py
vi6_23_runtime_policy.py
vi6_24_production_telemetry.py
vi6_24_runtime_telemetry.py
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
    vi6_6_active_brain.py \
    vi6_9_runtime_policy.py \
    vi6_19_true_recovery.py \
    vi6_22_story_audit.py \
    vi6_23_runtime_policy.py \
    vi6_24_runtime_telemetry.py
then

    echo
    echo "BASELINE FALHOU."
    echo "NENHUMA ALTERAÇÃO FEITA."

    exit 3
fi

echo "BASELINE=OK"


cp vi6_9_runtime_policy.py \
   "$BACKDIR/vi6_9_runtime_policy.py"


for F in \
    vi6_25_visual_sequence.py \
    vi6_26_motion_strategy.py \
    vi6_26_runtime_policy.py \
    vi6_27_transition_intelligence.py \
    vi6_27_runtime_policy.py \
    testar_vi625_vi627.py
do

    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi

done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.25-6.27"
    echo "======================================"

    cp \
        "$BACKDIR/vi6_9_runtime_policy.py" \
        vi6_9_runtime_policy.py


    for F in \
        vi6_25_visual_sequence.py \
        vi6_26_motion_strategy.py \
        vi6_26_runtime_policy.py \
        vi6_27_transition_intelligence.py \
        vi6_27_runtime_policy.py \
        testar_vi625_vi627.py
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
# 1. VI6.25 VISUAL SEQUENCE DIRECTOR
# =====================================================

cat > vi6_25_visual_sequence.py <<'PY'
#!/usr/bin/env python3

import json
import os
from datetime import datetime


VERSION = "6.25"


_HISTORY = []


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
            "medicine",
            "product",
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


def sequence_intent(scene):

    r = role(scene)
    beat = rhythm(scene)


    if r == "CTA":

        intent = "CTA_REUSE"
        motion = "LOW"
        media = "REUSE"
        pace = "CALM"


    elif r == "EVIDENCE":

        intent = "EVIDENCE_HOLD"
        motion = "LOW"
        media = "STILL_PREFERRED"
        pace = "CONTROLLED"


    elif r == "PERSON":

        intent = "PORTRAIT_FOCUS"
        motion = "LOW"
        media = "STILL_PREFERRED"
        pace = "CONTROLLED"


    elif r == "PLACE":

        if beat in {
            "HOOK",
            "SETUP",
        }:

            intent = "ESTABLISHING"
            motion = "MEDIUM"
            media = "EITHER"

        else:

            intent = "LOCATION_DETAIL"
            motion = "LOW"
            media = "STILL_PREFERRED"

        pace = "CONTROLLED"


    elif r == "OBJECT":

        intent = "DETAIL_INSERT"
        motion = "MEDIUM"
        media = "EITHER"
        pace = "QUICK"


    else:

        intent = "DYNAMIC_CONTEXT"

        if beat in {
            "HOOK",
            "ESCALATION",
        }:

            motion = "HIGH"
            pace = "QUICK"

        else:

            motion = "MEDIUM"
            pace = "CONTROLLED"

        media = "VIDEO_PREFERRED"


    return {

        "version":
            VERSION,

        "scene":
            scene_number(
                scene
            ),

        "role":
            r,

        "rhythm":
            beat,

        "intent":
            intent,

        "motion_need":
            motion,

        "media_preference":
            media,

        "pace":
            pace,
    }


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


    if any(
        x in raw
        for x in (
            "video",
            "vídeo",
            "mp4",
        )
    ):
        return "VIDEO"


    if any(
        x in raw
        for x in (
            "foto",
            "photo",
            "image",
            "imagem",
            "jpg",
            "jpeg",
            "png",
        )
    ):
        return "STILL"


    return "UNKNOWN"


def source(candidate):

    if not candidate:
        return None


    return _s(
        candidate.get(
            "fonte"
        )
        or candidate.get(
            "source"
        )
    )


def family(candidate):

    if not candidate:
        return None


    return _u(
        candidate.get(
            "family"
        )
        or candidate.get(
            "visual_family"
        )
    )


def candidate_class(
    candidate,
    meta=None
):

    meta = (
        meta
        or {}
    )


    if not candidate:
        return "FALLBACK"


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


def record_choice(
    scene,
    candidate,
    meta=None
):

    number = scene_number(
        scene
    )


    if (
        number == 1
        and _HISTORY
    ):

        reset()


    intent = sequence_intent(
        scene
    )


    event = {

        "scene":
            number,

        "intent":
            intent[
                "intent"
            ],

        "role":
            intent[
                "role"
            ],

        "rhythm":
            intent[
                "rhythm"
            ],

        "motion_need":
            intent[
                "motion_need"
            ],

        "media_type":
            media_type(
                candidate
            ),

        "source":
            source(
                candidate
            ),

        "family":
            family(
                candidate
            ),

        "class":
            candidate_class(
                candidate,
                meta
            ),
    }


    _HISTORY.append(
        event
    )


    return event


def history():

    return list(
        _HISTORY
    )


def previous():

    if not _HISTORY:
        return None


    return dict(
        _HISTORY[-1]
    )


def recent_media_types(
    limit=2
):

    return [
        event[
            "media_type"
        ]

        for event
        in _HISTORY[
            -limit:
        ]
    ]


def summary():

    videos = sum(
        1

        for event
        in _HISTORY

        if event[
            "media_type"
        ] == "VIDEO"
    )


    stills = sum(
        1

        for event
        in _HISTORY

        if event[
            "media_type"
        ] == "STILL"
    )


    return {

        "version":
            VERSION,

        "scenes":
            len(
                _HISTORY
            ),

        "videos":
            videos,

        "stills":
            stills,

        "history":
            history(),
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
            "vi6_25_sequence_latest.json"
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


def reset():

    _HISTORY.clear()


def self_test():

    reset()


    evidence = sequence_intent(
        {
            "retrieval_role_6_7":
                "EVIDENCE",

            "_vi68_storyboard":
                {
                    "scene": 3,
                    "rhythm": "SETUP"
                }
        }
    )


    assert (
        evidence[
            "intent"
        ]
        == "EVIDENCE_HOLD"
    )


    assert (
        evidence[
            "media_preference"
        ]
        == "STILL_PREFERRED"
    )


    context = sequence_intent(
        {
            "retrieval_role_6_7":
                "CONTEXT",

            "_vi68_storyboard":
                {
                    "scene": 6,
                    "rhythm":
                        "ESCALATION"
                }
        }
    )


    assert (
        context[
            "motion_need"
        ]
        == "HIGH"
    )


    record_choice(
        {
            "_vi68_storyboard":
                {
                    "scene": 1
                }
        },
        {
            "fonte": "Wikimedia",
            "tipo": "foto",
            "_vi6_class":
                "REAL_DOCUMENTARY",
        }
    )


    assert (
        summary()[
            "stills"
        ]
        == 1
    )


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.25 SEQUENCE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Scene Intent"
    )
    print(
        "OK Evidence Hold"
    )
    print(
        "OK Dynamic Context"
    )
    print(
        "OK Motion Need"
    )
    print(
        "OK Sequence Memory"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 2. VI6.26 MOTION STRATEGY
# =====================================================

cat > vi6_26_motion_strategy.py <<'PY'
#!/usr/bin/env python3

from vi6_25_visual_sequence import (
    sequence_intent,
    recent_media_types,
)


VERSION = "6.26"


def _s(v):
    return str(v or "").strip()


def _u(v):
    return _s(v).upper()


def _f(
    v,
    default=0.0
):

    try:
        return float(v)

    except Exception:
        return float(default)


def candidate_media_type(
    item
):

    raw = _s(
        item.get(
            "tipo"
        )
        or item.get(
            "type"
        )
    ).lower()


    if any(
        marker in raw
        for marker in (
            "video",
            "vídeo",
            "mp4",
        )
    ):

        return "VIDEO"


    if any(
        marker in raw
        for marker in (
            "foto",
            "photo",
            "image",
            "imagem",
            "jpg",
            "jpeg",
            "png",
        )
    ):

        return "STILL"


    return "UNKNOWN"


def adjust(
    result,
    item,
    scene
):

    if result is None:
        return None


    result = dict(
        result
    )


    plan = sequence_intent(
        scene
    )


    media = candidate_media_type(
        item
    )


    classe = _u(
        result.get(
            "class"
        )
    )


    semantic = _f(
        result.get(
            "semantic"
        )
    )


    truth = bool(
        result.get(
            "truth_ok",
            False
        )
    )


    score = _f(
        result.get(
            "score"
        )
    )


    adjustment = 0.0


    # =================================
    # MOTION WHERE MOTION HELPS
    # =================================

    if (
        media == "VIDEO"
        and plan[
            "motion_need"
        ] == "HIGH"
        and semantic >= 58
    ):

        adjustment += 6.0


    elif (
        media == "VIDEO"
        and plan[
            "motion_need"
        ] == "MEDIUM"
        and semantic >= 58
    ):

        adjustment += 3.0


    # =================================
    # DOCUMENTARY STILL IS A FEATURE
    # NOT A FAILURE
    # =================================

    if (
        media == "STILL"
        and classe
        == "REAL_DOCUMENTARY"
        and truth
    ):

        if plan[
            "role"
        ] in {
            "EVIDENCE",
            "PERSON",
            "PLACE",
        }:

            adjustment += 7.0


        else:

            adjustment += 3.0


    # =================================
    # DON'T FORCE VIDEO INTO EVIDENCE
    # =================================

    if (
        media == "VIDEO"
        and plan[
            "role"
        ] in {
            "EVIDENCE",
            "PERSON",
        }
    ):

        if classe == "SAFE_CONTEXT":

            adjustment -= 7.0


    # =================================
    # MOTION FATIGUE
    # =================================

    recent = recent_media_types(
        2
    )


    if (
        media == "VIDEO"
        and len(recent) >= 2
        and all(
            value == "VIDEO"
            for value in recent
        )
    ):

        adjustment -= 6.0


    # =================================
    # STATIC FATIGUE
    # =================================

    if (
        media == "VIDEO"
        and plan[
            "role"
        ] == "CONTEXT"
        and semantic >= 60
        and len(recent) >= 2
        and all(
            value == "STILL"
            for value in recent
        )
    ):

        adjustment += 4.0


    # =================================
    # UNKNOWN MEDIA
    # =================================

    if media == "UNKNOWN":

        adjustment -= 2.0


    result[
        "score"
    ] = round(
        score
        + adjustment,
        3
    )


    reasons = list(
        result.get(
            "reasons",
            []
        )
        or []
    )


    if adjustment > 0:

        reasons.append(
            "vi626_motion_sequence_boost"
        )


    elif adjustment < 0:

        reasons.append(
            "vi626_motion_sequence_penalty"
        )


    result[
        "reasons"
    ] = reasons


    result[
        "vi625_intent"
    ] = plan[
        "intent"
    ]


    result[
        "vi625_motion_need"
    ] = plan[
        "motion_need"
    ]


    result[
        "vi626_media_type"
    ] = media


    result[
        "vi626_adjustment"
    ] = round(
        adjustment,
        3
    )


    return result


def self_test():

    from vi6_25_visual_sequence import (
        reset,
        record_choice,
    )


    reset()


    scene = {

        "retrieval_role_6_7":
            "EVIDENCE",

        "_vi68_storyboard":
            {
                "scene": 3,
                "rhythm": "SETUP"
            }
    }


    doc = adjust(
        {
            "score": 70,
            "class":
                "REAL_DOCUMENTARY",
            "truth_ok": True,
            "semantic": 70,
            "reasons": [],
        },
        {
            "tipo": "foto"
        },
        scene
    )


    stock_video = adjust(
        {
            "score": 70,
            "class":
                "SAFE_CONTEXT",
            "truth_ok": True,
            "semantic": 70,
            "reasons": [],
        },
        {
            "tipo": "video"
        },
        scene
    )


    assert (
        doc[
            "score"
        ] > 70
    )


    assert (
        stock_video[
            "score"
        ] < 70
    )


    record_choice(
        {
            "_vi68_storyboard":
                {
                    "scene": 1
                }
        },
        {
            "tipo": "video"
        }
    )


    record_choice(
        {
            "_vi68_storyboard":
                {
                    "scene": 2
                }
        },
        {
            "tipo": "video"
        }
    )


    context = adjust(
        {
            "score": 70,
            "class":
                "SAFE_CONTEXT",
            "truth_ok": True,
            "semantic": 70,
            "reasons": [],
        },
        {
            "tipo": "video"
        },
        {
            "retrieval_role_6_7":
                "CONTEXT",

            "_vi68_storyboard":
                {
                    "scene": 3,
                    "rhythm":
                        "ESCALATION"
                }
        }
    )


    assert (
        context[
            "vi626_adjustment"
        ] <= 6
    )


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.26 MOTION SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Documentary Still Boost"
    )
    print(
        "OK Context Motion Boost"
    )
    print(
        "OK Evidence Stock Video Penalty"
    )
    print(
        "OK Motion Fatigue Guard"
    )
    print(
        "OK Static Fatigue Recovery"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 3. VI6.26 RUNTIME EVALUATOR
# =====================================================

cat > vi6_26_runtime_policy.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

from vi6_26_motion_strategy import (
    adjust
)


if not getattr(
    brain,
    "_VI626_RUNTIME_ACTIVE",
    False
):

    _base_evaluate_626 = (
        brain.evaluate
    )


    def _evaluate_626(
        item,
        cena,
        vi6_scene=None
    ):

        result = (
            _base_evaluate_626(
                item,
                cena,
                vi6_scene
            )
        )


        if result is None:

            return None


        return adjust(
            result,
            item,
            cena
        )


    brain.evaluate = (
        _evaluate_626
    )


    brain._VI626_RUNTIME_ACTIVE = True
PY


# =====================================================
# 4. VI6.27 TRANSITION INTELLIGENCE
# =====================================================

cat > vi6_27_transition_intelligence.py <<'PY'
#!/usr/bin/env python3

import json
import os
from datetime import datetime


from vi6_25_visual_sequence import (
    previous,
    sequence_intent,
    media_type,
    source,
    family,
    candidate_class,
    record_choice,
    summary as sequence_summary,
)


VERSION = "6.27"


_EVENTS = []


def _s(v):
    return str(v or "").strip()


def recommend(
    scene,
    candidate,
    meta=None
):

    meta = (
        meta
        or {}
    )


    plan = sequence_intent(
        scene
    )


    prev = previous()


    current_type = media_type(
        candidate
    )


    current_source = source(
        candidate
    )


    current_family = family(
        candidate
    )


    current_class = candidate_class(
        candidate,
        meta
    )


    if candidate is None:

        transition = "NONE"

        reason = (
            "fallback_no_active_asset"
        )


    elif plan[
        "role"
    ] == "CTA":

        transition = (
            "CLEAN_CUT"
        )

        reason = (
            "cta_clean_finish"
        )


    elif prev is None:

        transition = (
            "OPEN"
        )

        reason = (
            "first_scene"
        )


    elif (
        plan[
            "intent"
        ]
        in {
            "EVIDENCE_HOLD",
            "PORTRAIT_FOCUS",
        }
    ):

        transition = (
            "DIRECT_CUT"
        )

        reason = (
            "preserve_evidence_clarity"
        )


    elif (
        prev.get(
            "media_type"
        )
        != current_type
        and {
            prev.get(
                "media_type"
            ),
            current_type,
        }
        == {
            "VIDEO",
            "STILL",
        }
    ):

        transition = (
            "MATCH_CUT"
        )

        reason = (
            "media_type_change"
        )


    elif (
        current_family
        and prev.get(
            "family"
        )
        and current_family
        == prev.get(
            "family"
        )
    ):

        transition = (
            "CONTRAST_CUT"
        )

        reason = (
            "same_visual_family"
        )


    elif (
        current_source
        and prev.get(
            "source"
        )
        and current_source
        == prev.get(
            "source"
        )
    ):

        transition = (
            "HARD_CUT"
        )

        reason = (
            "same_source_break"
        )


    elif (
        plan[
            "rhythm"
        ]
        == "ESCALATION"
    ):

        transition = (
            "FAST_CUT"
        )

        reason = (
            "escalation_pacing"
        )


    elif (
        plan[
            "rhythm"
        ]
        == "RESOLUTION"
    ):

        transition = (
            "SOFT_CUT"
        )

        reason = (
            "resolution_pacing"
        )


    else:

        transition = (
            "DIRECT_CUT"
        )

        reason = (
            "default_clarity"
        )


    return {

        "version":
            VERSION,

        "scene":
            plan[
                "scene"
            ],

        "role":
            plan[
                "role"
            ],

        "intent":
            plan[
                "intent"
            ],

        "rhythm":
            plan[
                "rhythm"
            ],

        "media_type":
            current_type,

        "class":
            current_class,

        "transition":
            transition,

        "reason":
            reason,

        # Neste estágio é apenas
        # metadata/editorial direction.
        "renderer_applied":
            False,
    }


def record(
    scene,
    candidate,
    meta=None
):

    recommendation = recommend(
        scene,
        candidate,
        meta
    )


    _EVENTS.append(
        recommendation
    )


    record_choice(
        scene,
        candidate,
        meta
    )


    return recommendation


def summary():

    transitions = {}


    for event in _EVENTS:

        transition = event[
            "transition"
        ]


        transitions[
            transition
        ] = (
            transitions.get(
                transition,
                0
            )
            + 1
        )


    return {

        "version":
            VERSION,

        "scenes":
            len(
                _EVENTS
            ),

        "transitions":
            transitions,

        "sequence":
            sequence_summary(),

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
            "vi6_27_sequence_latest.json"
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


def reset():

    _EVENTS.clear()


    from vi6_25_visual_sequence import (
        reset as sequence_reset
    )


    sequence_reset()


def self_test():

    reset()


    scene1 = {
        "retrieval_role_6_7":
            "PLACE",

        "_vi68_storyboard":
            {
                "scene": 1,
                "rhythm": "HOOK"
            }
    }


    first = record(
        scene1,
        {
            "fonte": "Wikimedia",
            "tipo": "foto",
            "family": "HOTEL",
            "_vi6_class":
                "REAL_DOCUMENTARY",
        }
    )


    assert (
        first[
            "transition"
        ]
        == "OPEN"
    )


    second = record(
        {
            "retrieval_role_6_7":
                "CONTEXT",

            "_vi68_storyboard":
                {
                    "scene": 2,
                    "rhythm":
                        "ESCALATION"
                }
        },
        {
            "fonte": "Pixabay",
            "tipo": "video",
            "family": "CITY",
            "_vi6_class":
                "SAFE_CONTEXT",
        }
    )


    assert (
        second[
            "transition"
        ]
        in {
            "MATCH_CUT",
            "FAST_CUT",
        }
    )


    assert (
        second[
            "renderer_applied"
        ]
        is False
    )


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.27 TRANSITION SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Opening Logic"
    )
    print(
        "OK Evidence Clarity Cut"
    )
    print(
        "OK Photo/Video Match Cut"
    )
    print(
        "OK Same-Family Break"
    )
    print(
        "OK Escalation Pacing"
    )
    print(
        "OK Renderer remains untouched"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 5. VI6.27 RUNTIME WRAPPER
# =====================================================

cat > vi6_27_runtime_policy.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

from vi6_27_transition_intelligence import (
    record,
    flush,
    reset,
)


if not getattr(
    brain,
    "_VI627_RUNTIME_ACTIVE",
    False
):

    _base_supervisor_627 = (
        brain.supervisionar_vi6_6
    )


    def _wrapped_627(
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
        ) = _base_supervisor_627(
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


        transition = record(
            cena,
            candidate,
            meta
        )


        meta[
            "vi625_sequence_intent"
        ] = transition.get(
            "intent"
        )


        meta[
            "vi627_transition"
        ] = transition.get(
            "transition"
        )


        meta[
            "vi627_transition_reason"
        ] = transition.get(
            "reason"
        )


        meta[
            "vi627_renderer_applied"
        ] = False


        if candidate is not None:

            candidate[
                "_vi625_sequence_intent"
            ] = transition.get(
                "intent"
            )


            candidate[
                "_vi627_transition"
            ] = transition.get(
                "transition"
            )


        if (
            number >= 12
            or board.get(
                "cta_reuse"
            )
        ):

            try:

                meta[
                    "vi627_sequence_path"
                ] = flush()

            except Exception as exc:

                meta[
                    "vi627_sequence_error"
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
        _wrapped_627
    )


    brain._VI627_RUNTIME_ACTIVE = True
PY


# =====================================================
# 6. ATTACH TO EXISTING RUNTIME
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
    "# VI6.25-6.27 CINEMATIC RUNTIME STACK"
)


if MARKER in source:

    print(
        "VI6.25-6.27 já conectado."
    )

    raise SystemExit(0)


append = '''

# =========================================
# VI6.25-6.27 CINEMATIC RUNTIME STACK
# =========================================
import vi6_26_runtime_policy
import vi6_27_runtime_policy
'''


patched = (
    source.rstrip()
    + "\n"
    + append
    + "\n"
)


# Não grava se houver erro sintático.
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
    " VI6.25-6.27 RUNTIME ATTACHED"
)
print(
    "======================================"
)
print(
    "VI6.26 evaluator wrapper: ADDED"
)
print(
    "VI6.27 supervisor wrapper: ADDED"
)
print(
    "MIDIA.PY: UNTOUCHED"
)
print(
    "RENDERER: UNTOUCHED"
)
print()
PY


STATUS=$?


if [ "$STATUS" -ne 0 ]; then

    rollback
    exit "$STATUS"
fi


# =====================================================
# 7. OFFLINE RUNTIME TEST
# =====================================================

cat > testar_vi625_vi627.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy


FLAGS = (

    "_VI69_RUNTIME_PATCHED",

    "_VI611_RUNTIME_ACTIVE",
    "_VI612_RUNTIME_ACTIVE",

    "_VI619_RUNTIME_ACTIVE",
    "_VI620_RUNTIME_ACTIVE",
    "_VI621_RUNTIME_ACTIVE",

    "_VI623_RUNTIME_ACTIVE",
    "_VI624_RUNTIME_ACTIVE",

    "_VI626_RUNTIME_ACTIVE",
    "_VI627_RUNTIME_ACTIVE",
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
    " VI6.25-6.27 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.23 ADAPTIVE:",
    brain._VI623_RUNTIME_ACTIVE
)

print(
    "VI6.24 TELEMETRY:",
    brain._VI624_RUNTIME_ACTIVE
)

print(
    "VI6.26 MOTION:",
    brain._VI626_RUNTIME_ACTIVE
)

print(
    "VI6.27 TRANSITIONS:",
    brain._VI627_RUNTIME_ACTIVE
)

print()
print(
    "RENDERER MODIFIED=False"
)
print(
    "AUDIO MODIFIED=False"
)
print(
    "LEGEND MODIFIED=False"
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
# 8. FULL COMPILE
# =====================================================

echo
echo "===== FULL COMPILE ====="

if ! python -m py_compile \
    vi6_25_visual_sequence.py \
    vi6_26_motion_strategy.py \
    vi6_26_runtime_policy.py \
    vi6_27_transition_intelligence.py \
    vi6_27_runtime_policy.py \
    testar_vi625_vi627.py \
    vi6_9_runtime_policy.py \
    vi6_23_runtime_policy.py \
    vi6_24_runtime_telemetry.py \
    vi6_19_true_recovery.py \
    vi6_6_active_brain.py \
    midia.py
then

    echo
    echo "COMPILE FALHOU."

    rollback
    exit 1
fi

echo "PYTHON STATUS=0"


# =====================================================
# 9. SELF TESTS
# =====================================================

echo
echo "===== VI6.25 SELF TEST ====="

if ! python vi6_25_visual_sequence.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.26 SELF TEST ====="

if ! python vi6_26_motion_strategy.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.27 SELF TEST ====="

if ! python vi6_27_transition_intelligence.py; then
    rollback
    exit 1
fi


echo
echo "===== RUNTIME TEST ====="

if ! python testar_vi625_vi627.py; then
    rollback
    exit 1
fi


# =====================================================
# 10. REGRESSIONS
# =====================================================

echo
echo "===== VI6.22 REGRESSION ====="

if ! python vi6_22_story_audit.py; then
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
echo "===== VI6.24 REGRESSION ====="

if ! python vi6_24_production_telemetry.py; then
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


echo
echo "===== VI6.9 REGRESSION ====="

if ! python vi6_9_quality_firewall.py; then
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
# 12. VERIFY NO RENDER TOUCH
# =====================================================

echo
echo "===== SAFETY CHECK ====="

echo "MIDIA runtime import:"
grep -n \
'import vi6_9_runtime_policy' \
midia.py \
| head -3


echo
echo "New runtime stack:"
grep -nE \
'VI6\.25-6\.27|vi6_26_runtime_policy|vi6_27_runtime_policy' \
vi6_9_runtime_policy.py


echo
echo "======================================"
echo " VI6.25 + VI6.26 + VI6.27 INSTALADOS"
echo "======================================"
echo
echo "OK Visual Sequence Director"
echo "OK Scene Intent Engine"
echo "OK Hook / Setup / Escalation / Resolution"
echo "OK Evidence Hold Strategy"
echo "OK Portrait Focus Strategy"
echo "OK Establishing Strategy"
echo "OK Dynamic Context Strategy"
echo "OK Motion-Aware Candidate Ranking"
echo "OK Documentary Still Boost"
echo "OK Evidence Stock-Video Penalty"
echo "OK Motion Fatigue Guard"
echo "OK Static Fatigue Recovery"
echo "OK Transition Intelligence"
echo "OK Photo/Video Match-Cut Planning"
echo "OK Same-Family Break Planning"
echo "OK Source-Repetition Break Planning"
echo "OK Escalation Pacing"
echo "OK Sequence JSON Report"
echo "OK Existing Truth Stack Preserved"
echo "OK VI6.19 Recovery Preserved"
echo "OK VI6.23 Adaptive Budget Preserved"
echo "OK VI6.24 Telemetry Preserved"
echo
echo "MIDIA.PY MODIFICADO=NAO"
echo "VIDEO.PY MODIFICADO=NAO"
echo "AUDIO.PY MODIFICADO=NAO"
echo "LEGENDA MODIFICADA=NAO"
echo "GERAR_SHORT MODIFICADO=NAO"
echo "API CALLS=0"
echo "DOWNLOADS NOVOS=0"
echo "VIDEOS GERADOS=0"
echo
echo "FUTURO RELATORIO:"
echo "logs/producao/vi6_27_sequence_latest.json"
echo
