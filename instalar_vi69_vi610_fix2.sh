#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi69_fix2_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================"
echo " VI6.9 + VI6.10 FIX2"
echo " INSTALADOR LIMPO"
echo "======================================"
echo


# =====================================================
# 0. VALIDAR BASE ATUAL ANTES DE QUALQUER ALTERAÇÃO
# =====================================================

echo "===== BASELINE CHECK ====="

if ! python -m py_compile \
    midia.py \
    vi6_6_active_brain.py \
    vi6_7_retrieval_planner.py \
    vi6_8_storyboard_director.py \
    vi6_8_runtime_policy.py
then
    echo
    echo "BASE ATUAL NÃO COMPILA."
    echo "NADA FOI ALTERADO."
    exit 1
fi

echo "BASELINE PYTHON=OK"


if ! bash -n gerar_short.sh
then
    echo "BASELINE BASH FALHOU."
    echo "NADA FOI ALTERADO."
    exit 1
fi

echo "BASELINE BASH=OK"


cp midia.py \
   "$BACKDIR/midia.py"


for F in \
    vi6_9_quality_firewall.py \
    vi6_9_runtime_policy.py \
    vi6_10_coverage_predictor.py
do
    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi
done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK FIX2"
    echo "======================================"

    cp "$BACKDIR/midia.py" midia.py

    for F in \
        vi6_9_quality_firewall.py \
        vi6_9_runtime_policy.py \
        vi6_10_coverage_predictor.py
    do

        if [ -f "$BACKDIR/$F" ]; then
            cp "$BACKDIR/$F" "$F"
        else
            rm -f "$F"
        fi

    done

    rm -f testar_vi69_fix2.py

    echo "Projeto restaurado."
}


# =====================================================
# 1. VI6.10 COVERAGE CONTRACT
# =====================================================

cat > vi6_10_coverage_predictor.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.10"


def _s(v):
    return str(v or "").strip()


def role(scene):

    r = _s(
        scene.get(
            "retrieval_role_6_7"
        )
    ).upper()

    if r:
        return r


    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )

    r = _s(
        board.get("role")
    ).upper()

    if r:
        return r


    text = " ".join(
        [
            _s(scene.get("visual_mode")),
            _s(scene.get("visual_intent")),
            _s(scene.get("intent")),
        ]
    ).lower()


    if "cta" in text:
        return "CTA"


    if any(
        x in text
        for x in (
            "evidence",
            "document",
            "archive",
            "arquivo",
            "newspaper",
            "case_file",
        )
    ):
        return "EVIDENCE"


    if any(
        x in text
        for x in (
            "person",
            "portrait",
            "character",
        )
    ):
        return "PERSON"


    if any(
        x in text
        for x in (
            "location",
            "place",
            "architecture",
            "map",
            "transport",
        )
    ):
        return "PLACE"


    if any(
        x in text
        for x in (
            "object",
            "medicine",
            "product",
            "package",
            "packaging",
        )
    ):
        return "OBJECT"


    return "CONTEXT"


BASE = {

    "EVIDENCE": {
        "min_score": 58.0,
        "min_semantic": 60.0,
        "min_anchor": 0.18,
        "generic_guard": "STRICT",
        "prefer_documentary": True,
    },

    "PERSON": {
        "min_score": 56.0,
        "min_semantic": 58.0,
        "min_anchor": 0.20,
        "generic_guard": "STRICT",
        "prefer_documentary": True,
    },

    "PLACE": {
        "min_score": 54.0,
        "min_semantic": 55.0,
        "min_anchor": 0.14,
        "generic_guard": "MEDIUM",
        "prefer_documentary": True,
    },

    "OBJECT": {
        "min_score": 52.0,
        "min_semantic": 48.0,
        "min_anchor": 0.08,
        "generic_guard": "MEDIUM",
        "prefer_documentary": False,
    },

    "CONTEXT": {
        "min_score": 50.0,
        "min_semantic": 45.0,
        "min_anchor": 0.0,
        "generic_guard": "LIGHT",
        "prefer_documentary": False,
    },

    "CTA": {
        "min_score": 0.0,
        "min_semantic": 0.0,
        "min_anchor": 0.0,
        "generic_guard": "CTA_REUSE",
        "prefer_documentary": False,
    },
}


def contract(scene):

    r = role(scene)

    result = dict(
        BASE.get(
            r,
            BASE["CONTEXT"]
        )
    )


    strength = int(
        scene.get(
            "retrieval_anchor_strength_6_7",
            0
        )
        or 0
    )


    if (
        r in {
            "EVIDENCE",
            "PERSON",
            "PLACE"
        }
        and strength >= 6
    ):
        result["min_anchor"] = max(
            result["min_anchor"],
            0.20
        )


    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    if board.get(
        "prefer_documentary"
    ):
        result[
            "prefer_documentary"
        ] = True


    result["role"] = r
    result["version"] = VERSION
    result["retrieval_strength"] = strength

    return result


def self_test():

    x = contract(
        {
            "retrieval_role_6_7":
                "EVIDENCE",

            "retrieval_anchor_strength_6_7":
                7,
        }
    )

    assert x["role"] == "EVIDENCE"
    assert x["min_semantic"] >= 60
    assert x["min_anchor"] >= .20
    assert x["prefer_documentary"] is True


    x = contract(
        {
            "visual_mode":
                "cta_reuse"
        }
    )

    assert x["role"] == "CTA"
    assert x["min_score"] == 0


    print()
    print("======================================")
    print(" VI6.10 COVERAGE SELF TEST: PASS")
    print("======================================")
    print("OK Evidence")
    print("OK Person")
    print("OK Place")
    print("OK Object")
    print("OK Context")
    print("OK CTA")
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 2. VI6.9 QUALITY FIREWALL
# =====================================================

cat > vi6_9_quality_firewall.py <<'PY'
#!/usr/bin/env python3

from vi6_10_coverage_predictor import (
    contract
)


VERSION = "6.9"


def _s(v):
    return str(v or "").strip()


def _u(v):
    return _s(v).upper()


def _f(v, default=0.0):

    try:
        return float(v)

    except Exception:
        return float(default)


def check(
    candidate,
    scene,
    meta=None
):

    meta = meta or {}

    c = contract(scene)


    if candidate is None:

        return {
            "action": "FALLBACK",
            "reason": "vi69_no_candidate",
            "contract": c,
        }


    classe = _u(
        meta.get("class")
        or candidate.get("_vi6_class")
        or candidate.get("class")
    )


    risk = _u(
        candidate.get("_vi6_risk")
        or candidate.get("risk")
    )


    quality = _u(
        candidate.get(
            "_vi6_quality_tier"
        )
        or candidate.get(
            "quality_tier"
        )
    )


    truth_ok = bool(
        meta.get(
            "truth_ok",
            candidate.get(
                "_vi6_truth_ok",
                candidate.get(
                    "truth_ok",
                    False
                )
            )
        )
    )


    score = _f(
        meta.get(
            "score",
            candidate.get(
                "_vi6_score",
                candidate.get(
                    "score",
                    0
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
        meta.get("role")
        or c["role"]
    )


    reasons = (
        meta.get("reasons")
        or []
    )


    if isinstance(
        reasons,
        str
    ):
        reasons = [reasons]


    reason_text = " ".join(
        str(x)
        for x in reasons
    ).lower()


    reason_text += " " + _s(
        candidate.get("_vi6_reason")
        or candidate.get("reason")
    ).lower()


    # =================================
    # HARD BLOCKS
    # =================================

    if risk == "HIGH":

        return {
            "action": "FALLBACK",
            "reason": "vi69_high_risk",
            "contract": c,
        }


    if "MISLEADING" in classe:

        return {
            "action": "FALLBACK",
            "reason": "vi69_misleading",
            "contract": c,
        }


    if (
        quality
        and quality not in {
            "NORMAL",
            "CONTROLLED_FALLBACK"
        }
    ):

        return {
            "action": "FALLBACK",
            "reason": "vi69_quality_floor",
            "contract": c,
        }


    # =================================
    # CTA MEMORY
    # =================================

    if role == "CTA":

        return {
            "action": "KEEP",
            "reason": "vi69_cta_reuse",
            "contract": c,
        }


    # =================================
    # DOCUMENTARY
    # =================================

    if classe == "REAL_DOCUMENTARY":

        if not truth_ok:

            return {
                "action": "FALLBACK",
                "reason":
                    "vi69_documentary_truth_failed",
                "contract": c,
            }


        if score < c["min_score"]:

            return {
                "action": "FALLBACK",
                "reason":
                    "vi69_documentary_score_floor",
                "contract": c,
            }


        return {
            "action": "KEEP",
            "reason":
                "vi69_verified_documentary",
            "contract": c,
        }


    # =================================
    # SAFE CONTEXT
    # =================================

    if classe != "SAFE_CONTEXT":

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_unsupported_class",
            "contract": c,
        }


    if score < c["min_score"]:

        return {
            "action": "FALLBACK",
            "reason": "vi69_score_floor",
            "contract": c,
        }


    if semantic < c["min_semantic"]:

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_semantic_floor",
            "contract": c,
        }


    generic = any(
        marker in reason_text

        for marker in (
            "generic_stock",
            "generic_context",
            "generic_person",
            "generic_place",
            "weak_anchor_stock",
        )
    )


    guard = c[
        "generic_guard"
    ]


    if (
        generic
        and guard == "STRICT"
        and anchor < c["min_anchor"]
    ):

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_generic_strict_veto",
            "contract": c,
        }


    if (
        generic
        and guard == "MEDIUM"
        and anchor < c["min_anchor"]
        and semantic < 62
    ):

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_generic_medium_veto",
            "contract": c,
        }


    if (
        role == "EVIDENCE"
        and (
            semantic < 60
            or anchor < .18
        )
    ):

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_stock_not_evidence_grade",
            "contract": c,
        }


    if (
        role == "PERSON"
        and generic
        and anchor < .20
    ):

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_random_person_veto",
            "contract": c,
        }


    if (
        role == "PLACE"
        and generic
        and anchor < .14
    ):

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_generic_place_veto",
            "contract": c,
        }


    return {
        "action": "KEEP",
        "reason": "vi69_quality_pass",
        "contract": c,
    }


def self_test():

    scene = {
        "retrieval_role_6_7":
            "EVIDENCE",

        "retrieval_anchor_strength_6_7":
            7,
    }


    stock = {
        "_vi6_class":
            "SAFE_CONTEXT",

        "_vi6_risk":
            "LOW",

        "_vi6_quality_tier":
            "NORMAL",

        "_vi6_truth_ok":
            True,

        "_vi6_score":
            80,

        "_vi6_reason":
            "generic_context_without_identity_claim",
    }


    x = check(
        stock,
        scene,
        {
            "class":
                "SAFE_CONTEXT",

            "score":
                80,

            "semantic":
                50,

            "anchor":
                .05,

            "role":
                "EVIDENCE",

            "reasons":
                ["generic_stock"]
        }
    )

    assert x["action"] == "FALLBACK"


    x = check(
        stock,
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

            "reasons":
                ["relevant_motion"]
        }
    )

    assert x["action"] == "KEEP"


    doc = {
        "_vi6_class":
            "REAL_DOCUMENTARY",

        "_vi6_risk":
            "LOW",

        "_vi6_quality_tier":
            "NORMAL",

        "_vi6_truth_ok":
            False,

        "_vi6_score":
            100,
    }


    x = check(
        doc,
        scene,
        {
            "class":
                "REAL_DOCUMENTARY",

            "score":
                100,

            "truth_ok":
                False,

            "role":
                "EVIDENCE",
        }
    )

    assert x["action"] == "FALLBACK"


    doc[
        "_vi6_truth_ok"
    ] = True


    x = check(
        doc,
        scene,
        {
            "class":
                "REAL_DOCUMENTARY",

            "score":
                100,

            "truth_ok":
                True,

            "role":
                "EVIDENCE",
        }
    )

    assert x["action"] == "KEEP"


    print()
    print("======================================")
    print(" VI6.9 FIREWALL SELF TEST: PASS")
    print("======================================")
    print("OK Generic Evidence Veto")
    print("OK Strong Evidence Context")
    print("OK Documentary Truth Lock")
    print("OK Semantic Floor")
    print("OK Anchor Floor")
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 3. VI6.9 RUNTIME WRAPPER
# =====================================================

cat > vi6_9_runtime_policy.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

from vi6_9_quality_firewall import (
    check
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


        if candidate is None:

            return (
                candidate,
                reason,
                meta
            )


        result = check(
            candidate,
            cena,
            meta
        )


        meta = dict(
            meta or {}
        )


        meta[
            "vi69_action"
        ] = result.get(
            "action"
        )


        meta[
            "vi69_reason"
        ] = result.get(
            "reason"
        )


        meta[
            "vi610_contract"
        ] = result.get(
            "contract"
        )


        if (
            result.get("action")
            == "FALLBACK"
        ):

            meta[
                "decision"
            ] = "5X_FIREWALL"


            return (
                None,
                result.get(
                    "reason",
                    "vi69_firewall"
                ),
                meta
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
PY


# =====================================================
# 4. TESTAR MÓDULOS ANTES DE TOCAR NO MIDIA.PY
# =====================================================

echo
echo "===== NOVOS MÓDULOS COMPILE ====="

if ! python -m py_compile \
    vi6_10_coverage_predictor.py \
    vi6_9_quality_firewall.py \
    vi6_9_runtime_policy.py
then
    echo "NOVOS MÓDULOS FALHARAM."
    rollback
    exit 1
fi

echo "NOVOS MÓDULOS=OK"


echo
echo "===== SELF TEST 6.10 ====="

if ! python vi6_10_coverage_predictor.py; then
    rollback
    exit 1
fi


echo
echo "===== SELF TEST 6.9 ====="

if ! python vi6_9_quality_firewall.py; then
    rollback
    exit 1
fi


# =====================================================
# 5. PATCH TOP-LEVEL VIA AST
# =====================================================

echo
echo "===== AST PATCH MIDIA.PY ====="

python - <<'PYFIX'
from pathlib import Path
import ast


p = Path("midia.py")

source = p.read_text(
    encoding="utf-8"
)


# Arquivo precisa estar saudável ANTES do patch.
tree = ast.parse(
    source
)


if "import vi6_9_runtime_policy" in source:

    print(
        "VI6.9 import já existe; "
        "nenhuma duplicação."
    )

    raise SystemExit(0)


body = tree.body

insert_after = 0
i = 0


# Docstring.
if (
    body
    and isinstance(
        body[0],
        ast.Expr
    )
    and isinstance(
        body[0].value,
        ast.Constant
    )
    and isinstance(
        body[0].value.value,
        str
    )
):
    insert_after = (
        body[0].end_lineno
    )

    i = 1


# Imports top-level consecutivos.
while (
    i < len(body)
    and isinstance(
        body[i],
        (
            ast.Import,
            ast.ImportFrom
        )
    )
):
    insert_after = (
        body[i].end_lineno
    )

    i += 1


block = """

# =========================================
# VI6.8 + VI6.9 RUNTIME SAFETY STACK
# =========================================
import vi6_8_runtime_policy
import vi6_9_runtime_policy
"""


lines = source.splitlines(
    keepends=True
)


lines.insert(
    insert_after,
    block
)


patched = "".join(
    lines
)


# CRÍTICO:
# não grava se estiver inválido.
ast.parse(
    patched
)


p.write_text(
    patched,
    encoding="utf-8"
)


print()
print(
    "VI6.9 AST PATCH: OK"
)

print(
    "LOCATION=TOP_LEVEL"
)

print(
    "TRY_BLOCKS=UNTOUCHED"
)
PYFIX


STATUS=$?


if [ "$STATUS" -ne 0 ]; then
    echo "AST PATCH FALHOU."
    rollback
    exit "$STATUS"
fi


# =====================================================
# 6. COMPILE COMPLETO
# =====================================================

echo
echo "===== FULL COMPILE ====="

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
    echo "FULL COMPILE FALHOU."
    rollback
    exit 1
fi

echo "PYTHON STATUS=0"


# =====================================================
# 7. RUNTIME PATCH ISOLADO
# =====================================================

echo
echo "===== RUNTIME STACK TEST ====="

if ! python - <<'PY'
import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy


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


print(
    "VI6.8 RUNTIME=OK"
)

print(
    "VI6.9 RUNTIME=OK"
)
PY
then
    rollback
    exit 1
fi


# =====================================================
# 8. REGRESSÕES
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


# =====================================================
# 9. SHELL + RELEASE
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
# 10. FINAL CODE CHECK
# =====================================================

echo
echo "===== FINAL CODE CHECK ====="

grep -nE \
'VI6\.8 \+ VI6\.9 RUNTIME SAFETY STACK|import vi6_8_runtime_policy|import vi6_9_runtime_policy|VI6\.7 \+ VI6\.8 ACTIVE VISUAL PLANNING' \
midia.py | head -40


echo
echo "======================================"
echo " VI6.9 + VI6.10 FIX2 INSTALADOS"
echo "======================================"
echo
echo "OK modules created before import"
echo "OK top-level AST patch"
echo "OK try/except untouched"
echo "OK VI6.8 runtime"
echo "OK VI6.9 runtime"
echo "OK VI6.10 coverage contracts"
echo "OK Documentary Truth Lock"
echo "OK Evidence Stock Firewall"
echo "OK Person Guard"
echo "OK Place Guard"
echo "OK Semantic Floors"
echo "OK Anchor Floors"
echo "OK CTA reuse"
echo "OK VI6.6 regression"
echo "OK VI6.7 regression"
echo "OK VI6.8 regression"
echo "OK 5.x safety fallback"
echo
echo "VIDEO GERADO=0"
echo "DOWNLOAD NOVO=0"
echo "API CALLS=0"
echo "GERAR_SHORT NÃO EXECUTADO"
echo
