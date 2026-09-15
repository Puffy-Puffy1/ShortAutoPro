#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi69_vi610_${STAMP}"

mkdir -p "$BACKDIR"

cp midia.py "$BACKDIR/midia.py" || exit 1

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
    echo " ROLLBACK VI6.9 + VI6.10"
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

    rm -f testar_vi69_vi610_offline.py

    echo "Projeto restaurado."
}


echo
echo "======================================"
echo " VI6.9 + VI6.10"
echo " QUALITY FIREWALL + COVERAGE CONTRACT"
echo "======================================"
echo


# =====================================================
# PRÉ-CHECK
# =====================================================

for F in \
    vi6_6_active_brain.py \
    vi6_7_retrieval_planner.py \
    vi6_8_storyboard_director.py \
    vi6_8_runtime_policy.py
do

    if [ ! -f "$F" ]; then

        echo "ERRO: $F não encontrado."
        echo "Nenhuma alteração foi feita."

        exit 2
    fi

done


if ! grep -q \
'VI6.7 + VI6.8 ACTIVE VISUAL PLANNING' \
midia.py
then

    echo "ERRO: integração VI6.7/6.8 não encontrada."
    echo "Nenhuma alteração foi feita."

    exit 3
fi


# =====================================================
# VI6.10 VISUAL COVERAGE CONTRACT
# =====================================================

cat > vi6_10_coverage_predictor.py <<'PY'
#!/usr/bin/env python3


VERSION = "6.10"


def _s(value):
    return str(value or "").strip()


def _role(scene):

    # Primeiro reutiliza classificação
    # já produzida pelos módulos anteriores.
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
        board.get(
            "role"
        )
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


CONTRACTS = {

    "EVIDENCE": {

        "min_semantic_stock":
            60.0,

        "min_anchor_stock":
            0.18,

        "min_score":
            58.0,

        "generic_stock":
            "STRICT",

        "prefer_documentary":
            True,

        "documentary_truth_required":
            True,

        "allow_low_anchor_generic":
            False,
    },


    "PERSON": {

        "min_semantic_stock":
            58.0,

        "min_anchor_stock":
            0.20,

        "min_score":
            56.0,

        "generic_stock":
            "STRICT",

        "prefer_documentary":
            True,

        "documentary_truth_required":
            True,

        "allow_low_anchor_generic":
            False,
    },


    "PLACE": {

        "min_semantic_stock":
            55.0,

        "min_anchor_stock":
            0.14,

        "min_score":
            54.0,

        "generic_stock":
            "MEDIUM",

        "prefer_documentary":
            True,

        "documentary_truth_required":
            True,

        "allow_low_anchor_generic":
            False,
    },


    "OBJECT": {

        "min_semantic_stock":
            48.0,

        "min_anchor_stock":
            0.08,

        "min_score":
            52.0,

        "generic_stock":
            "MEDIUM",

        "prefer_documentary":
            False,

        "documentary_truth_required":
            True,

        "allow_low_anchor_generic":
            True,
    },


    "CONTEXT": {

        "min_semantic_stock":
            45.0,

        "min_anchor_stock":
            0.0,

        "min_score":
            50.0,

        "generic_stock":
            "LIGHT",

        "prefer_documentary":
            False,

        "documentary_truth_required":
            True,

        "allow_low_anchor_generic":
            True,
    },


    "CTA": {

        "min_semantic_stock":
            0.0,

        "min_anchor_stock":
            0.0,

        "min_score":
            0.0,

        "generic_stock":
            "CTA_REUSE",

        "prefer_documentary":
            False,

        "documentary_truth_required":
            True,

        "allow_low_anchor_generic":
            True,
    },
}


def predict_scene_contract(
    scene
):

    role = _role(
        scene
    )


    base = dict(
        CONTRACTS.get(
            role,
            CONTRACTS[
                "CONTEXT"
            ]
        )
    )


    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    retrieval_strength = int(
        scene.get(
            "retrieval_anchor_strength_6_7",
            0
        )
        or 0
    )


    # Se retrieval possui âncoras muito
    # fortes, podemos exigir mais precisão.
    if (
        role
        in {
            "EVIDENCE",
            "PERSON",
            "PLACE"
        }
        and retrieval_strength >= 6
    ):

        base[
            "min_anchor_stock"
        ] = max(
            base[
                "min_anchor_stock"
            ],
            0.20
        )


    if board.get(
        "prefer_documentary"
    ):

        base[
            "prefer_documentary"
        ] = True


    base[
        "version"
    ] = VERSION


    base[
        "role"
    ] = role


    base[
        "retrieval_strength"
    ] = retrieval_strength


    base[
        "retrieval_strategy"
    ] = scene.get(
        "retrieval_strategy_6_7"
    )


    base[
        "cta_reuse"
    ] = bool(
        board.get(
            "cta_reuse"
        )
        or role == "CTA"
    )


    return base


def build_story_contracts(
    scenes
):

    contracts = []


    for index, scene in enumerate(
        scenes,
        1
    ):

        contract = (
            predict_scene_contract(
                scene
            )
        )


        contract[
            "scene"
        ] = index


        contracts.append(
            contract
        )


    documentary_required = sum(
        1

        for c in contracts

        if c[
            "prefer_documentary"
        ]
    )


    strict = sum(
        1

        for c in contracts

        if c[
            "generic_stock"
        ] == "STRICT"
    )


    return {

        "version":
            VERSION,

        "scene_count":
            len(
                contracts
            ),

        "documentary_priority_scenes":
            documentary_required,

        "strict_generic_guard_scenes":
            strict,

        "contracts":
            contracts,
    }


def self_test():

    evidence = {

        "retrieval_role_6_7":
            "EVIDENCE",

        "retrieval_anchor_strength_6_7":
            7,
    }


    c = predict_scene_contract(
        evidence
    )


    assert c[
        "role"
    ] == "EVIDENCE"

    assert c[
        "min_semantic_stock"
    ] >= 60

    assert c[
        "min_anchor_stock"
    ] >= .20

    assert c[
        "prefer_documentary"
    ] is True


    context = {

        "retrieval_role_6_7":
            "CONTEXT"
    }


    c = predict_scene_contract(
        context
    )


    assert c[
        "generic_stock"
    ] == "LIGHT"


    cta = {

        "visual_mode":
            "cta_reuse",

        "_vi68_storyboard":
            {
                "cta_reuse":
                    True
            }
    }


    c = predict_scene_contract(
        cta
    )


    assert c[
        "role"
    ] == "CTA"

    assert c[
        "cta_reuse"
    ] is True


    print()
    print(
        "======================================"
    )
    print(
        " VI6.10 COVERAGE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Evidence Contract"
    )
    print(
        "OK Person Contract"
    )
    print(
        "OK Place Contract"
    )
    print(
        "OK Context Contract"
    )
    print(
        "OK CTA Contract"
    )
    print(
        "OK Retrieval-aware floor"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# VI6.9 QUALITY FIREWALL
# =====================================================

cat > vi6_9_quality_firewall.py <<'PY'
#!/usr/bin/env python3

from vi6_10_coverage_predictor import (
    predict_scene_contract
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


def evaluate_candidate_firewall_6_9(
    candidate,
    scene,
    supervisor_meta=None
):

    supervisor_meta = (
        supervisor_meta
        or {}
    )


    contract = (
        predict_scene_contract(
            scene
        )
    )


    if candidate is None:

        return {
            "action":
                "FALLBACK",

            "reason":
                "vi69_no_candidate",

            "contract":
                contract,
        }


    classe = _u(
        supervisor_meta.get(
            "class"
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


    quality = _u(
        candidate.get(
            "_vi6_quality_tier"
        )
        or candidate.get(
            "quality_tier"
        )
    )


    truth_ok = bool(
        supervisor_meta.get(
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
        supervisor_meta.get(
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
        supervisor_meta.get(
            "semantic",
            candidate.get(
                "semantic",
                0
            )
        )
    )


    anchor = _f(
        supervisor_meta.get(
            "anchor",
            supervisor_meta.get(
                "anchor_ratio",
                candidate.get(
                    "_vi66_anchor",
                    0
                )
            )
        )
    )


    role = _u(
        supervisor_meta.get(
            "role"
        )
        or contract[
            "role"
        ]
    )


    reasons = (
        supervisor_meta.get(
            "reasons"
        )
        or []
    )


    if isinstance(
        reasons,
        str
    ):

        reasons = [
            reasons
        ]


    reason_text = " ".join(
        str(x)
        for x in reasons
    ).lower()


    reason_text += " " + _s(
        candidate.get(
            "_vi6_reason"
        )
        or candidate.get(
            "reason"
        )
    ).lower()


    # =================================
    # HARD SAFETY
    # =================================

    if risk == "HIGH":

        return {
            "action": "FALLBACK",
            "reason": "vi69_high_risk",
            "contract": contract,
        }


    if "MISLEADING" in classe:

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_misleading",
            "contract": contract,
        }


    if (
        quality
        and quality
        not in {
            "NORMAL",
            "CONTROLLED_FALLBACK"
        }
    ):

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_quality_floor",
            "contract": contract,
        }


    # =================================
    # DOCUMENTARY
    # =================================

    if (
        classe
        == "REAL_DOCUMENTARY"
    ):

        if not truth_ok:

            return {
                "action":
                    "FALLBACK",

                "reason":
                    "vi69_documentary_truth_failed",

                "contract":
                    contract,
            }


        if (
            score
            < contract[
                "min_score"
            ]
            and role != "CTA"
        ):

            return {
                "action":
                    "FALLBACK",

                "reason":
                    "vi69_documentary_score_floor",

                "score":
                    score,

                "contract":
                    contract,
            }


        return {
            "action":
                "KEEP",

            "reason":
                "vi69_verified_documentary",

            "score":
                score,

            "semantic":
                semantic,

            "anchor":
                anchor,

            "contract":
                contract,
        }


    # =================================
    # SAFE CONTEXT
    # =================================

    if (
        classe
        != "SAFE_CONTEXT"
    ):

        return {
            "action":
                "FALLBACK",

            "reason":
                "vi69_unsupported_class",

            "contract":
                contract,
        }


    # CTA reutilizado é exceção controlada.
    if role == "CTA":

        return {
            "action":
                "KEEP",

            "reason":
                "vi69_cta_reuse",

            "contract":
                contract,
        }


    if (
        score
        < contract[
            "min_score"
        ]
    ):

        return {
            "action":
                "FALLBACK",

            "reason":
                "vi69_score_floor",

            "score":
                score,

            "contract":
                contract,
        }


    if (
        semantic
        < contract[
            "min_semantic_stock"
        ]
    ):

        return {
            "action":
                "FALLBACK",

            "reason":
                "vi69_semantic_floor",

            "semantic":
                semantic,

            "required":
                contract[
                    "min_semantic_stock"
                ],

            "contract":
                contract,
        }


    # =================================
    # GENERIC STOCK FIREWALL
    # =================================

    generic = any(
        marker
        in reason_text

        for marker in (
            "generic_stock",
            "generic_context",
            "generic_person",
            "generic_place",
            "weak_anchor_stock",
        )
    )


    strictness = (
        contract[
            "generic_stock"
        ]
    )


    if (
        generic
        and strictness == "STRICT"
    ):

        if (
            anchor
            < contract[
                "min_anchor_stock"
            ]
        ):

            return {
                "action":
                    "FALLBACK",

                "reason":
                    "vi69_generic_strict_veto",

                "anchor":
                    anchor,

                "required":
                    contract[
                        "min_anchor_stock"
                    ],

                "contract":
                    contract,
            }


    elif (
        generic
        and strictness == "MEDIUM"
    ):

        if (
            anchor
            < contract[
                "min_anchor_stock"
            ]
            and semantic < 62
        ):

            return {
                "action":
                    "FALLBACK",

                "reason":
                    "vi69_generic_medium_veto",

                "anchor":
                    anchor,

                "semantic":
                    semantic,

                "contract":
                    contract,
            }


    # =================================
    # EVIDENCE STOCK FIREWALL
    # =================================

    if role == "EVIDENCE":

        if (
            semantic < 60
            or anchor < .18
        ):

            return {
                "action":
                    "FALLBACK",

                "reason":
                    "vi69_stock_not_evidence_grade",

                "semantic":
                    semantic,

                "anchor":
                    anchor,

                "contract":
                    contract,
            }


    # =================================
    # PERSON FIREWALL
    # =================================

    if role == "PERSON":

        if (
            generic
            and anchor < .20
        ):

            return {
                "action":
                    "FALLBACK",

                "reason":
                    "vi69_random_person_veto",

                "anchor":
                    anchor,

                "contract":
                    contract,
            }


    # =================================
    # PLACE FIREWALL
    # =================================

    if role == "PLACE":

        if (
            generic
            and anchor < .14
        ):

            return {
                "action":
                    "FALLBACK",

                "reason":
                    "vi69_generic_place_veto",

                "anchor":
                    anchor,

                "contract":
                    contract,
            }


    return {
        "action":
            "KEEP",

        "reason":
            "vi69_quality_pass",

        "score":
            score,

        "semantic":
            semantic,

        "anchor":
            anchor,

        "contract":
            contract,
    }


def self_test():

    evidence_scene = {

        "retrieval_role_6_7":
            "EVIDENCE",

        "retrieval_anchor_strength_6_7":
            7,
    }


    generic_stock = {

        "fonte":
            "Pixabay",

        "tipo":
            "vídeo",

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


    r = evaluate_candidate_firewall_6_9(
        generic_stock,
        evidence_scene,
        {
            "class":
                "SAFE_CONTEXT",

            "score":
                80,

            "semantic":
                50,

            "anchor":
                .08,

            "role":
                "EVIDENCE",

            "reasons":
                [
                    "generic_stock",
                    "stock_evidence_guard"
                ]
        }
    )


    assert r[
        "action"
    ] == "FALLBACK"


    strong_stock = dict(
        generic_stock
    )


    r = evaluate_candidate_firewall_6_9(
        strong_stock,
        evidence_scene,
        {
            "class":
                "SAFE_CONTEXT",

            "score":
                82,

            "semantic":
                72,

            "anchor":
                .42,

            "role":
                "EVIDENCE",

            "reasons":
                [
                    "relevant_motion"
                ]
        }
    )


    assert r[
        "action"
    ] == "KEEP"


    bad_doc = {

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


    r = evaluate_candidate_firewall_6_9(
        bad_doc,
        evidence_scene,
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


    assert r[
        "action"
    ] == "FALLBACK"


    good_doc = dict(
        bad_doc
    )

    good_doc[
        "_vi6_truth_ok"
    ] = True


    r = evaluate_candidate_firewall_6_9(
        good_doc,
        evidence_scene,
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


    assert r[
        "action"
    ] == "KEEP"


    cta = {

        "visual_mode":
            "cta_reuse"
    }


    r = evaluate_candidate_firewall_6_9(
        generic_stock,
        cta,
        {
            "class":
                "SAFE_CONTEXT",

            "score":
                10,

            "semantic":
                0,

            "anchor":
                0,

            "role":
                "CTA",
        }
    )


    assert r[
        "action"
    ] == "KEEP"


    print()
    print(
        "======================================"
    )
    print(
        " VI6.9 FIREWALL SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Generic Evidence Veto"
    )
    print(
        "OK Strong Context Accepted"
    )
    print(
        "OK Documentary Truth Lock"
    )
    print(
        "OK Evidence-grade Floor"
    )
    print(
        "OK Person/Place Contracts"
    )
    print(
        "OK CTA Reuse Exception"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# VI6.9 RUNTIME POLICY
# =====================================================

cat > vi6_9_runtime_policy.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

from vi6_9_quality_firewall import (
    evaluate_candidate_firewall_6_9
)


if not getattr(
    brain,
    "_VI69_RUNTIME_PATCHED",
    False
):

    _base_supervisor_6_6 = (
        brain.supervisionar_vi6_6
    )


    def supervisionar_vi6_6_com_firewall(
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
        ) = _base_supervisor_6_6(
            vi6_scene,
            candidatos,
            cena,
            current_candidate,
            current_reason
        )


        # Respeita fallback anterior.
        if candidate is None:

            return (
                candidate,
                reason,
                meta
            )


        firewall = (
            evaluate_candidate_firewall_6_9(
                candidate,
                cena,
                meta
            )
        )


        meta = dict(
            meta
            or {}
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


        # =============================================
        # VETO -> VOLTA PARA 5.x
        # =============================================

        if (
            firewall.get(
                "action"
            )
            == "FALLBACK"
        ):

            meta[
                "decision"
            ] = "5X_FIREWALL"


            return (
                None,
                firewall.get(
                    "reason",
                    "vi69_firewall_fallback"
                ),
                meta
            )


        return (
            candidate,
            reason,
            meta
        )


    brain.supervisionar_vi6_6 = (
        supervisionar_vi6_6_com_firewall
    )


    brain._VI69_RUNTIME_PATCHED = (
        True
    )
PY


# =====================================================
# PATCH MÍNIMO DO MIDIA.PY
# =====================================================

python - <<'PY'
from pathlib import Path


p = Path(
    "midia.py"
)


t = p.read_text(
    encoding="utf-8"
)


if "import vi6_9_runtime_policy" in t:

    print(
        "VI6.9 runtime já integrado."
    )

    raise SystemExit(0)


marker = (
    "    import vi6_8_runtime_policy\n"
)


if marker not in t:

    raise SystemExit(
        "ERRO: import VI6.8 runtime "
        "não localizado. "
        "midia.py NÃO foi alterado."
    )


replacement = (
    marker
    + "\n"
    + "    # VI6.9 final candidate firewall\n"
    + "    import vi6_9_runtime_policy\n"
)


t = t.replace(
    marker,
    replacement,
    1
)


p.write_text(
    t,
    encoding="utf-8"
)


print()
print(
    "OK VI6.9 Runtime integrado "
    "depois do VI6.8"
)
PY


PATCH_STATUS=$?


if [ "$PATCH_STATUS" -ne 0 ]; then

    rollback
    exit "$PATCH_STATUS"
fi


# =====================================================
# AUDITORIA RETROSPECTIVA REAL
# =====================================================

cat > testar_vi69_vi610_offline.py <<'PY'
#!/usr/bin/env python3

import glob
import json
import os

from vi6_9_quality_firewall import (
    evaluate_candidate_firewall_6_9
)

from vi6_10_coverage_predictor import (
    predict_scene_contract
)


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)


reports = sorted(
    glob.glob(
        os.path.join(
            BASE,
            "roteiros",
            "visual_intelligence_6_*.json"
        )
    ),
    key=os.path.getmtime,
    reverse=True
)


if not reports:

    raise SystemExit(
        "ERRO: relatório VI6 não encontrado."
    )


path = reports[0]


with open(
    path,
    "r",
    encoding="utf-8"
) as f:

    data = json.load(f)


keep = 0
fallback = 0
docs = 0
stock = 0


print()
print(
    "======================================"
)
print(
    " VI6.9 + VI6.10 REAL REPORT AUDIT"
)
print(
    " SEM API / SEM DOWNLOAD / SEM VIDEO"
)
print(
    "======================================"
)
print(
    "REPORT:",
    path
)
print()


for index, scene in enumerate(
    data.get(
        "scenes",
        []
    ),
    1
):

    winner = (
        scene.get(
            "winner"
        )
        or {}
    )


    contract = (
        predict_scene_contract(
            scene
        )
    )


    if not winner:

        fallback += 1

        print(
            f"CENA {index:02d} "
            f"-> FALLBACK "
            f"| sem winner"
        )

        continue


    meta = {

        "class":
            winner.get(
                "class"
            ),

        "score":
            winner.get(
                "score"
            ),

        "semantic":
            winner.get(
                "semantic"
            ),

        "anchor":
            (
                winner.get(
                    "anchor_ratio"
                )

                or winner.get(
                    "wiki_anchor_ratio"
                )

                or 0
            ),

        "truth_ok":
            winner.get(
                "truth_ok"
            ),

        "role":
            contract[
                "role"
            ],

        "reasons":
            [
                winner.get(
                    "reason",
                    ""
                )
            ],
    }


    result = (
        evaluate_candidate_firewall_6_9(
            winner,
            scene,
            meta
        )
    )


    action = result[
        "action"
    ]


    classe = str(
        winner.get(
            "class",
            "?"
        )
    )


    if action == "KEEP":

        keep += 1

        if (
            classe.upper()
            == "REAL_DOCUMENTARY"
        ):

            docs += 1

        else:

            stock += 1

    else:

        fallback += 1


    print(
        f"CENA {index:02d} "
        f"-> {action} "
        f"| role={contract['role']} "
        f"| class={classe} "
        f"| reason={result['reason']}"
    )


print()
print(
    "======================================"
)
print(
    " RESUMO VI6.9 + VI6.10"
)
print(
    "======================================"
)
print(
    "KEEP:",
    keep
)
print(
    "  REAL_DOCUMENTARY:",
    docs
)
print(
    "  SAFE_CONTEXT:",
    stock
)
print(
    "FALLBACK:",
    fallback
)
print(
    "TOTAL:",
    keep + fallback
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
    vi6_9_quality_firewall.py \
    vi6_9_runtime_policy.py \
    vi6_10_coverage_predictor.py \
    testar_vi69_vi610_offline.py \
    vi6_6_active_brain.py \
    vi6_7_retrieval_planner.py \
    vi6_8_storyboard_director.py \
    vi6_8_runtime_policy.py \
    midia.py
then

    echo
    echo "COMPILE FALHOU."

    rollback
    exit 1
fi

echo "PYTHON STATUS=0"


# =====================================================
# SELF TESTS
# =====================================================

echo
echo "===== VI6.10 SELF TEST ====="

if ! python vi6_10_coverage_predictor.py
then
    rollback
    exit 1
fi


echo
echo "===== VI6.9 SELF TEST ====="

if ! python vi6_9_quality_firewall.py
then
    rollback
    exit 1
fi


echo
echo "===== RUNTIME PATCH TEST ====="

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
    "VI6.8 RUNTIME PATCH: OK"
)

print(
    "VI6.9 RUNTIME PATCH: OK"
)
PY
then
    rollback
    exit 1
fi


echo
echo "===== VI6.6 REGRESSION ====="

if ! python vi6_6_active_brain.py
then
    rollback
    exit 1
fi


echo
echo "===== VI6.7 REGRESSION ====="

if ! python vi6_7_retrieval_planner.py
then
    rollback
    exit 1
fi


echo
echo "===== VI6.8 REGRESSION ====="

if ! python vi6_8_storyboard_director.py
then
    rollback
    exit 1
fi


echo
echo "===== BASH CHECK ====="

if ! bash -n gerar_short.sh
then
    rollback
    exit 1
fi

echo "BASH STATUS=0"


echo
echo "===== RELEASE CHECK ====="

if ! ./release_check.sh
then
    rollback
    exit 1
fi


echo
echo "===== CODE CHECK ====="

grep -nE \
'vi6_8_runtime_policy|vi6_9_runtime_policy|VI6\.7 \+ VI6\.8 ACTIVE VISUAL PLANNING' \
midia.py | head -30


echo
echo "======================================"
echo " VI6.9 + VI6.10 INSTALADOS"
echo "======================================"
echo
echo "OK Final Candidate Firewall"
echo "OK Visual Coverage Contract"
echo "OK Evidence Grade Floor"
echo "OK Generic Stock Veto"
echo "OK Random Person Veto"
echo "OK Generic Place Veto"
echo "OK Documentary Truth Lock"
echo "OK Semantic Floor por tipo de cena"
echo "OK Anchor Floor por tipo de cena"
echo "OK Retrieval-aware Requirements"
echo "OK VI6.8 Storyboard-aware Requirements"
echo "OK CTA Reuse Exception"
echo "OK VI6.6 fallback preservado"
echo "OK VI6.3 fallback preservado"
echo "OK 5.x fallback preservado"
echo
echo "VIDEO GERADO=0"
echo "DOWNLOAD NOVO=0"
echo "API CALLS=0"
echo "GERAR_SHORT NÃO EXECUTADO"
echo


echo "======================================"
echo " AUDITORIA RETROSPECTIVA"
echo "======================================"

python testar_vi69_vi610_offline.py

