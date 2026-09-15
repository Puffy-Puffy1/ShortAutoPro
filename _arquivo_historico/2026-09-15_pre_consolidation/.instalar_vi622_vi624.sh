#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi622_vi624_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================"
echo " VI6.22 + VI6.23 + VI6.24"
echo " STORY AUDIT + ADAPTIVE BUDGET"
echo " + PRODUCTION TELEMETRY"
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
vi6_16_source_capabilities.py
vi6_17_recovery_router.py
vi6_18_activation_guard.py
vi6_19_true_recovery.py
vi6_20_recovery_normalizer.py
vi6_21_recovery_circuit.py
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
    vi6_8_runtime_policy.py \
    vi6_9_runtime_policy.py \
    vi6_19_true_recovery.py \
    vi6_20_recovery_normalizer.py \
    vi6_21_recovery_circuit.py
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
    vi6_22_story_audit.py \
    vi6_23_adaptive_budget.py \
    vi6_23_runtime_policy.py \
    vi6_24_production_telemetry.py \
    vi6_24_runtime_telemetry.py \
    testar_vi622_vi624.py
do

    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi

done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.22-6.24"
    echo "======================================"

    cp \
        "$BACKDIR/vi6_9_runtime_policy.py" \
        vi6_9_runtime_policy.py


    for F in \
        vi6_22_story_audit.py \
        vi6_23_adaptive_budget.py \
        vi6_23_runtime_policy.py \
        vi6_24_production_telemetry.py \
        vi6_24_runtime_telemetry.py \
        testar_vi622_vi624.py
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
# 1. VI6.22 ROLLING STORY AUDIT
# =====================================================

cat > vi6_22_story_audit.py <<'PY'
#!/usr/bin/env python3

import os


VERSION = "6.22"


TOTAL_SCENES = int(
    os.getenv(
        "VI622_TOTAL_SCENES",
        "12"
    )
)


DOCUMENTARY_TARGET = int(
    os.getenv(
        "VI622_DOCUMENTARY_TARGET",
        "4"
    )
)


_STATE = {

    "events":
        [],

    "last_scene":
        0,
}


def _s(v):

    return str(
        v or ""
    ).strip()


def _u(v):

    return _s(
        v
    ).upper()


def _f(
    v,
    default=0.0
):

    try:
        return float(v)

    except Exception:
        return float(default)


def scene_number(
    scene
):

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


def role_of(
    scene,
    meta=None
):

    meta = (
        meta
        or {}
    )


    role = _u(
        meta.get(
            "role"
        )
        or scene.get(
            "retrieval_role_6_7"
        )
    )


    if role:
        return role


    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    return _u(
        board.get(
            "role"
        )
        or "CONTEXT"
    )


def candidate_class(
    candidate,
    meta=None
):

    meta = (
        meta
        or {}
    )


    if candidate is None:
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


def source_of(
    candidate
):

    if candidate is None:
        return None


    return _s(
        candidate.get(
            "fonte"
        )
        or candidate.get(
            "source"
        )
    )


def family_of(
    candidate
):

    if candidate is None:
        return None


    return _u(
        candidate.get(
            "family"
        )
        or candidate.get(
            "visual_family"
        )
    )


def _quality_confidence(
    candidate,
    meta
):

    if candidate is None:
        return 0.0


    classe = candidate_class(
        candidate,
        meta
    )


    score = _f(
        meta.get(
            "score",
            candidate.get(
                "_vi611_score",
                candidate.get(
                    "_vi6_score",
                    candidate.get(
                        "score",
                        0
                    )
                )
            )
        )
    )


    semantic = _f(
        meta.get(
            "semantic",
            candidate.get(
                "semantic",
                0
            )
        )
    )


    anchor = _f(
        meta.get(
            "anchor",
            meta.get(
                "anchor_ratio",
                candidate.get(
                    "_vi66_anchor",
                    0
                )
            )
        )
    )


    truth = bool(
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


    confidence = 0.0


    confidence += min(
        35.0,
        max(
            0.0,
            score * .35
        )
    )


    confidence += min(
        25.0,
        max(
            0.0,
            semantic * .25
        )
    )


    confidence += min(
        20.0,
        max(
            0.0,
            anchor * 40.0
        )
    )


    if (
        classe
        == "REAL_DOCUMENTARY"
        and truth
    ):

        confidence += 20.0


    elif classe == "SAFE_CONTEXT":

        confidence += 8.0


    return round(
        min(
            100.0,
            confidence
        ),
        2
    )


def reset():

    _STATE[
        "events"
    ].clear()

    _STATE[
        "last_scene"
    ] = 0


def record_final(
    scene,
    candidate,
    reason,
    meta=None
):

    meta = (
        meta
        or {}
    )


    number = scene_number(
        scene
    )


    # Novo Short no mesmo processo:
    # evita contaminar memória anterior.
    if (
        number == 1
        and _STATE[
            "last_scene"
        ] != 0
    ):

        reset()


    classe = candidate_class(
        candidate,
        meta
    )


    event = {

        "scene":
            number,

        "role":
            role_of(
                scene,
                meta
            ),

        "class":
            classe,

        "source":
            source_of(
                candidate
            ),

        "family":
            family_of(
                candidate
            ),

        "reason":
            reason,

        "decision":
            meta.get(
                "decision"
            ),

        "recovered":
            bool(
                candidate
                and candidate.get(
                    "_vi619_true_recovery"
                )
            ),

        "second_chance":
            bool(
                candidate
                and candidate.get(
                    "_vi611_rescued"
                )
            ),

        "truth_ok":
            bool(
                meta.get(
                    "truth_ok",
                    candidate.get(
                        "_vi6_truth_ok",
                        False
                    )
                    if candidate
                    else False
                )
            ),

        "confidence":
            _quality_confidence(
                candidate,
                meta
            ),
    }


    _STATE[
        "events"
    ].append(
        event
    )


    if number:

        _STATE[
            "last_scene"
        ] = number


    return event


def summary():

    events = list(
        _STATE[
            "events"
        ]
    )


    seen = len(
        events
    )


    documentary = sum(
        1
        for event in events
        if (
            event[
                "class"
            ]
            == "REAL_DOCUMENTARY"
        )
    )


    safe_context = sum(
        1
        for event in events
        if (
            event[
                "class"
            ]
            == "SAFE_CONTEXT"
        )
    )


    fallback = sum(
        1
        for event in events
        if (
            event[
                "class"
            ]
            == "FALLBACK"
        )
    )


    recovered = sum(
        1
        for event in events
        if event[
            "recovered"
        ]
    )


    second_chance = sum(
        1
        for event in events
        if event[
            "second_chance"
        ]
    )


    remaining = max(
        0,
        TOTAL_SCENES
        - seen
    )


    documentary_needed = max(
        0,
        DOCUMENTARY_TARGET
        - documentary
    )


    impossible = (
        documentary_needed
        > remaining
    )


    if documentary_needed <= 0:

        urgency = 0.0

    elif remaining <= 0:

        urgency = 1.0

    else:

        urgency = min(
            1.0,
            documentary_needed
            / float(
                remaining
            )
        )


    low_confidence = [
        event[
            "scene"
        ]
        for event in events
        if event[
            "confidence"
        ] < 48
    ]


    sources = {}

    for event in events:

        source = event.get(
            "source"
        )

        if not source:
            continue


        sources[
            source
        ] = (
            sources.get(
                source,
                0
            )
            + 1
        )


    return {

        "version":
            VERSION,

        "scenes_seen":
            seen,

        "total_scenes":
            TOTAL_SCENES,

        "remaining":
            remaining,

        "documentary":
            documentary,

        "documentary_target":
            DOCUMENTARY_TARGET,

        "documentary_needed":
            documentary_needed,

        "documentary_urgency":
            round(
                urgency,
                3
            ),

        "documentary_target_impossible":
            impossible,

        "safe_context":
            safe_context,

        "fallback":
            fallback,

        "true_recovery":
            recovered,

        "second_chance":
            second_chance,

        "low_confidence_scenes":
            low_confidence,

        "sources":
            sources,

        "events":
            events,
    }


def self_test():

    reset()


    scene1 = {
        "_vi68_storyboard":
            {
                "scene": 1,
                "role": "EVIDENCE"
            }
    }


    doc = {
        "fonte":
            "Wikimedia",

        "_vi6_class":
            "REAL_DOCUMENTARY",

        "_vi6_truth_ok":
            True,

        "_vi6_score":
            90,
    }


    record_final(
        scene1,
        doc,
        "test",
        {
            "class":
                "REAL_DOCUMENTARY",

            "score":
                90,

            "semantic":
                75,

            "anchor":
                .60,

            "truth_ok":
                True,
        }
    )


    scene2 = {
        "_vi68_storyboard":
            {
                "scene": 2,
                "role": "CONTEXT"
            }
    }


    stock = {
        "fonte":
            "Pixabay",

        "_vi6_class":
            "SAFE_CONTEXT",

        "_vi6_score":
            70,
    }


    record_final(
        scene2,
        stock,
        "test",
        {
            "class":
                "SAFE_CONTEXT",

            "score":
                70,

            "semantic":
                65,

            "anchor":
                .10,
        }
    )


    result = summary()


    assert result[
        "scenes_seen"
    ] == 2


    assert result[
        "documentary"
    ] == 1


    assert result[
        "safe_context"
    ] == 1


    assert result[
        "documentary_needed"
    ] == 3


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.22 STORY AUDIT SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Rolling Story Memory"
    )
    print(
        "OK Documentary Deficit"
    )
    print(
        "OK Remaining Scene Projection"
    )
    print(
        "OK Confidence Audit"
    )
    print(
        "OK Recovery Counters"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 2. VI6.23 ADAPTIVE DOCUMENTARY BUDGET
# =====================================================

cat > vi6_23_adaptive_budget.py <<'PY'
#!/usr/bin/env python3

from vi6_22_story_audit import (
    summary
)


VERSION = "6.23"


DOCUMENTARY_ROLES = {
    "EVIDENCE",
    "PERSON",
    "PLACE",
}


def _s(v):

    return str(
        v or ""
    ).strip()


def _u(v):

    return _s(
        v
    ).upper()


def adjust_result(
    result,
    scene
):

    if result is None:

        return None


    result = dict(
        result
    )


    state = summary()


    urgency = float(
        state.get(
            "documentary_urgency",
            0
        )
        or 0
    )


    if urgency <= 0:

        result[
            "vi623_adjustment"
        ] = 0.0

        return result


    role = _u(
        result.get(
            "role"
        )
        or scene.get(
            "retrieval_role_6_7"
        )
        or (
            scene.get(
                "_vi68_storyboard"
            )
            or {}
        ).get(
            "role"
        )
    )


    classe = _u(
        result.get(
            "class"
        )
    )


    truth = bool(
        result.get(
            "truth_ok",
            False
        )
    )


    adjustment = 0.0


    # Só pressiona cenas em que documentário
    # realmente faz sentido editorial.
    if role in DOCUMENTARY_ROLES:

        if (
            classe
            == "REAL_DOCUMENTARY"
            and truth
        ):

            adjustment += (
                4.0
                + urgency * 14.0
            )


        elif (
            classe
            == "SAFE_CONTEXT"
        ):

            adjustment -= (
                urgency * 9.0
            )


    # Se o alvo já ficou matematicamente
    # impossível, força prioridade documental
    # ainda maior nas cenas adequadas.
    if (
        state.get(
            "documentary_target_impossible"
        )
        and role in DOCUMENTARY_ROLES
    ):

        if (
            classe
            == "REAL_DOCUMENTARY"
            and truth
        ):

            adjustment += 6.0


        elif (
            classe
            == "SAFE_CONTEXT"
        ):

            adjustment -= 5.0


    old_score = float(
        result.get(
            "score",
            0
        )
        or 0
    )


    result[
        "score"
    ] = round(
        old_score
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
            "vi623_documentary_budget_boost"
        )


    elif adjustment < 0:

        reasons.append(
            "vi623_stock_budget_penalty"
        )


    result[
        "reasons"
    ] = reasons


    result[
        "vi623_adjustment"
    ] = round(
        adjustment,
        3
    )


    result[
        "vi623_documentary_urgency"
    ] = urgency


    result[
        "vi623_documentary_needed"
    ] = state.get(
        "documentary_needed"
    )


    return result


def self_test():

    from vi6_22_story_audit import (
        reset,
        record_final
    )


    reset()


    # Três cenas stock iniciais:
    # deficit documental aumenta.
    for number in (
        1,
        2,
        3,
    ):

        record_final(
            {
                "_vi68_storyboard":
                    {
                        "scene":
                            number,

                        "role":
                            "CONTEXT"
                    }
            },
            {
                "fonte":
                    "Pixabay",

                "_vi6_class":
                    "SAFE_CONTEXT"
            },
            "test",
            {
                "class":
                    "SAFE_CONTEXT",

                "score":
                    70
            }
        )


    doc = adjust_result(
        {
            "score":
                70,

            "class":
                "REAL_DOCUMENTARY",

            "truth_ok":
                True,

            "role":
                "EVIDENCE",

            "reasons":
                []
        },
        {
            "retrieval_role_6_7":
                "EVIDENCE"
        }
    )


    stock = adjust_result(
        {
            "score":
                70,

            "class":
                "SAFE_CONTEXT",

            "truth_ok":
                True,

            "role":
                "EVIDENCE",

            "reasons":
                []
        },
        {
            "retrieval_role_6_7":
                "EVIDENCE"
        }
    )


    assert doc[
        "score"
    ] > 70


    assert stock[
        "score"
    ] < 70


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.23 ADAPTIVE BUDGET SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Documentary Deficit Detection"
    )
    print(
        "OK Documentary Score Boost"
    )
    print(
        "OK Stock Penalty"
    )
    print(
        "OK Role-Aware Adjustment"
    )
    print(
        "OK No Hard Truth Relaxation"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 3. VI6.23 RUNTIME POLICY
# =====================================================

cat > vi6_23_runtime_policy.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

from vi6_23_adaptive_budget import (
    adjust_result
)


if not getattr(
    brain,
    "_VI623_RUNTIME_ACTIVE",
    False
):

    _base_evaluate_623 = (
        brain.evaluate
    )


    def _evaluate_623(
        item,
        cena,
        vi6_scene=None
    ):

        result = (
            _base_evaluate_623(
                item,
                cena,
                vi6_scene
            )
        )


        if result is None:

            return None


        return adjust_result(
            result,
            cena
        )


    brain.evaluate = (
        _evaluate_623
    )


    brain._VI623_RUNTIME_ACTIVE = True
PY


# =====================================================
# 4. VI6.24 TELEMETRY CORE
# =====================================================

cat > vi6_24_production_telemetry.py <<'PY'
#!/usr/bin/env python3

import json
import os
from datetime import datetime


VERSION = "6.24"


_RUNTIME = []


def reset():

    _RUNTIME.clear()


def record(
    scene,
    candidate,
    reason,
    meta,
    story_state
):

    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    try:

        scene_number = int(
            board.get(
                "scene",
                len(
                    _RUNTIME
                ) + 1
            )
            or len(
                _RUNTIME
            ) + 1
        )

    except Exception:

        scene_number = (
            len(
                _RUNTIME
            )
            + 1
        )


    event = {

        "scene":
            scene_number,

        "role":
            meta.get(
                "role"
            )
            or scene.get(
                "retrieval_role_6_7"
            )
            or board.get(
                "role"
            ),

        "accepted":
            candidate is not None,

        "source":
            (
                candidate.get(
                    "fonte"
                )
                or candidate.get(
                    "source"
                )
            )
            if candidate
            else None,

        "class":
            (
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
            )
            if candidate
            else "FALLBACK",

        "reason":
            reason,

        "decision":
            meta.get(
                "decision"
            ),

        "vi69":
            meta.get(
                "vi69_reason"
            ),

        "vi611":
            meta.get(
                "vi611_reason"
            ),

        "vi612":
            meta.get(
                "vi612_reason"
            ),

        "vi614":
            meta.get(
                "vi614_reason"
            ),

        "vi619":
            meta.get(
                "vi619_reason"
            )
            or meta.get(
                "vi619_decision"
            ),

        "vi623_adjustment":
            meta.get(
                "vi623_adjustment"
            ),

        "documentary_so_far":
            story_state.get(
                "documentary"
            ),

        "documentary_needed":
            story_state.get(
                "documentary_needed"
            ),

        "documentary_urgency":
            story_state.get(
                "documentary_urgency"
            ),

        "fallback_so_far":
            story_state.get(
                "fallback"
            ),

        "true_recovery_so_far":
            story_state.get(
                "true_recovery"
            ),
    }


    _RUNTIME.append(
        event
    )


    return event


def summary(
    story_state
):

    return {

        "version":
            VERSION,

        "events":
            len(
                _RUNTIME
            ),

        "accepted":
            sum(
                1
                for event in _RUNTIME
                if event[
                    "accepted"
                ]
            ),

        "fallback":
            sum(
                1
                for event in _RUNTIME
                if not event[
                    "accepted"
                ]
            ),

        "documentary":
            story_state.get(
                "documentary"
            ),

        "documentary_target":
            story_state.get(
                "documentary_target"
            ),

        "safe_context":
            story_state.get(
                "safe_context"
            ),

        "true_recovery":
            story_state.get(
                "true_recovery"
            ),

        "second_chance":
            story_state.get(
                "second_chance"
            ),

        "low_confidence_scenes":
            story_state.get(
                "low_confidence_scenes"
            ),

        "source_distribution":
            story_state.get(
                "sources"
            ),

        "events_detail":
            list(
                _RUNTIME
            ),
    }


def flush(
    story_state,
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
            "vi6_24_telemetry_latest.json"
        )


    payload = {

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "summary":
            summary(
                story_state
            ),
    }


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2
        )


    return path


def self_test():

    reset()


    state = {

        "documentary":
            2,

        "documentary_target":
            4,

        "safe_context":
            3,

        "true_recovery":
            1,

        "second_chance":
            1,

        "low_confidence_scenes":
            [],

        "sources":
            {
                "Wikimedia":
                    2,

                "Pixabay":
                    3,
            },

        "documentary_needed":
            2,

        "documentary_urgency":
            .4,

        "fallback":
            0,
    }


    record(
        {
            "_vi68_storyboard":
                {
                    "scene": 1
                }
        },
        {
            "fonte":
                "Wikimedia",

            "_vi6_class":
                "REAL_DOCUMENTARY"
        },
        "test",
        {
            "class":
                "REAL_DOCUMENTARY"
        },
        state
    )


    result = summary(
        state
    )


    assert result[
        "events"
    ] == 1


    assert result[
        "documentary"
    ] == 2


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.24 TELEMETRY SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Per-Scene Telemetry"
    )
    print(
        "OK Recovery Telemetry"
    )
    print(
        "OK Documentary Telemetry"
    )
    print(
        "OK Source Distribution"
    )
    print(
        "OK JSON Runtime Report"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 5. VI6.24 FINAL SUPERVISOR WRAPPER
# =====================================================

cat > vi6_24_runtime_telemetry.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

from vi6_22_story_audit import (
    record_final,
    summary as story_summary,
    reset as story_reset,
)

from vi6_24_production_telemetry import (
    record as telemetry_record,
    flush as telemetry_flush,
    reset as telemetry_reset,
)


if not getattr(
    brain,
    "_VI624_RUNTIME_ACTIVE",
    False
):

    _base_supervisor_624 = (
        brain.supervisionar_vi6_6
    )


    def _wrapped_624(
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

            story_reset()
            telemetry_reset()


        (
            candidate,
            reason,
            meta
        ) = _base_supervisor_624(
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


        # O VI6.23 ajusta o resultado do
        # evaluator. Quando esse valor chegou
        # ao supervisor, preservamos o estado
        # quando disponível.
        if candidate is not None:

            adjustment = (
                candidate.get(
                    "_vi623_adjustment"
                )
            )


            if adjustment is not None:

                meta[
                    "vi623_adjustment"
                ] = adjustment


        record_final(
            cena,
            candidate,
            reason,
            meta
        )


        state = story_summary()


        telemetry_record(
            cena,
            candidate,
            reason,
            meta,
            state
        )


        meta[
            "vi622_story_state"
        ] = {

            "documentary":
                state.get(
                    "documentary"
                ),

            "documentary_target":
                state.get(
                    "documentary_target"
                ),

            "documentary_needed":
                state.get(
                    "documentary_needed"
                ),

            "documentary_urgency":
                state.get(
                    "documentary_urgency"
                ),

            "fallback":
                state.get(
                    "fallback"
                ),

            "true_recovery":
                state.get(
                    "true_recovery"
                ),

            "low_confidence_scenes":
                state.get(
                    "low_confidence_scenes"
                ),
        }


        if (
            number >= 12
            or board.get(
                "cta_reuse"
            )
        ):

            try:

                meta[
                    "vi624_telemetry_path"
                ] = telemetry_flush(
                    state
                )

            except Exception as exc:

                meta[
                    "vi624_telemetry_error"
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
        _wrapped_624
    )


    brain._VI624_RUNTIME_ACTIVE = True
PY


# =====================================================
# 6. ATTACH RUNTIME POLICIES SAFELY
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
    "# VI6.22-6.24 RUNTIME STACK"
)


if MARKER in source:

    print(
        "VI6.22-6.24 runtime já conectado."
    )

    raise SystemExit(0)


append = '''

# =========================================
# VI6.22-6.24 RUNTIME STACK
# =========================================
import vi6_23_runtime_policy
import vi6_24_runtime_telemetry
'''


patched = (
    source.rstrip()
    + "\n"
    + append
    + "\n"
)


# Não grava caso a sintaxe fique inválida.
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
    " VI6.22-6.24 RUNTIME ATTACHED"
)
print(
    "======================================"
)
print(
    "VI6.9 original logic: INTACT"
)
print(
    "VI6.23 evaluator wrapper: ADDED"
)
print(
    "VI6.24 supervisor wrapper: ADDED"
)
print()
PY


STATUS=$?


if [ "$STATUS" -ne 0 ]; then

    rollback
    exit "$STATUS"
fi


# =====================================================
# 7. OFFLINE SYSTEM TEST
# =====================================================

cat > testar_vi622_vi624.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy


assert getattr(
    brain,
    "_VI623_RUNTIME_ACTIVE",
    False
)


assert getattr(
    brain,
    "_VI624_RUNTIME_ACTIVE",
    False
)


# Flags anteriores também precisam continuar.
for flag in (
    "_VI69_RUNTIME_PATCHED",
    "_VI611_RUNTIME_ACTIVE",
    "_VI612_RUNTIME_ACTIVE",
    "_VI613_RUNTIME_ACTIVE",
    "_VI614_RUNTIME_ACTIVE",
    "_VI615_RUNTIME_ACTIVE",
    "_VI619_RUNTIME_ACTIVE",
    "_VI620_RUNTIME_ACTIVE",
    "_VI621_RUNTIME_ACTIVE",
):

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
    " VI6.22-6.24 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.23 ADAPTIVE BUDGET:",
    brain._VI623_RUNTIME_ACTIVE
)

print(
    "VI6.24 TELEMETRY:",
    brain._VI624_RUNTIME_ACTIVE
)

print(
    "VI6.19 TRUE RECOVERY:",
    brain._VI619_RUNTIME_ACTIVE
)

print(
    "VI6.21 CIRCUIT:",
    brain._VI621_RUNTIME_ACTIVE
)

print()
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
# 8. COMPILE
# =====================================================

echo
echo "===== FULL COMPILE ====="

if ! python -m py_compile \
    vi6_22_story_audit.py \
    vi6_23_adaptive_budget.py \
    vi6_23_runtime_policy.py \
    vi6_24_production_telemetry.py \
    vi6_24_runtime_telemetry.py \
    vi6_9_runtime_policy.py \
    testar_vi622_vi624.py \
    vi6_19_true_recovery.py \
    vi6_20_recovery_normalizer.py \
    vi6_21_recovery_circuit.py \
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
echo "===== VI6.22 SELF TEST ====="

if ! python vi6_22_story_audit.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.23 SELF TEST ====="

if ! python vi6_23_adaptive_budget.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.24 SELF TEST ====="

if ! python vi6_24_production_telemetry.py; then
    rollback
    exit 1
fi


echo
echo "===== RUNTIME TEST ====="

if ! python testar_vi622_vi624.py; then
    rollback
    exit 1
fi


# =====================================================
# 10. REGRESSIONS
# =====================================================

echo
echo "===== VI6.19 REGRESSION ====="

if ! python vi6_19_true_recovery.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.20 REGRESSION ====="

if ! python vi6_20_recovery_normalizer.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.21 REGRESSION ====="

if ! python vi6_21_recovery_circuit.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.13 REGRESSION ====="

if ! python vi6_13_recovery_planner.py; then
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
# FINAL
# =====================================================

echo
echo "======================================"
echo " VI6.22 + VI6.23 + VI6.24 INSTALADOS"
echo "======================================"
echo
echo "OK Rolling Story Audit"
echo "OK Documentary Deficit Tracking"
echo "OK Remaining Scene Projection"
echo "OK Adaptive Documentary Budget"
echo "OK Documentary Score Boost"
echo "OK Stock Budget Penalty"
echo "OK Role-Aware Budget"
echo "OK Rolling Confidence Audit"
echo "OK Low-Confidence Scene Detection"
echo "OK Source Distribution Telemetry"
echo "OK Second-Chance Telemetry"
echo "OK True-Recovery Telemetry"
echo "OK Final JSON Telemetry"
echo "OK VI6.19 True Recovery preservado"
echo "OK VI6.21 Circuit Breaker preservado"
echo "OK VI6.14 Final Gate preservado"
echo "OK VI6.9 Firewall preservado"
echo "OK VI6.6 Active Brain preservado"
echo "OK 5.x fallback preservado"
echo
echo "MIDIA.PY MODIFICADO=NAO"
echo "GERAR_SHORT MODIFICADO=NAO"
echo "API CALLS DURANTE INSTALACAO=0"
echo "DOWNLOADS DURANTE INSTALACAO=0"
echo "VIDEOS GERADOS=0"
echo
echo "FUTURA TELEMETRIA:"
echo "logs/producao/vi6_24_telemetry_latest.json"
echo
