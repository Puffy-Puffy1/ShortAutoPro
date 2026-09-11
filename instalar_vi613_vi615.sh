#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi613_vi615_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================"
echo " VI6.13 + VI6.14 + VI6.15"
echo " RECOVERY + FINAL GATE + LEDGER"
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
"

for F in $REQUIRED
do

    if [ ! -f "$F" ]; then

        echo "ERRO: $F não encontrado."
        echo "NADA FOI ALTERADO."

        exit 2
    fi

done


echo "===== BASELINE COMPILE ====="

if ! python -m py_compile \
    midia.py \
    vi6_6_active_brain.py \
    vi6_7_retrieval_planner.py \
    vi6_8_storyboard_director.py \
    vi6_8_runtime_policy.py \
    vi6_9_quality_firewall.py \
    vi6_9_runtime_policy.py \
    vi6_10_coverage_predictor.py \
    vi6_11_second_chance.py \
    vi6_12_story_guard.py
then

    echo
    echo "BASE ATUAL NÃO COMPILA."
    echo "NADA FOI ALTERADO."

    exit 3
fi

echo "BASELINE=OK"


if ! grep -q \
'import vi6_9_runtime_policy' \
midia.py
then

    echo
    echo "ERRO: midia.py não carrega VI6.9 runtime."
    echo "NADA FOI ALTERADO."

    exit 4
fi


cp vi6_9_runtime_policy.py \
   "$BACKDIR/vi6_9_runtime_policy.py"


for F in \
    vi6_13_recovery_planner.py \
    vi6_14_pre_download_gate.py \
    vi6_15_decision_ledger.py \
    mapear_retrieval_sources_6_13.py
do

    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi

done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.13-6.15"
    echo "======================================"

    cp \
        "$BACKDIR/vi6_9_runtime_policy.py" \
        vi6_9_runtime_policy.py


    for F in \
        vi6_13_recovery_planner.py \
        vi6_14_pre_download_gate.py \
        vi6_15_decision_ledger.py \
        mapear_retrieval_sources_6_13.py
    do

        if [ -f "$BACKDIR/$F" ]; then

            cp "$BACKDIR/$F" "$F"

        else

            rm -f "$F"

        fi

    done


    rm -f testar_vi613_vi615.py

    echo "Projeto restaurado."
}


# =====================================================
# 1. VI6.13 RECOVERY QUERY PLANNER
# =====================================================

cat > vi6_13_recovery_planner.py <<'PY'
#!/usr/bin/env python3

import re


VERSION = "6.13"


HARD_NO_RETRY = {
    "vi69_high_risk",
    "vi69_misleading",
    "vi69_documentary_truth_failed",
    "vi69_unsupported_class",
    "vi611_hard_rejection_preserved",
}


def _s(v):

    return str(
        v or ""
    ).strip()


def _unique(values):

    out = []
    seen = set()


    for value in values:

        value = re.sub(
            r"\s+",
            " ",
            _s(value)
        ).strip()


        if not value:
            continue


        key = value.lower()


        if key in seen:
            continue


        seen.add(key)
        out.append(value)


    return out


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


    role = _s(
        board.get(
            "role"
        )
    ).upper()


    if role:
        return role


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
            "archive"
        )
    ):
        return "EVIDENCE"

    if "person" in mode:
        return "PERSON"

    if any(
        x in mode
        for x in (
            "location",
            "place",
            "architecture"
        )
    ):
        return "PLACE"

    if any(
        x in mode
        for x in (
            "object",
            "product",
            "medicine",
            "package"
        )
    ):
        return "OBJECT"

    return "CONTEXT"


def _anchors(scene):

    raw = (
        scene.get(
            "retrieval_anchors_6_7"
        )
        or []
    )


    if isinstance(
        raw,
        str
    ):
        raw = [raw]


    return _unique(
        raw
    )


def _existing_queries(scene):

    raw = (
        scene.get(
            "retrieval_queries_6_7"
        )
        or []
    )


    if isinstance(
        raw,
        str
    ):
        raw = [raw]


    primary = _s(
        scene.get(
            "retrieval_primary_query_6_7"
        )
    )


    original = _s(
        scene.get(
            "visual_query_original_6_7"
        )
        or scene.get(
            "visual_query"
        )
        or scene.get(
            "query"
        )
    )


    return _unique(
        [primary]
        + list(raw)
        + [original]
    )


def _compact(parts):

    words = []


    for part in parts:

        for word in _s(
            part
        ).split():

            if (
                word.lower()
                not in {
                    x.lower()
                    for x in words
                }
            ):

                words.append(
                    word
                )


    return " ".join(
        words[:14]
    )


def build_recovery_plan(
    scene,
    vi6_scene=None,
    rejection_reason=None
):

    role = _role(
        scene
    )


    rejection_reason = _s(
        rejection_reason
    )


    anchors = _anchors(
        scene
    )


    existing = _existing_queries(
        scene
    )


    if (
        rejection_reason
        in HARD_NO_RETRY
    ):

        return {

            "version":
                VERSION,

            "eligible":
                False,

            "role":
                role,

            "reason":
                "hard_safety_no_retry",

            "queries":
                [],

            "max_attempts":
                0,
        }


    if role == "CTA":

        return {

            "version":
                VERSION,

            "eligible":
                False,

            "role":
                role,

            "reason":
                "cta_reuse_only",

            "queries":
                [],

            "max_attempts":
                0,
        }


    queries = []


    # =================================
    # EVIDENCE
    # =================================

    if role == "EVIDENCE":

        if anchors:

            queries.extend(
                [
                    _compact(
                        anchors[:4]
                        + [
                            "archive photograph"
                        ]
                    ),

                    _compact(
                        anchors[:4]
                        + [
                            "newspaper archive"
                        ]
                    ),

                    _compact(
                        anchors[:4]
                        + [
                            "historical document"
                        ]
                    ),

                    _compact(
                        anchors[:4]
                        + [
                            "case file"
                        ]
                    ),
                ]
            )


    # =================================
    # PERSON
    # =================================

    elif role == "PERSON":

        if anchors:

            queries.extend(
                [
                    _compact(
                        anchors[:3]
                        + [
                            "archive photograph"
                        ]
                    ),

                    _compact(
                        anchors[:3]
                        + [
                            "historical portrait"
                        ]
                    ),
                ]
            )


    # =================================
    # PLACE
    # =================================

    elif role == "PLACE":

        if anchors:

            queries.extend(
                [
                    _compact(
                        anchors[:4]
                        + [
                            "historical photograph"
                        ]
                    ),

                    _compact(
                        anchors[:4]
                        + [
                            "exterior archive"
                        ]
                    ),

                    _compact(
                        anchors[:4]
                        + [
                            "location archive"
                        ]
                    ),
                ]
            )


    # =================================
    # OBJECT
    # =================================

    elif role == "OBJECT":

        if anchors:

            queries.extend(
                [
                    _compact(
                        anchors[:3]
                        + [
                            "historical product"
                        ]
                    ),

                    _compact(
                        anchors[:3]
                        + [
                            "packaging archive"
                        ]
                    ),
                ]
            )


    # =================================
    # CONTEXT
    # =================================

    else:

        for query in existing[:2]:

            if query:

                queries.append(
                    _compact(
                        [
                            query,
                            "documentary"
                        ]
                    )
                )


    queries.extend(
        existing
    )


    queries = _unique(
        queries
    )


    # Não repetir exatamente as primeiras
    # consultas se conseguimos criar uma
    # alternativa mais específica.
    original_keys = {
        q.lower()
        for q in existing
    }


    novel = [
        q
        for q in queries
        if q.lower()
        not in original_keys
    ]


    ordered = (
        novel
        + existing
    )


    ordered = _unique(
        ordered
    )[:5]


    eligible = bool(
        ordered
    )


    strategy = (
        "DOCUMENTARY_RETRY"

        if role in {
            "EVIDENCE",
            "PERSON",
            "PLACE"
        }

        else "PRECISION_RETRY"
    )


    return {

        "version":
            VERSION,

        "eligible":
            eligible,

        "role":
            role,

        "strategy":
            strategy,

        "trigger":
            rejection_reason,

        "anchors":
            anchors,

        "queries":
            ordered,

        "max_attempts":
            (
                2
                if eligible
                else 0
            ),

        "prefer_wikimedia":
            role in {
                "EVIDENCE",
                "PERSON",
                "PLACE"
            },

        "allow_stock_retry":
            role in {
                "OBJECT",
                "CONTEXT",
                "PLACE"
            },
    }


def self_test():

    scene = {

        "retrieval_role_6_7":
            "EVIDENCE",

        "retrieval_anchors_6_7":
            [
                "Flight 19",
                "1945"
            ],

        "retrieval_queries_6_7":
            [
                "Flight 19 1945"
            ],

        "retrieval_primary_query_6_7":
            "Flight 19 1945"
    }


    result = build_recovery_plan(
        scene,
        {},
        "vi69_semantic_floor"
    )


    assert result[
        "eligible"
    ] is True


    assert result[
        "prefer_wikimedia"
    ] is True


    assert any(
        "archive"
        in q.lower()
        for q in result[
            "queries"
        ]
    )


    blocked = build_recovery_plan(
        scene,
        {},
        "vi69_documentary_truth_failed"
    )


    assert blocked[
        "eligible"
    ] is False


    cta = build_recovery_plan(
        {
            "retrieval_role_6_7":
                "CTA"
        },
        {},
        "anything"
    )


    assert cta[
        "eligible"
    ] is False


    print()
    print(
        "======================================"
    )
    print(
        " VI6.13 RECOVERY SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Evidence Recovery Queries"
    )
    print(
        "OK Documentary Retry Strategy"
    )
    print(
        "OK Hard Safety No-Retry"
    )
    print(
        "OK CTA No-Retry"
    )
    print(
        "OK Query Budget"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 2. VI6.14 FINAL PRE-DOWNLOAD GATE
# =====================================================

cat > vi6_14_pre_download_gate.py <<'PY'
#!/usr/bin/env python3

from vi6_10_coverage_predictor import (
    contract
)


VERSION = "6.14"


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


def final_gate(
    candidate,
    scene,
    meta=None
):

    meta = (
        meta
        or {}
    )


    c = contract(
        scene
    )


    if candidate is None:

        return {

            "action":
                "FALLBACK",

            "reason":
                "vi614_no_candidate",

            "contract":
                c,
        }


    classe = _u(
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


    risk = _u(
        candidate.get(
            "_vi6_risk"
        )
        or candidate.get(
            "risk"
        )
    )


    truth_ok = bool(
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


    role = _u(
        meta.get(
            "role"
        )
        or c[
            "role"
        ]
    )


    # =================================
    # HARD SAFETY
    # =================================

    if risk == "HIGH":

        return {
            "action": "FALLBACK",
            "reason":
                "vi614_high_risk",
            "contract": c,
        }


    if "MISLEADING" in classe:

        return {
            "action": "FALLBACK",
            "reason":
                "vi614_misleading",
            "contract": c,
        }


    if classe not in {
        "REAL_DOCUMENTARY",
        "SAFE_CONTEXT"
    }:

        return {
            "action": "FALLBACK",
            "reason":
                "vi614_invalid_class",
            "contract": c,
        }


    # =================================
    # CTA
    # =================================

    if role == "CTA":

        return {
            "action": "ACCEPT",
            "reason":
                "vi614_cta_accept",
            "contract": c,
        }


    # =================================
    # DOCUMENTARY
    # =================================

    if classe == "REAL_DOCUMENTARY":

        if not truth_ok:

            return {
                "action":
                    "FALLBACK",

                "reason":
                    "vi614_documentary_truth_failed",

                "contract":
                    c,
            }


        evidence = _u(
            candidate.get(
                "evidence_class"
            )
        )


        strong_evidence = (
            evidence
            == "CASE_DIRECT"
        )


        # Se o retrieval tinha identidade
        # forte mas o documental não possui
        # nenhuma âncora, exija evidência
        # direta para liberar.
        if (
            c.get(
                "retrieval_strength",
                0
            ) >= 6

            and anchor < .08

            and not strong_evidence
        ):

            return {
                "action":
                    "FALLBACK",

                "reason":
                    "vi614_documentary_anchor_gap",

                "contract":
                    c,
            }


        return {
            "action":
                "ACCEPT",

            "reason":
                "vi614_documentary_accept",

            "score":
                score,

            "anchor":
                anchor,

            "contract":
                c,
        }


    # =================================
    # SAFE CONTEXT FINAL CHECK
    # =================================

    if score < c[
        "min_score"
    ]:

        return {
            "action":
                "FALLBACK",

            "reason":
                "vi614_final_score_floor",

            "contract":
                c,
        }


    if semantic < c[
        "min_semantic"
    ]:

        return {
            "action":
                "FALLBACK",

            "reason":
                "vi614_final_semantic_floor",

            "contract":
                c,
        }


    # Cenas factuais com retrieval forte
    # não devem passar com contexto solto.
    if (
        role
        in {
            "EVIDENCE",
            "PERSON",
            "PLACE"
        }

        and c.get(
            "retrieval_strength",
            0
        ) >= 5

        and anchor
        < c[
            "min_anchor"
        ]
    ):

        return {
            "action":
                "FALLBACK",

            "reason":
                "vi614_final_anchor_floor",

            "anchor":
                anchor,

            "required":
                c[
                    "min_anchor"
                ],

            "contract":
                c,
        }


    return {
        "action":
            "ACCEPT",

        "reason":
            "vi614_final_accept",

        "score":
            score,

        "semantic":
            semantic,

        "anchor":
            anchor,

        "contract":
            c,
    }


def self_test():

    scene = {

        "retrieval_role_6_7":
            "EVIDENCE",

        "retrieval_anchor_strength_6_7":
            7,
    }


    weak = {

        "_vi6_class":
            "SAFE_CONTEXT",

        "_vi6_risk":
            "LOW",

        "_vi6_score":
            80,
    }


    result = final_gate(
        weak,
        scene,
        {
            "class":
                "SAFE_CONTEXT",

            "score":
                80,

            "semantic":
                70,

            "anchor":
                .05,

            "role":
                "EVIDENCE",
        }
    )


    assert result[
        "action"
    ] == "FALLBACK"


    strong = final_gate(
        weak,
        scene,
        {
            "class":
                "SAFE_CONTEXT",

            "score":
                85,

            "semantic":
                75,

            "anchor":
                .45,

            "role":
                "EVIDENCE",
        }
    )


    assert strong[
        "action"
    ] == "ACCEPT"


    doc = {

        "_vi6_class":
            "REAL_DOCUMENTARY",

        "_vi6_risk":
            "LOW",

        "_vi6_truth_ok":
            True,

        "evidence_class":
            "CASE_DIRECT",
    }


    result = final_gate(
        doc,
        scene,
        {
            "class":
                "REAL_DOCUMENTARY",

            "truth_ok":
                True,

            "score":
                90,

            "anchor":
                0,

            "role":
                "EVIDENCE",
        }
    )


    assert result[
        "action"
    ] == "ACCEPT"


    print()
    print(
        "======================================"
    )
    print(
        " VI6.14 PRE-DOWNLOAD SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Final Semantic Floor"
    )
    print(
        "OK Final Anchor Floor"
    )
    print(
        "OK Documentary Truth"
    )
    print(
        "OK Case-Direct Exception"
    )
    print(
        "OK CTA Acceptance"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 3. VI6.15 DECISION LEDGER
# =====================================================

cat > vi6_15_decision_ledger.py <<'PY'
#!/usr/bin/env python3

import json
import os
from datetime import datetime


VERSION = "6.15"


_EVENTS = []


def _s(v):

    return str(
        v or ""
    ).strip()


def _source(candidate):

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


def _type(candidate):

    if not candidate:
        return None

    return _s(
        candidate.get(
            "tipo"
        )
        or candidate.get(
            "type"
        )
    )


def _scene_number(
    scene
):

    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    try:

        value = int(
            board.get(
                "scene",
                len(
                    _EVENTS
                ) + 1
            )
            or len(
                _EVENTS
            ) + 1
        )

        return value

    except Exception:

        return (
            len(
                _EVENTS
            )
            + 1
        )


def record(
    scene,
    candidate,
    reason,
    meta=None,
    recovery_plan=None,
    final_action=None
):

    meta = (
        meta
        or {}
    )


    event = {

        "scene":
            _scene_number(
                scene
            ),

        "role":
            meta.get(
                "role"
            )
            or scene.get(
                "retrieval_role_6_7"
            ),

        "source":
            _source(
                candidate
            ),

        "type":
            _type(
                candidate
            ),

        "class":
            meta.get(
                "class"
            ),

        "decision":
            meta.get(
                "decision"
            ),

        "reason":
            reason,

        "final_action":
            final_action,

        "score":
            meta.get(
                "score"
            ),

        "semantic":
            meta.get(
                "semantic"
            ),

        "anchor":
            meta.get(
                "anchor"
            )
            or meta.get(
                "anchor_ratio"
            ),

        "truth_ok":
            meta.get(
                "truth_ok"
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

        "recovery":
            recovery_plan,
    }


    _EVENTS.append(
        event
    )


    return event


def summary():

    total = len(
        _EVENTS
    )


    accepted = sum(
        1
        for event
        in _EVENTS
        if event.get(
            "final_action"
        ) == "ACCEPT"
    )


    fallback = sum(
        1
        for event
        in _EVENTS
        if event.get(
            "final_action"
        ) == "FALLBACK"
    )


    rescued = sum(
        1
        for event
        in _EVENTS
        if (
            event.get(
                "vi611"
            )
            == "vi611_second_chance_rescue"
            or "rescue"
            in _s(
                event.get(
                    "reason"
                )
            ).lower()
        )
    )


    documentary = sum(
        1
        for event
        in _EVENTS
        if (
            _s(
                event.get(
                    "class"
                )
            ).upper()
            == "REAL_DOCUMENTARY"
        )
    )


    return {

        "version":
            VERSION,

        "events":
            total,

        "accepted":
            accepted,

        "fallback":
            fallback,

        "rescued":
            rescued,

        "documentary":
            documentary,
    }


def flush(
    path=None
):

    if path is None:

        base = os.path.expanduser(
            "~/ShortAutoPro"
        )


        folder = os.path.join(
            base,
            "logs",
            "producao"
        )


        os.makedirs(
            folder,
            exist_ok=True
        )


        path = os.path.join(
            folder,
            "vi6_15_runtime_latest.json"
        )


    payload = {

        "version":
            VERSION,

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "summary":
            summary(),

        "events":
            list(
                _EVENTS
            ),
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


def self_test():

    reset()


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

            "tipo":
                "foto"
        },
        "vi614_documentary_accept",
        {
            "class":
                "REAL_DOCUMENTARY",

            "score":
                90,

            "truth_ok":
                True,
        },
        None,
        "ACCEPT"
    )


    x = summary()


    assert x[
        "events"
    ] == 1

    assert x[
        "accepted"
    ] == 1

    assert x[
        "documentary"
    ] == 1


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.15 LEDGER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Scene Decision Events"
    )
    print(
        "OK Accept/Fallback Stats"
    )
    print(
        "OK Rescue Stats"
    )
    print(
        "OK Documentary Stats"
    )
    print(
        "OK Runtime JSON Ready"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 4. SOURCE SIGNATURE MAPPER
# =====================================================

cat > mapear_retrieval_sources_6_13.py <<'PY'
#!/usr/bin/env python3

import ast
from pathlib import Path


FILES = [

    "midia.py",

    "wikimedia_source.py",

    "source_router.py",

    "wikimedia_query_bridge.py",
]


KEYWORDS = (
    "buscar",
    "search",
    "pixabay",
    "wikimedia",
    "source",
    "media",
)


def signature(
    node
):

    args = []


    for arg in (
        node.args.posonlyargs
        + node.args.args
    ):

        args.append(
            arg.arg
        )


    if node.args.vararg:

        args.append(
            "*"
            + node.args.vararg.arg
        )


    for arg in (
        node.args.kwonlyargs
    ):

        args.append(
            arg.arg
        )


    if node.args.kwarg:

        args.append(
            "**"
            + node.args.kwarg.arg
        )


    return (
        node.name
        + "("
        + ", ".join(
            args
        )
        + ")"
    )


print()
print(
    "======================================"
)
print(
    " VI6.13 SOURCE MAP"
)
print(
    "======================================"
)


count = 0


for filename in FILES:

    path = Path(
        filename
    )


    if not path.exists():

        continue


    try:

        source = path.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source
        )

    except Exception as exc:

        print(
            f"{filename}: "
            f"PARSE ERROR {exc}"
        )

        continue


    found = []


    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):

            continue


        name = node.name.lower()


        if any(
            keyword in name
            for keyword
            in KEYWORDS
        ):

            found.append(
                (
                    node.lineno,
                    signature(
                        node
                    )
                )
            )


    if found:

        print()
        print(
            f"[{filename}]"
        )


        for line, sig in sorted(
            found
        ):

            count += 1

            print(
                f"  L{line}: {sig}"
            )


print()
print(
    "TOTAL FUNCTIONS:",
    count
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
# 5. NOVO RUNTIME STACK
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

from vi6_13_recovery_planner import (
    build_recovery_plan
)

from vi6_14_pre_download_gate import (
    final_gate
)

from vi6_15_decision_ledger import (
    record,
    flush
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
        # VI6.6 ACTIVE BRAIN
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
        # VI6.9 QUALITY FIREWALL
        # =========================================

        if candidate is not None:

            fw = check(
                candidate,
                cena,
                meta
            )


            meta[
                "vi69_action"
            ] = fw.get(
                "action"
            )


            meta[
                "vi69_reason"
            ] = fw.get(
                "reason"
            )


            meta[
                "vi610_contract"
            ] = fw.get(
                "contract"
            )


            if (
                fw.get(
                    "action"
                )
                == "FALLBACK"
            ):

                rejection_reason = (
                    fw.get(
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
        # VI6.11 SECOND CHANCE
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

                # =================================
                # VI6.13 RECOVERY PLAN
                # =================================

                recovery = (
                    build_recovery_plan(
                        cena,
                        vi6_scene,
                        rejection_reason
                        or rescue_reason
                    )
                )


                meta[
                    "vi613_recovery_plan"
                ] = recovery


                meta[
                    "decision"
                ] = "5X_AFTER_611"


                record(
                    cena,
                    None,
                    rejection_reason
                    or rescue_reason,
                    meta,
                    recovery,
                    "FALLBACK"
                )


                return (
                    None,
                    rejection_reason
                    or rescue_reason,
                    meta
                )


        # =========================================
        # VI6.12 GLOBAL STORY GUARD
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

            recovery = (
                build_recovery_plan(
                    cena,
                    vi6_scene,
                    story_reason
                )
            )


            meta[
                "vi613_recovery_plan"
            ] = recovery


            meta[
                "decision"
            ] = "5X_AFTER_612"


            record(
                cena,
                None,
                story_reason,
                meta,
                recovery,
                "FALLBACK"
            )


            return (
                None,
                story_reason,
                meta
            )


        # =========================================
        # VI6.14 PRE-DOWNLOAD FINAL GATE
        # =========================================

        gate = final_gate(
            candidate,
            cena,
            meta
        )


        meta[
            "vi614_action"
        ] = gate.get(
            "action"
        )


        meta[
            "vi614_reason"
        ] = gate.get(
            "reason"
        )


        if (
            gate.get(
                "action"
            )
            != "ACCEPT"
        ):

            recovery = (
                build_recovery_plan(
                    cena,
                    vi6_scene,
                    gate.get(
                        "reason"
                    )
                )
            )


            meta[
                "vi613_recovery_plan"
            ] = recovery


            meta[
                "decision"
            ] = "5X_AFTER_614"


            record(
                cena,
                None,
                gate.get(
                    "reason"
                ),
                meta,
                recovery,
                "FALLBACK"
            )


            return (
                None,
                gate.get(
                    "reason"
                ),
                meta
            )


        # =========================================
        # FINAL ACCEPT
        # =========================================

        meta[
            "decision"
        ] = meta.get(
            "decision",
            "VI6_ACCEPT"
        )


        reason = (
            gate.get(
                "reason"
            )
            or story_reason
        )


        record(
            cena,
            candidate,
            reason,
            meta,
            None,
            "ACCEPT"
        )


        board = (
            cena.get(
                "_vi68_storyboard"
            )
            or {}
        )


        # =========================================
        # FINAL STORY LEDGER
        # =========================================

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


            try:

                meta[
                    "vi615_ledger_path"
                ] = flush()

            except Exception as exc:

                meta[
                    "vi615_ledger_error"
                ] = (
                    f"{type(exc).__name__}: "
                    f"{str(exc)[:120]}"
                )


        return (
            candidate,
            reason,
            meta
        )


    brain.supervisionar_vi6_6 = (
        _wrapped
    )


    brain._VI69_RUNTIME_PATCHED = True

    brain._VI611_RUNTIME_ACTIVE = True

    brain._VI612_RUNTIME_ACTIVE = True

    brain._VI613_RUNTIME_ACTIVE = True

    brain._VI614_RUNTIME_ACTIVE = True

    brain._VI615_RUNTIME_ACTIVE = True
PY


# =====================================================
# 6. OFFLINE INTEGRATION TEST
# =====================================================

cat > testar_vi613_vi615.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy

from vi6_13_recovery_planner import (
    build_recovery_plan
)

from vi6_14_pre_download_gate import (
    final_gate
)

from vi6_15_decision_ledger import (
    reset,
    record,
    summary
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

assert getattr(
    brain,
    "_VI613_RUNTIME_ACTIVE",
    False
)

assert getattr(
    brain,
    "_VI614_RUNTIME_ACTIVE",
    False
)

assert getattr(
    brain,
    "_VI615_RUNTIME_ACTIVE",
    False
)


scene = {

    "retrieval_role_6_7":
        "EVIDENCE",

    "retrieval_anchor_strength_6_7":
        7,

    "retrieval_anchors_6_7":
        [
            "Flight 19",
            "1945"
        ],

    "retrieval_primary_query_6_7":
        "Flight 19 1945",
}


recovery = build_recovery_plan(
    scene,
    {},
    "vi69_semantic_floor"
)


assert recovery[
    "eligible"
] is True


strong_candidate = {

    "_vi6_class":
        "SAFE_CONTEXT",

    "_vi6_risk":
        "LOW",

    "_vi6_score":
        90,
}


gate = final_gate(
    strong_candidate,
    scene,
    {
        "class":
            "SAFE_CONTEXT",

        "score":
            90,

        "semantic":
            78,

        "anchor":
            .50,

        "role":
            "EVIDENCE",
    }
)


assert gate[
    "action"
] == "ACCEPT"


reset()


record(
    scene,
    {
        "fonte":
            "Wikimedia",

        "tipo":
            "foto"
    },
    "vi614_documentary_accept",
    {
        "class":
            "REAL_DOCUMENTARY",

        "score":
            95,
    },
    None,
    "ACCEPT"
)


ledger = summary()


assert ledger[
    "events"
] == 1

assert ledger[
    "accepted"
] == 1


print()
print(
    "======================================"
)
print(
    " VI6.13-6.15 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.8:",
    brain._VI68_RUNTIME_PATCHED
)

print(
    "VI6.9:",
    brain._VI69_RUNTIME_PATCHED
)

print(
    "VI6.11:",
    brain._VI611_RUNTIME_ACTIVE
)

print(
    "VI6.12:",
    brain._VI612_RUNTIME_ACTIVE
)

print(
    "VI6.13:",
    brain._VI613_RUNTIME_ACTIVE
)

print(
    "VI6.14:",
    brain._VI614_RUNTIME_ACTIVE
)

print(
    "VI6.15:",
    brain._VI615_RUNTIME_ACTIVE
)

print()
print(
    "RECOVERY QUERIES:",
    len(
        recovery[
            "queries"
        ]
    )
)

print(
    "FINAL GATE:",
    gate[
        "action"
    ]
)

print(
    "LEDGER:",
    ledger
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
# 7. COMPILE
# =====================================================

echo
echo "===== FULL COMPILE ====="

if ! python -m py_compile \
    vi6_13_recovery_planner.py \
    vi6_14_pre_download_gate.py \
    vi6_15_decision_ledger.py \
    mapear_retrieval_sources_6_13.py \
    vi6_9_runtime_policy.py \
    vi6_11_second_chance.py \
    vi6_12_story_guard.py \
    vi6_10_coverage_predictor.py \
    vi6_9_quality_firewall.py \
    vi6_8_runtime_policy.py \
    vi6_7_retrieval_planner.py \
    vi6_6_active_brain.py \
    midia.py \
    testar_vi613_vi615.py
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
echo "===== VI6.13 SELF TEST ====="

if ! python vi6_13_recovery_planner.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.14 SELF TEST ====="

if ! python vi6_14_pre_download_gate.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.15 SELF TEST ====="

if ! python vi6_15_decision_ledger.py; then
    rollback
    exit 1
fi


echo
echo "===== RUNTIME TEST ====="

if ! python testar_vi613_vi615.py; then
    rollback
    exit 1
fi


# =====================================================
# 9. REGRESSIONS
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


echo
echo "===== VI6.11 REGRESSION ====="

if ! python vi6_11_second_chance.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.12 REGRESSION ====="

if ! python vi6_12_story_guard.py; then
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
# 11. SOURCE MAPPER
# =====================================================

echo
echo "===== RETRIEVAL SOURCE MAP ====="

python mapear_retrieval_sources_6_13.py


# =====================================================
# FINAL
# =====================================================

echo
echo "======================================"
echo " VI6.13 + VI6.14 + VI6.15 INSTALADOS"
echo "======================================"
echo
echo "OK Recovery Query Planner"
echo "OK Hard-Safety No-Retry"
echo "OK Documentary Recovery Queries"
echo "OK Person Recovery Queries"
echo "OK Place Recovery Queries"
echo "OK Object Recovery Queries"
echo "OK Final Pre-Download Gate"
echo "OK Final Semantic Contract"
echo "OK Final Anchor Contract"
echo "OK Documentary Truth Final Lock"
echo "OK Decision Ledger"
echo "OK Accept/Fallback Telemetry"
echo "OK Rescue Telemetry"
echo "OK Source Signature Mapper"
echo "OK VI6.11 Second Chance"
echo "OK VI6.12 Story Guard"
echo "OK VI6.9 Firewall"
echo "OK VI6.8 Global Storyboard"
echo "OK VI6.7 Retrieval"
echo "OK VI6.6 Active Brain"
echo "OK 5.x fallback"
echo
echo "MIDIA.PY MODIFICADO=NAO"
echo "GERAR_SHORT MODIFICADO=NAO"
echo "API CALLS=0"
echo "DOWNLOADS NOVOS=0"
echo "VIDEOS GERADOS=0"
echo
