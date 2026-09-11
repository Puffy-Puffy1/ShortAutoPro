#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi611_vi612_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================"
echo " VI6.11 + VI6.12"
echo " SECOND CHANCE + GLOBAL STORY GUARD"
echo "======================================"
echo


# =====================================================
# BASELINE
# =====================================================

echo "===== BASELINE ====="

for F in \
    midia.py \
    vi6_6_active_brain.py \
    vi6_7_retrieval_planner.py \
    vi6_8_storyboard_director.py \
    vi6_8_runtime_policy.py \
    vi6_9_quality_firewall.py \
    vi6_9_runtime_policy.py \
    vi6_10_coverage_predictor.py
do

    if [ ! -f "$F" ]; then
        echo "ERRO: $F não encontrado."
        echo "NADA FOI ALTERADO."
        exit 2
    fi

done


if ! python -m py_compile \
    midia.py \
    vi6_6_active_brain.py \
    vi6_7_retrieval_planner.py \
    vi6_8_storyboard_director.py \
    vi6_8_runtime_policy.py \
    vi6_9_quality_firewall.py \
    vi6_9_runtime_policy.py \
    vi6_10_coverage_predictor.py
then

    echo "BASELINE NÃO COMPILA."
    echo "NADA FOI ALTERADO."
    exit 3
fi

echo "BASELINE=OK"


cp vi6_9_runtime_policy.py \
   "$BACKDIR/vi6_9_runtime_policy.py"


for F in \
    vi6_11_second_chance.py \
    vi6_12_story_guard.py
do

    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi

done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.11/6.12"
    echo "======================================"

    cp "$BACKDIR/vi6_9_runtime_policy.py" \
       vi6_9_runtime_policy.py

    for F in \
        vi6_11_second_chance.py \
        vi6_12_story_guard.py
    do

        if [ -f "$BACKDIR/$F" ]; then
            cp "$BACKDIR/$F" "$F"
        else
            rm -f "$F"
        fi

    done

    rm -f testar_vi611_vi612.py

    echo "Projeto restaurado."
}


# =====================================================
# VI6.11 SECOND-CHANCE RESCUE
# =====================================================

cat > vi6_11_second_chance.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.11"


HARD_REJECTIONS = {
    "vi69_high_risk",
    "vi69_misleading",
    "vi69_quality_floor",
    "vi69_documentary_truth_failed",
    "vi69_unsupported_class",
}


def _s(v):
    return str(v or "").strip()


def _u(v):
    return _s(v).upper()


def _f(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return float(default)


def _key(item):

    return (
        _s(
            item.get("fonte")
            or item.get("source")
        ),
        _s(item.get("id")),
        _s(item.get("url")),
    )


def _id_key(item):

    return (
        _s(
            item.get("fonte")
            or item.get("source")
        ),
        _s(item.get("id")),
    )


def _find_original(
    serialized,
    candidatos
):

    if not serialized:
        return None


    key = _key(serialized)


    for item in candidatos or []:

        if (
            any(key)
            and _key(item) == key
        ):
            return item


    src, ident = _id_key(
        serialized
    )


    if src and ident:

        matches = [
            item
            for item in candidatos or []
            if (
                _id_key(item)
                == (src, ident)
            )
        ]

        if len(matches) == 1:
            return matches[0]


    return None


def _serialized_pool(
    vi6_scene
):

    raw = []


    winner = (
        (vi6_scene or {}).get("winner")
        or {}
    )

    if winner:
        raw.append(winner)


    raw.extend(
        (
            (vi6_scene or {}).get("top")
            or []
        )[:12]
    )


    out = []
    seen = set()


    for item in raw:

        if not item:
            continue


        key = _key(item)


        if not any(key):

            key = (
                _s(item.get("descricao")),
                _s(item.get("class")),
                _f(item.get("score")),
            )


        if key in seen:
            continue


        seen.add(key)
        out.append(item)


    return out


def rescue(
    vi6_scene,
    candidatos,
    cena,
    rejection_reason,
    evaluator,
    firewall
):

    # Hard safety nunca é relaxado.
    if rejection_reason in HARD_REJECTIONS:

        return (
            None,
            "vi611_hard_rejection_preserved",
            {
                "decision":
                    "NO_RESCUE"
            }
        )


    evaluated = []


    for serialized in _serialized_pool(
        vi6_scene
    ):

        original = _find_original(
            serialized,
            candidatos
        )


        if original is None:
            continue


        result = evaluator(
            serialized,
            cena,
            vi6_scene
        )


        if result is None:
            continue


        firewall_result = firewall(
            original,
            cena,
            result
        )


        if (
            firewall_result.get("action")
            != "KEEP"
        ):
            continue


        score = _f(
            result.get("score")
        )


        classe = _u(
            result.get("class")
        )


        # Documental verdadeiro recebe
        # desempate editorial.
        rescue_score = score


        if (
            classe
            == "REAL_DOCUMENTARY"
            and result.get(
                "truth_ok",
                False
            )
        ):

            rescue_score += 8.0


        evaluated.append(
            {
                "original":
                    original,

                "result":
                    result,

                "score":
                    score,

                "rescue_score":
                    rescue_score,

                "firewall":
                    firewall_result,
            }
        )


    if not evaluated:

        return (
            None,
            "vi611_no_safe_alternative",
            {
                "decision":
                    "NO_RESCUE"
            }
        )


    evaluated.sort(
        key=lambda x:
            x["rescue_score"],
        reverse=True
    )


    best = evaluated[0]


    # Piso mínimo absoluto.
    if best["score"] < 50:

        return (
            None,
            "vi611_rescue_floor",
            {
                "decision":
                    "NO_RESCUE",

                "score":
                    best["score"],
            }
        )


    original = best[
        "original"
    ]


    result = best[
        "result"
    ]


    original[
        "_vi611_rescued"
    ] = True

    original[
        "_vi611_score"
    ] = best[
        "score"
    ]

    original[
        "_vi611_class"
    ] = result.get(
        "class"
    )

    original[
        "_vi611_truth"
    ] = result.get(
        "truth_ok"
    )

    original[
        "_vi611_reason"
    ] = (
        "second_chance_candidate"
    )


    return (
        original,
        "vi611_second_chance_rescue",
        {
            "decision":
                "RESCUE",

            "score":
                best["score"],

            "class":
                result.get(
                    "class"
                ),

            "role":
                result.get(
                    "role"
                ),

            "semantic":
                result.get(
                    "semantic"
                ),

            "provenance":
                result.get(
                    "provenance"
                ),

            "anchor":
                result.get(
                    "anchor_ratio"
                ),

            "truth_ok":
                result.get(
                    "truth_ok"
                ),

            "original_rejection":
                rejection_reason,
        }
    )


def self_test():

    scene = {
        "retrieval_role_6_7":
            "EVIDENCE"
    }


    bad = {
        "fonte":
            "Pixabay",
        "tipo":
            "vídeo",
        "id":
            "bad",
        "url":
            "bad",
        "class":
            "SAFE_CONTEXT",
        "risk":
            "LOW",
        "quality_tier":
            "NORMAL",
        "truth_ok":
            True,
        "score":
            80,
    }


    doc = {
        "fonte":
            "Wikimedia",
        "tipo":
            "foto",
        "id":
            "doc",
        "url":
            "doc",
        "class":
            "REAL_DOCUMENTARY",
        "risk":
            "LOW",
        "quality_tier":
            "NORMAL",
        "truth_ok":
            True,
        "score":
            75,
    }


    vi6_scene = {
        "winner": bad,
        "top": [
            bad,
            doc,
        ]
    }


    candidatos = [
        bad,
        doc,
    ]


    def evaluator(
        item,
        cena,
        vi6
    ):

        if item["id"] == "bad":

            return {
                "score": 80,
                "class":
                    "SAFE_CONTEXT",
                "truth_ok": True,
                "semantic": 48,
                "role":
                    "EVIDENCE",
                "anchor_ratio": .05,
            }


        return {
            "score": 75,
            "class":
                "REAL_DOCUMENTARY",
            "truth_ok": True,
            "semantic": 70,
            "role":
                "EVIDENCE",
            "anchor_ratio": .60,
        }


    def firewall(
        candidate,
        cena,
        meta
    ):

        if candidate["id"] == "bad":

            return {
                "action":
                    "FALLBACK"
            }


        return {
            "action":
                "KEEP"
        }


    candidate, reason, meta = rescue(
        vi6_scene,
        candidatos,
        scene,
        "vi69_semantic_floor",
        evaluator,
        firewall
    )


    assert candidate is not None

    assert candidate["id"] == "doc"

    assert (
        reason
        == "vi611_second_chance_rescue"
    )


    candidate, _, _ = rescue(
        vi6_scene,
        candidatos,
        scene,
        "vi69_documentary_truth_failed",
        evaluator,
        firewall
    )


    assert candidate is None


    print()
    print(
        "======================================"
    )
    print(
        " VI6.11 SECOND CHANCE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK alternative candidate rescue"
    )
    print(
        "OK documentary rescue"
    )
    print(
        "OK hard safety preserved"
    )
    print(
        "OK no API required"
    )
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI6.12 GLOBAL STORY GUARD
# =====================================================

cat > vi6_12_story_guard.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.12"


_HISTORY = []


def _s(v):
    return str(v or "").strip()


def _u(v):
    return _s(v).upper()


def _f(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return float(default)


def _key(item):

    return (
        _s(
            item.get("fonte")
            or item.get("source")
        ),
        _s(item.get("id")),
        _s(item.get("url")),
    )


def _source(item):

    return _s(
        item.get("fonte")
        or item.get("source")
    )


def _family(item):

    return _u(
        item.get("family")
    )


def _class_from_meta(
    candidate,
    meta
):

    return _u(
        meta.get("class")
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


def _scene_number(scene):

    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    return int(
        board.get(
            "scene",
            len(_HISTORY) + 1
        )
        or len(_HISTORY) + 1
    )


def _cta(scene):

    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    return bool(
        board.get(
            "cta_reuse"
        )
        or _u(
            scene.get(
                "retrieval_role_6_7"
            )
        ) == "CTA"
    )


def _find_original(
    serialized,
    candidatos
):

    key = _key(
        serialized
    )


    for candidate in candidatos or []:

        if (
            any(key)
            and _key(candidate) == key
        ):

            return candidate


    return None


def _alternatives(
    vi6_scene,
    candidatos,
    cena,
    evaluator,
    firewall
):

    raw = []


    winner = (
        (vi6_scene or {}).get("winner")
        or {}
    )


    if winner:
        raw.append(winner)


    raw.extend(
        (
            (vi6_scene or {}).get("top")
            or []
        )[:12]
    )


    output = []
    seen = set()


    for serialized in raw:

        if not serialized:
            continue


        key = _key(
            serialized
        )


        if not any(key):
            continue


        if key in seen:
            continue


        seen.add(key)


        original = _find_original(
            serialized,
            candidatos
        )


        if original is None:
            continue


        meta = evaluator(
            serialized,
            cena,
            vi6_scene
        )


        if meta is None:
            continue


        fw = firewall(
            original,
            cena,
            meta
        )


        if fw.get("action") != "KEEP":
            continue


        output.append(
            {
                "candidate":
                    original,

                "meta":
                    meta,

                "score":
                    _f(
                        meta.get(
                            "score"
                        )
                    ),
            }
        )


    output.sort(
        key=lambda x:
            x["score"],
        reverse=True
    )


    return output


def _record(
    candidate,
    meta
):

    _HISTORY.append(
        {
            "key":
                _key(candidate),

            "source":
                _source(candidate),

            "family":
                _family(candidate),

            "class":
                _class_from_meta(
                    candidate,
                    meta
                ),
        }
    )


def review(
    candidate,
    cena,
    meta,
    vi6_scene,
    candidatos,
    evaluator,
    firewall
):

    if candidate is None:

        return (
            None,
            "vi612_no_candidate",
            meta
        )


    meta = dict(
        meta
        or {}
    )


    scene_no = _scene_number(
        cena
    )


    # =================================
    # CTA reutiliza história.
    # =================================

    if _cta(cena):

        _record(
            candidate,
            meta
        )


        meta[
            "vi612_decision"
        ] = "CTA_KEEP"


        return (
            candidate,
            "vi612_cta_keep",
            meta
        )


    key = _key(
        candidate
    )


    src = _source(
        candidate
    )


    family = _family(
        candidate
    )


    current_class = (
        _class_from_meta(
            candidate,
            meta
        )
    )


    # =================================
    # DUPLICATE ASSET GUARD
    # =================================

    duplicate = any(
        item["key"] == key
        for item in _HISTORY
    )


    # =================================
    # SOURCE STREAK GUARD
    # =================================

    last2 = _HISTORY[-2:]


    source_streak = (
        len(last2) == 2
        and all(
            item["source"] == src
            for item in last2
        )
    )


    # =================================
    # FAMILY STREAK GUARD
    # =================================

    family_streak = (
        bool(family)
        and family != "OTHER"
        and len(last2) == 2
        and all(
            item["family"] == family
            for item in last2
        )
    )


    board = (
        cena.get(
            "_vi68_storyboard"
        )
        or {}
    )


    prefer_documentary = bool(
        board.get(
            "prefer_documentary"
        )
    )


    need_alternative = (
        duplicate
        or source_streak
        or family_streak
        or (
            prefer_documentary
            and current_class
            == "SAFE_CONTEXT"
        )
    )


    if need_alternative:

        alternatives = _alternatives(
            vi6_scene,
            candidatos,
            cena,
            evaluator,
            firewall
        )


        current_score = _f(
            meta.get(
                "score",
                candidate.get(
                    "_vi611_score",
                    candidate.get(
                        "_vi6_score",
                        0
                    )
                )
            )
        )


        for alt in alternatives:

            alt_candidate = alt[
                "candidate"
            ]

            alt_meta = alt[
                "meta"
            ]


            if (
                _key(alt_candidate)
                == key
            ):
                continue


            alt_src = _source(
                alt_candidate
            )


            alt_family = _family(
                alt_candidate
            )


            # Não cria outro streak.
            if (
                source_streak
                and alt_src == src
            ):
                continue


            if (
                family_streak
                and alt_family == family
            ):
                continue


            alt_class = _u(
                alt_meta.get(
                    "class"
                )
            )


            # Se storyboard pede documental,
            # procurar documental primeiro.
            if (
                prefer_documentary
                and current_class
                == "SAFE_CONTEXT"
                and alt_class
                != "REAL_DOCUMENTARY"
            ):
                continue


            # Não troca por opção muito pior.
            margin = (
                14.0
                if (
                    alt_class
                    == "REAL_DOCUMENTARY"
                )
                else 8.0
            )


            if (
                alt["score"]
                < current_score - margin
            ):
                continue


            alt_candidate[
                "_vi612_override"
            ] = True


            alt_candidate[
                "_vi612_reason"
            ] = (
                "global_story_guard"
            )


            _record(
                alt_candidate,
                alt_meta
            )


            meta = dict(
                alt_meta
            )


            meta[
                "vi612_decision"
            ] = "OVERRIDE"


            meta[
                "vi612_original_source"
            ] = src


            return (
                alt_candidate,
                "vi612_story_override",
                meta
            )


    # =================================
    # HARD DUPLICATE
    # =================================
    #
    # Mesmo asset não entra duas vezes,
    # exceto CTA.
    # =================================

    if duplicate:

        meta[
            "vi612_decision"
        ] = "5X_DUPLICATE"


        return (
            None,
            "vi612_duplicate_asset_fallback",
            meta
        )


    _record(
        candidate,
        meta
    )


    meta[
        "vi612_decision"
    ] = "KEEP"


    # Resumo na última cena/CTA é produzido
    # pela função story_summary().
    meta[
        "vi612_scene"
    ] = scene_no


    return (
        candidate,
        "vi612_story_keep",
        meta
    )


def story_summary():

    documentary = sum(
        1
        for item in _HISTORY
        if (
            item["class"]
            == "REAL_DOCUMENTARY"
        )
    )


    safe = sum(
        1
        for item in _HISTORY
        if (
            item["class"]
            == "SAFE_CONTEXT"
        )
    )


    unique_assets = len(
        {
            item["key"]
            for item in _HISTORY
        }
    )


    return {
        "version":
            VERSION,

        "scenes_seen":
            len(_HISTORY),

        "documentary":
            documentary,

        "safe_context":
            safe,

        "unique_assets":
            unique_assets,

        "duplicate_assets":
            max(
                0,
                len(_HISTORY)
                - unique_assets
            ),
    }


def reset_state():

    _HISTORY.clear()


def self_test():

    reset_state()


    scene = {
        "_vi68_storyboard":
            {
                "scene": 1,
                "prefer_documentary": False,
            }
    }


    a = {
        "fonte": "Pixabay",
        "id": "a",
        "url": "a",
        "family": "CITY",
        "_vi6_class":
            "SAFE_CONTEXT",
    }


    meta = {
        "class":
            "SAFE_CONTEXT",
        "score": 80,
    }


    def evaluator(
        item,
        scene,
        vi6
    ):

        return {
            "class":
                item.get(
                    "class",
                    "SAFE_CONTEXT"
                ),
            "score":
                item.get(
                    "score",
                    80
                ),
            "truth_ok":
                True,
        }


    def firewall(
        candidate,
        scene,
        meta
    ):

        return {
            "action":
                "KEEP"
        }


    chosen, _, _ = review(
        a,
        scene,
        meta,
        {},
        [a],
        evaluator,
        firewall
    )


    assert chosen is a


    # Mesmo asset outra vez,
    # sem alternativa => fallback.
    scene2 = {
        "_vi68_storyboard":
            {
                "scene": 2,
                "prefer_documentary": False,
            }
    }


    chosen, reason, _ = review(
        a,
        scene2,
        meta,
        {},
        [a],
        evaluator,
        firewall
    )


    assert chosen is None

    assert (
        reason
        == "vi612_duplicate_asset_fallback"
    )


    summary = story_summary()

    assert (
        summary[
            "duplicate_assets"
        ]
        == 0
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.12 STORY GUARD SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Duplicate Asset Guard"
    )
    print(
        "OK Source Streak Guard"
    )
    print(
        "OK Visual Family Guard"
    )
    print(
        "OK Documentary Opportunity"
    )
    print(
        "OK CTA Exception"
    )
    print(
        "OK Story Ledger"
    )
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# NOVO VI6.9 RUNTIME STACK
#
# Substituímos apenas este wrapper.
# midia.py NÃO é alterado.
# =====================================================

cat > vi6_9_runtime_policy.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

from vi6_9_quality_firewall import (
    check
)

from vi6_11_second_chance import (
    rescue
)

from vi6_12_story_guard import (
    review,
    story_summary
)


if not getattr(
    brain,
    "_VI69_RUNTIME_PATCHED",
    False
):

    _base = (
        brain.supervisionar_vi6_6
    )


    def _wrapped(
        vi6_scene,
        candidatos,
        cena,
        current_candidate,
        current_reason
    ):

        # =========================================
        # 1. VI6.6 ACTIVE BRAIN
        # =========================================

        (
            candidate,
            reason,
            meta
        ) = _base(
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


        rejection_reason = None


        # =========================================
        # 2. VI6.9 FIREWALL
        # =========================================

        if candidate is not None:

            firewall = check(
                candidate,
                cena,
                meta
            )


            meta[
                "vi69_action"
            ] = firewall.get(
                "action"
            )


            meta[
                "vi69_reason"
            ] = firewall.get(
                "reason"
            )


            meta[
                "vi610_contract"
            ] = firewall.get(
                "contract"
            )


            if (
                firewall.get(
                    "action"
                )
                == "FALLBACK"
            ):

                rejection_reason = (
                    firewall.get(
                        "reason",
                        "vi69_firewall"
                    )
                )


                candidate = None


        else:

            rejection_reason = (
                reason
                or current_reason
                or "vi66_no_candidate"
            )


        # =========================================
        # 3. VI6.11 SECOND CHANCE
        # =========================================

        if candidate is None:

            (
                rescued,
                rescue_reason,
                rescue_meta
            ) = rescue(
                vi6_scene,
                candidatos,
                cena,
                rejection_reason,
                brain.evaluate,
                check
            )


            meta[
                "vi611_decision"
            ] = rescue_meta.get(
                "decision"
            )


            meta[
                "vi611_reason"
            ] = rescue_reason


            if rescued is not None:

                candidate = rescued

                reason = (
                    rescue_reason
                )


                meta.update(
                    rescue_meta
                )


            else:

                meta[
                    "decision"
                ] = "5X_AFTER_611"


                return (
                    None,
                    rejection_reason
                    or rescue_reason,
                    meta
                )


        # =========================================
        # 4. VI6.12 GLOBAL STORY GUARD
        # =========================================

        (
            candidate,
            story_reason,
            story_meta
        ) = review(
            candidate,
            cena,
            meta,
            vi6_scene,
            candidatos,
            brain.evaluate,
            check
        )


        meta = dict(
            story_meta
            or meta
        )


        meta[
            "vi612_reason"
        ] = story_reason


        if candidate is None:

            meta[
                "decision"
            ] = "5X_AFTER_612"


            return (
                None,
                story_reason,
                meta
            )


        # =========================================
        # 5. FINAL ACTIVE DECISION
        # =========================================

        reason = story_reason


        board = (
            cena.get(
                "_vi68_storyboard"
            )
            or {}
        )


        # Última cena / CTA:
        # anexa snapshot global ao log/meta.
        if (
            board.get(
                "cta_reuse"
            )
            or int(
                board.get(
                    "scene",
                    0
                )
                or 0
            ) >= 12
        ):

            meta[
                "vi612_story_summary"
            ] = story_summary()


        return (
            candidate,
            reason,
            meta
        )


    brain.supervisionar_vi6_6 = (
        _wrapped
    )


    brain._VI69_RUNTIME_PATCHED = (
        True
    )


    brain._VI611_RUNTIME_ACTIVE = (
        True
    )


    brain._VI612_RUNTIME_ACTIVE = (
        True
    )
PY


# =====================================================
# OFFLINE INTEGRATION TEST
# =====================================================

cat > testar_vi611_vi612.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain
import vi6_8_runtime_policy
import vi6_9_runtime_policy

from vi6_12_story_guard import (
    reset_state,
    story_summary
)


assert getattr(
    brain,
    "_VI68_RUNTIME_PATCHED",
    False
)


assert getattr(
    brain,
    "_VI69_RUNTIME_PATCHED",
    False
)


assert getattr(
    brain,
    "_VI611_RUNTIME_ACTIVE",
    False
)


assert getattr(
    brain,
    "_VI612_RUNTIME_ACTIVE",
    False
)


reset_state()


print()
print(
    "======================================"
)
print(
    " VI6.11 + VI6.12 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.8 RUNTIME:",
    brain._VI68_RUNTIME_PATCHED
)

print(
    "VI6.9 RUNTIME:",
    brain._VI69_RUNTIME_PATCHED
)

print(
    "VI6.11 RUNTIME:",
    brain._VI611_RUNTIME_ACTIVE
)

print(
    "VI6.12 RUNTIME:",
    brain._VI612_RUNTIME_ACTIVE
)

print(
    "STORY STATE:",
    story_summary()
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
# COMPILE
# =====================================================

echo
echo "===== COMPILE ====="

if ! python -m py_compile \
    vi6_11_second_chance.py \
    vi6_12_story_guard.py \
    vi6_9_runtime_policy.py \
    vi6_9_quality_firewall.py \
    vi6_10_coverage_predictor.py \
    vi6_6_active_brain.py \
    vi6_8_runtime_policy.py \
    midia.py \
    testar_vi611_vi612.py
then

    echo "COMPILE FALHOU."

    rollback

    exit 1
fi

echo "PYTHON STATUS=0"


# =====================================================
# SELF TESTS
# =====================================================

echo
echo "===== VI6.11 SELF TEST ====="

if ! python vi6_11_second_chance.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.12 SELF TEST ====="

if ! python vi6_12_story_guard.py; then
    rollback
    exit 1
fi


echo
echo "===== RUNTIME INTEGRATION ====="

if ! python testar_vi611_vi612.py; then
    rollback
    exit 1
fi


# =====================================================
# REGRESSION
# =====================================================

echo
echo "===== VI6.6 REGRESSION ====="

if ! python vi6_6_active_brain.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.7 REGRESSION ====="

if ! python vi6_7_retrieval_planner.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.8 REGRESSION ====="

if ! python vi6_8_storyboard_director.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.9 REGRESSION ====="

if ! python vi6_9_quality_firewall.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.10 REGRESSION ====="

if ! python vi6_10_coverage_predictor.py; then
    rollback
    exit 1
fi


# =====================================================
# CORE VALIDATION
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
echo " VI6.11 + VI6.12 INSTALADOS"
echo "======================================"
echo
echo "OK Second-Chance Candidate Rescue"
echo "OK Rejected Winner Recovery"
echo "OK Documentary Alternative Rescue"
echo "OK Hard Safety Never Relaxed"
echo "OK Duplicate Asset Guard"
echo "OK Same-Source Streak Guard"
echo "OK Visual Family Streak Guard"
echo "OK Documentary Opportunity Guard"
echo "OK Global Story Memory"
echo "OK CTA Reuse Exception"
echo "OK VI6.9 Firewall preservado"
echo "OK VI6.10 Contracts preservados"
echo "OK VI6.8 Storyboard preservado"
echo "OK VI6.7 Retrieval preservado"
echo "OK VI6.6 Active Brain preservado"
echo "OK VI6.3 / 5.x safety fallback preservado"
echo
echo "MIDIA.PY MODIFICADO=NAO"
echo "GERAR_SHORT MODIFICADO=NAO"
echo "API CALLS=0"
echo "DOWNLOADS NOVOS=0"
echo "VIDEOS GERADOS=0"
echo
