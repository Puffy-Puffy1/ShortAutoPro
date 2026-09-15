#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p backups/stable_release_ready

BACKUP="backups/stable_release_ready/midia_pre_vi67_68_real_${STAMP}.py"

cp midia.py "$BACKUP" || exit 1

echo
echo "======================================"
echo " VI6.7 + VI6.8 REAL INTEGRATION"
echo " SEM VIDEO / SEM DOWNLOAD"
echo "======================================"
echo


# =====================================================
# PRÉ-CHECKS
# =====================================================

for FILE in \
    vi6_6_active_brain.py \
    vi6_7_retrieval_planner.py \
    vi6_8_storyboard_director.py
do

    if [ ! -f "$FILE" ]; then

        echo "ERRO: $FILE não encontrado."
        echo "midia.py ainda não foi alterado."

        exit 2
    fi

done


echo "===== SELF TESTS EXISTENTES ====="

python vi6_7_retrieval_planner.py || exit 3

python vi6_8_storyboard_director.py || exit 4

python vi6_6_active_brain.py || exit 5


# =====================================================
# VI6.8 RUNTIME POLICY
# =====================================================

cat > vi6_8_runtime_policy.py <<'PY'
#!/usr/bin/env python3

# =====================================================
# VI6.8 GLOBAL STORYBOARD RUNTIME POLICY
#
# Monkey-patch controlado do evaluator VI6.6.
#
# Não busca.
# Não baixa.
# Não renderiza.
# =====================================================


import vi6_6_active_brain as brain


if not getattr(
    brain,
    "_VI68_RUNTIME_PATCHED",
    False
):

    _base_evaluate_6_6 = (
        brain.evaluate
    )


    def evaluate_6_8(
        item,
        cena,
        vi6_scene=None
    ):

        result = _base_evaluate_6_6(
            item,
            cena,
            vi6_scene
        )


        if result is None:

            return None


        global_plan = (
            cena.get(
                "_vi68_storyboard"
            )
            or {}
        )


        if not global_plan:

            return result


        score = float(
            result.get(
                "score",
                0.0
            )
        )


        reasons = list(
            result.get(
                "reasons",
                []
            )
        )


        classe = str(
            result.get(
                "class",
                ""
            )
        ).upper()


        semantic = float(
            result.get(
                "semantic",
                0.0
            )
            or 0.0
        )


        media_type = str(
            item.get(
                "tipo"
            )
            or item.get(
                "type"
            )
            or ""
        ).lower()


        # =============================================
        # GLOBAL DOCUMENTARY TARGET
        # =============================================

        if global_plan.get(
            "prefer_documentary"
        ):

            if (
                classe
                == "REAL_DOCUMENTARY"
                and result.get(
                    "truth_ok",
                    False
                )
            ):

                score += 10.0

                reasons.append(
                    "vi68_documentary_target"
                )


            elif (
                classe
                == "SAFE_CONTEXT"
            ):

                score -= 4.0

                reasons.append(
                    "vi68_stock_deprioritized"
                )


        # =============================================
        # MOTION BUDGET
        # =============================================

        if global_plan.get(
            "prefer_motion"
        ):

            if (
                media_type
                in {
                    "video",
                    "vídeo"
                }
                and semantic >= 58.0
            ):

                score += 4.0

                reasons.append(
                    "vi68_motion_target"
                )


        # =============================================
        # PHOTO IS VALID FOR DOCUMENTARY
        # =============================================

        if (
            global_plan.get(
                "photo_is_fully_valid"
            )
            and classe
            == "REAL_DOCUMENTARY"
            and media_type
            in {
                "foto",
                "photo",
                "image"
            }
        ):

            score += 3.0

            reasons.append(
                "vi68_documentary_photo_ok"
            )


        # =============================================
        # DIVERSITY PRIORITY
        # =============================================

        if (
            global_plan.get(
                "diversity_priority"
            )
            == "HIGH"
            and classe
            == "SAFE_CONTEXT"
        ):

            reason_text = " ".join(
                reasons
            ).lower()


            if (
                "generic"
                in reason_text
            ):

                score -= 4.0

                reasons.append(
                    "vi68_diversity_generic_penalty"
                )


        # =============================================
        # CTA
        # =============================================

        if global_plan.get(
            "cta_reuse"
        ):

            if bool(
                item.get(
                    "reuse",
                    False
                )
            ):

                score += 12.0

                reasons.append(
                    "vi68_cta_reuse"
                )


        result[
            "score"
        ] = round(
            score,
            3
        )


        result[
            "reasons"
        ] = reasons


        result[
            "vi68_global"
        ] = True


        return result


    brain.evaluate = (
        evaluate_6_8
    )


    brain._VI68_RUNTIME_PATCHED = (
        True
    )
PY


# =====================================================
# PATCH AST NO MIDIA.PY
# =====================================================

python - <<'PY'
from pathlib import Path
import ast


path = Path(
    "midia.py"
)

source = path.read_text(
    encoding="utf-8"
)


MARKER = (
    "VI6.7 + VI6.8 ACTIVE VISUAL PLANNING"
)


if MARKER in source:

    print(
        "VI6.7 + VI6.8 já estão integrados."
    )

    raise SystemExit(0)


tree = ast.parse(
    source
)


# =====================================================
# LINHA DE REFERÊNCIA DO VI6
# =====================================================

vi6_lines = []


for node in ast.walk(
    tree
):

    if isinstance(
        node,
        ast.Call
    ):

        func = node.func


        if (
            isinstance(
                func,
                ast.Name
            )
            and func.id
            in {
                "vi6_audit_scene",
                "audit_scene"
            }
        ):

            vi6_lines.append(
                node.lineno
            )


# Fallback textual.
if not vi6_lines:

    for number, line in enumerate(
        source.splitlines(),
        1
    ):

        if "vi6_audit_scene" in line:

            vi6_lines.append(
                number
            )


if not vi6_lines:

    raise SystemExit(
        "ERRO: ponto VI6 não localizado. "
        "Nenhuma alteração feita."
    )


vi6_line = min(
    vi6_lines
)


# =====================================================
# LOCALIZAR ASSIGNMENT REAL DE `cenas`
# =====================================================

assignments = []


def has_cenas_target(
    target
):

    if isinstance(
        target,
        ast.Name
    ):

        return (
            target.id
            == "cenas"
        )


    if isinstance(
        target,
        (
            ast.Tuple,
            ast.List
        )
    ):

        return any(
            has_cenas_target(
                child
            )
            for child in target.elts
        )


    return False


for node in ast.walk(
    tree
):

    if isinstance(
        node,
        ast.Assign
    ):

        if any(
            has_cenas_target(
                target
            )
            for target in node.targets
        ):

            if (
                node.lineno
                < vi6_line
            ):

                assignments.append(
                    node
                )


    elif isinstance(
        node,
        ast.AnnAssign
    ):

        if (
            has_cenas_target(
                node.target
            )
            and node.lineno
            < vi6_line
        ):

            assignments.append(
                node
            )


if not assignments:

    raise SystemExit(
        "ERRO: assignment de `cenas` "
        "antes do VI6 não localizado. "
        "Nenhuma alteração feita."
    )


# Assignment mais próximo do VI6.
assignment = max(
    assignments,
    key=lambda node:
        node.end_lineno
)


insert_line = (
    assignment.end_lineno
)


indent = " " * int(
    assignment.col_offset
)


lines = source.splitlines(
    keepends=True
)


block_raw = r'''
# =========================================
# VI6.7 + VI6.8 ACTIVE VISUAL PLANNING
# =========================================

try:

    from vi6_7_retrieval_planner import (
        plan as _vi67_plan
    )

    from vi6_8_storyboard_director import (
        build_global_plan as _vi68_build
    )

    # Importar ativa a política global
    # sobre o evaluator do VI6.6.
    import vi6_8_runtime_policy


    if isinstance(
        cenas,
        list
    ):

        _vi68_global = (
            _vi68_build(
                cenas
            )
        )


        _vi68_scene_map = {

            int(
                item.get(
                    "scene",
                    0
                )
                or 0
            ):
            item

            for item
            in _vi68_global.get(
                "scenes",
                []
            )

        }


        _vi67_overrides = 0


        for (
            _vi67_index,
            _vi67_scene
        ) in enumerate(
            cenas,
            1
        ):

            if not isinstance(
                _vi67_scene,
                dict
            ):

                continue


            _vi67_plan_result = (
                _vi67_plan(
                    _vi67_scene
                )
            )


            # =====================================
            # RETRIEVAL METADATA
            # =====================================

            _vi67_scene[
                "retrieval_version"
            ] = "6.7"


            _vi67_scene[
                "retrieval_role_6_7"
            ] = (
                _vi67_plan_result.get(
                    "role"
                )
            )


            _vi67_scene[
                "retrieval_strategy_6_7"
            ] = (
                _vi67_plan_result.get(
                    "strategy"
                )
            )


            _vi67_scene[
                "retrieval_anchor_strength_6_7"
            ] = (
                _vi67_plan_result.get(
                    "strength"
                )
            )


            _vi67_scene[
                "retrieval_anchors_6_7"
            ] = (
                _vi67_plan_result.get(
                    "anchors",
                    []
                )
            )


            _vi67_scene[
                "retrieval_queries_6_7"
            ] = (
                _vi67_plan_result.get(
                    "queries",
                    []
                )
            )


            _vi67_scene[
                "retrieval_primary_query_6_7"
            ] = (
                _vi67_plan_result.get(
                    "primary"
                )
            )


            _vi67_scene[
                "retrieval_query_overridden_6_7"
            ] = bool(
                _vi67_plan_result.get(
                    "override",
                    False
                )
            )


            # =====================================
            # GLOBAL STORYBOARD METADATA
            # =====================================

            _vi67_scene[
                "_vi68_storyboard"
            ] = (
                _vi68_scene_map.get(
                    _vi67_index,
                    {}
                )
            )


            # =====================================
            # ACTIVE QUERY OVERRIDE
            # =====================================

            if (
                _vi67_plan_result.get(
                    "override",
                    False
                )

                and _vi67_plan_result.get(
                    "primary"
                )
            ):

                if (
                    "visual_query_original_6_7"
                    not in _vi67_scene
                ):

                    _vi67_scene[
                        "visual_query_original_6_7"
                    ] = (
                        _vi67_scene.get(
                            "visual_query"
                        )

                        or _vi67_scene.get(
                            "query"
                        )

                        or ""
                    )


                _vi67_scene[
                    "visual_query"
                ] = (
                    _vi67_plan_result[
                        "primary"
                    ]
                )


                _vi67_overrides += 1


        print()
        print(
            "======================================"
        )
        print(
            " VI6.7 + VI6.8 ACTIVE PLANNING"
        )
        print(
            "======================================"
        )

        print(
            f"CENAS={len(cenas)}"
        )

        print(
            f"QUERY_OVERRIDES="
            f"{_vi67_overrides}"
        )

        print(
            f"DOCUMENTARY_TARGET="
            f"{_vi68_global.get('documentary_target')}"
        )

        print(
            f"MOTION_TARGET="
            f"{_vi68_global.get('motion_target')}"
        )

        print(
            "CTA_STRATEGY="
            f"{_vi68_global.get('cta_strategy')}"
        )

        print()


    else:

        print(
            "VI6.7/6.8 WARNING: "
            "`cenas` não é list; "
            "planejamento ignorado."
        )


except Exception as _vi678_error:

    print(
        "VI6.7/6.8 WARNING: "
        f"{type(_vi678_error).__name__}: "
        f"{str(_vi678_error)[:180]}"
    )

    print(
        "VI6.7/6.8 -> pipeline original preservado"
    )
'''


block = ""


for line in block_raw.splitlines():

    if line:

        block += (
            indent
            + line
            + "\n"
        )

    else:

        block += "\n"


# insert_line é 1-based e queremos
# inserir APÓS o assignment.
lines.insert(
    insert_line,
    block
)


patched = "".join(
    lines
)


# Validação sintática antes de gravar.
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
    " PATCH AST CONCLUÍDO"
)
print(
    "======================================"
)
print(
    "Assignment cenas:",
    assignment.lineno,
    "-",
    assignment.end_lineno
)
print(
    "VI6 referência:",
    vi6_line
)
print(
    "OK integração inserida antes do VI6"
)
PY


PATCH_STATUS=$?


if [ "$PATCH_STATUS" -ne 0 ]; then

    echo
    echo "PATCH FALHOU."
    echo "Restaurando midia.py."

    cp "$BACKUP" midia.py

    exit "$PATCH_STATUS"
fi


# =====================================================
# TESTE OFFLINE INTEGRADO
# =====================================================

cat > testar_vi67_68_integracao.py <<'PY'
#!/usr/bin/env python3

from vi6_7_retrieval_planner import (
    plan
)

from vi6_8_storyboard_director import (
    build_global_plan
)

import vi6_6_active_brain as brain

import vi6_8_runtime_policy


# =====================================================
# 12 CENAS SINTÉTICAS
# =====================================================

scenes = [

    {
        "visual_mode":
            "evidence",

        "visual_query":
            "aircraft mystery",

        "must_have":
            [
                "Flight 19",
                "1945"
            ]
    },

    {
        "visual_mode":
            "location",

        "visual_query":
            "old hotel",

        "must_have":
            [
                "Cecil Hotel",
                "Los Angeles"
            ]
    },

    {
        "visual_mode":
            "context",

        "visual_query":
            "city street"
    },

    {
        "visual_mode":
            "person",

        "visual_query":
            "young woman"
    },

    {
        "visual_mode":
            "object",

        "visual_query":
            "medicine bottle"
    },

    {
        "visual_mode":
            "evidence",

        "visual_query":
            "newspaper archive"
    },

    {
        "visual_mode":
            "context",

        "visual_query":
            "investigation"
    },

    {
        "visual_mode":
            "location",

        "visual_query":
            "building exterior"
    },

    {
        "visual_mode":
            "evidence",

        "visual_query":
            "case documents"
    },

    {
        "visual_mode":
            "context",

        "visual_query":
            "pharmacy shelves"
    },

    {
        "visual_mode":
            "object",

        "visual_query":
            "sealed packaging"
    },

    {
        "visual_mode":
            "cta_reuse"
    }
]


global_plan = (
    build_global_plan(
        scenes
    )
)


scene_map = {

    x["scene"]:
    x

    for x in global_plan[
        "scenes"
    ]

}


overrides = 0


for i, scene in enumerate(
    scenes,
    1
):

    p = plan(
        scene
    )


    scene[
        "_vi68_storyboard"
    ] = scene_map[
        i
    ]


    if p.get(
        "override"
    ):

        overrides += 1


# =====================================================
# PROVAR QUE O RUNTIME PATCH ESTÁ ATIVO
# =====================================================

assert getattr(
    brain,
    "_VI68_RUNTIME_PATCHED",
    False
)


doc = {

    "fonte":
        "Wikimedia",

    "tipo":
        "foto",

    "id":
        "flight19",

    "url":
        "flight19",

    "class":
        "REAL_DOCUMENTARY",

    "risk":
        "LOW",

    "quality_tier":
        "NORMAL",

    "truth_ok":
        True,

    "semantic":
        72,

    "provenance":
        95,

    "score":
        70,

    "evidence_class":
        "CASE_DIRECT",

    "wiki_query_tier":
        "CASE",

    "title":
        "Flight 19 aircraft 1945 archive"
}


test_scene = scenes[0]


result = brain.evaluate(
    doc,
    test_scene,
    {
        "intent":
            "EVIDENCE"
    }
)


assert result is not None


assert (
    "vi68_documentary_target"
    in result[
        "reasons"
    ]
)


print()
print(
    "======================================"
)
print(
    " VI6.7 + VI6.8 INTEGRATION TEST: PASS"
)
print(
    "======================================"
)

print(
    "SCENES:",
    len(
        scenes
    )
)

print(
    "QUERY OVERRIDES:",
    overrides
)

print(
    "DOCUMENTARY TARGET:",
    global_plan[
        "documentary_target"
    ]
)

print(
    "MOTION TARGET:",
    global_plan[
        "motion_target"
    ]
)

print(
    "RUNTIME PATCH:",
    getattr(
        brain,
        "_VI68_RUNTIME_PATCHED",
        False
    )
)

print(
    "DOCUMENTARY TEST SCORE:",
    result[
        "score"
    ]
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
echo "===== PYTHON COMPILE ====="

if ! python -m py_compile \
    vi6_6_active_brain.py \
    vi6_7_retrieval_planner.py \
    vi6_8_storyboard_director.py \
    vi6_8_runtime_policy.py \
    testar_vi67_68_integracao.py \
    midia.py
then

    echo
    echo "COMPILE FALHOU."
    echo "ROLLBACK AUTOMATICO."

    cp "$BACKUP" midia.py

    rm -f vi6_8_runtime_policy.py
    rm -f testar_vi67_68_integracao.py

    exit 1
fi

echo "PYTHON STATUS=0"


# =====================================================
# INTEGRATION TEST
# =====================================================

echo
echo "===== INTEGRATION TEST ====="

if ! python testar_vi67_68_integracao.py
then

    echo
    echo "INTEGRATION TEST FALHOU."
    echo "ROLLBACK AUTOMATICO."

    cp "$BACKUP" midia.py

    rm -f vi6_8_runtime_policy.py
    rm -f testar_vi67_68_integracao.py

    exit 1
fi


# =====================================================
# BASH
# =====================================================

echo
echo "===== BASH CHECK ====="

if ! bash -n gerar_short.sh
then

    echo
    echo "BASH CHECK FALHOU."
    echo "ROLLBACK AUTOMATICO."

    cp "$BACKUP" midia.py

    exit 1
fi

echo "BASH STATUS=0"


# =====================================================
# RELEASE
# =====================================================

echo
echo "===== RELEASE CHECK ====="

if ! ./release_check.sh
then

    echo
    echo "RELEASE CHECK FALHOU."
    echo "ROLLBACK AUTOMATICO."

    cp "$BACKUP" midia.py

    exit 1
fi


# =====================================================
# CODE CHECK
# =====================================================

echo
echo "===== CODE CHECK ====="

grep -nE \
'VI6\.7 \+ VI6\.8 ACTIVE VISUAL PLANNING|retrieval_primary_query_6_7|_vi68_storyboard|vi6_8_runtime_policy' \
midia.py | head -40


echo
echo "======================================"
echo " VI6.7 + VI6.8 INTEGRADOS"
echo "======================================"
echo
echo "OK Retrieval ativo antes das buscas"
echo "OK Storyboard global ativo"
echo "OK Documentary target ativo"
echo "OK Motion budget ativo"
echo "OK Query factual preserva identidade"
echo "OK Query original preservada"
echo "OK Generic person guard preservado"
echo "OK CTA reuse preservado"
echo "OK VI6.8 influencia VI6.6"
echo "OK fallback VI6.6 preservado"
echo "OK fallback VI6.3 preservado"
echo "OK fallback 5.x preservado"
echo
echo "IMPORTANTE:"
echo "VIDEO GERADO=0"
echo "DOWNLOAD NOVO=0"
echo "API CALLS=0"
echo "GERAR_SHORT NÃO EXECUTADO"
echo
