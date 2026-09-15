#!/data/data/com.termux/files/usr/bin/bash

set -u

BASE="$HOME/ShortAutoPro"

cd "$BASE" || exit 1

echo
echo "======================================"
echo " SHORTAUTOPRO 6.2 - MASTER VALIDATION"
echo "======================================"
echo


# =====================================================
# 1. SYNTAX
# =====================================================

echo "--------------------------------------"
echo "1/7 - PYTHON / BASH"
echo "--------------------------------------"

python -m py_compile \
source_identity.py \
post_script_truth_lock.py \
visual_intelligence_6.py \
topic_engine.py \
topic_reserve.py \
roteiro.py \
semantic_integrity_gate.py \
production_supervisor.py \
midia.py

if [ "$?" -ne 0 ]; then
    echo "ERRO: Python compile."
    exit 1
fi

bash -n gerar_short.sh

if [ "$?" -ne 0 ]; then
    echo "ERRO: gerar_short.sh inválido."
    exit 1
fi

echo "SYNTAX: PASS"


# =====================================================
# 2. TRUTH IDENTITY
# =====================================================

echo
echo "--------------------------------------"
echo "2/7 - TRUTH IDENTITY LOCK 6.2"
echo "--------------------------------------"

python - <<'PY'
from source_identity import validar_identidade

tests = [
    (
        "O Incidente do Voo 19",
        "Voo TAM 3054",
        False
    ),
    (
        "O Incidente do Voo 19",
        "Flight 19",
        True
    ),
    (
        "Voo TAM 3054",
        "TAM Flight 3054",
        True
    ),
    (
        "MH370",
        "Malaysia Airlines Flight 370",
        True
    ),
    (
        "MH370",
        "Malaysia Airlines Flight 17",
        False
    ),
    (
        "Caso Boy in the Box",
        "Joseph Augustus Zarelli",
        True
    ),
    (
        "Caso Boy in the Box",
        "The Boy in the Striped Pyjamas",
        False
    )
]

fails = []

for topic, source, expected in tests:

    r = validar_identidade(
        topic,
        source,
        ""
    )

    got = bool(
        r.get("valid")
    )

    status = (
        "PASS"
        if got == expected
        else "FAIL"
    )

    print(
        f"{status}: "
        f"{topic} -> {source} "
        f"valid={got} "
        f"reason={r.get('reason')}"
    )

    if got != expected:
        fails.append(
            (topic, source)
        )


if fails:
    raise SystemExit(
        f"TRUTH IDENTITY FAIL: {fails}"
    )


print()
print(
    "TRUTH IDENTITY LOCK 6.2: PASS"
)
PY

if [ "$?" -ne 0 ]; then
    exit 1
fi


# =====================================================
# 3. HISTORICAL CONTAMINATION
# =====================================================

echo
echo "--------------------------------------"
echo "3/7 - HISTORICAL BUG 1426"
echo "--------------------------------------"

SHORT_ID="2026-08-31_1426" \
python post_script_truth_lock.py >/tmp/truth_1426.log 2>&1

CODE=$?

cat /tmp/truth_1426.log | tail -35

if [ "$CODE" -eq 0 ]; then

    echo
    echo "ERRO:"
    echo "Produção contaminada 1426 foi aceita."
    exit 1

fi

echo
echo "HISTORICAL BUG 1426: BLOQUEADO CORRETAMENTE"


# =====================================================
# 4. VISUAL TRUTH CORE
# =====================================================

echo
echo "--------------------------------------"
echo "4/7 - VISUAL INTELLIGENCE 6.2 CORE"
echo "--------------------------------------"

python - <<'PY'
import visual_intelligence_6 as vi


generic = vi.documentary_truth_anchor_6_2(
    {
        "fonte":
            "Wikimedia",

        "evidence_class":
            "CONTEXTUAL",

        "wiki_query_tier":
            "CONTEXT",

        "wiki_anchor_ratio":
            1.0,

        "topic_overlap":
            0.0,

        "segment_overlap":
            0.25
    }
)


combined = vi.documentary_truth_anchor_6_2(
    {
        "fonte":
            "Wikimedia",

        "evidence_class":
            "CONTEXTUAL",

        "wiki_query_tier":
            "CONTEXT_COMBINED",

        "wiki_anchor_ratio":
            1.0,

        "topic_overlap":
            0.0,

        "segment_overlap":
            0.25
    }
)


direct = vi.documentary_truth_anchor_6_2(
    {
        "fonte":
            "Wikimedia",

        "evidence_class":
            "CASE_DIRECT",

        "wiki_query_tier":
            "CASE",

        "wiki_anchor_ratio":
            1.0,

        "topic_overlap":
            1.0
    }
)


print(
    "CONTEXT:",
    generic
)

print(
    "CONTEXT_COMBINED:",
    combined
)

print(
    "CASE_DIRECT:",
    direct
)


assert not generic["truth_ok"]
assert not generic["documentary"]

assert combined["truth_ok"]
assert combined["documentary"]

assert direct["truth_ok"]
assert direct["documentary"]


print()
print(
    "DOCUMENTARY TRUTH ANCHOR: PASS"
)


print()
print("MOTION BALANCE:")

for total in range(
    0,
    9
):

    video = (
        vi.motion_balance_6_2(
            {
                "tipo":
                    "vídeo"
            },
            total
        )
    )

    foto = (
        vi.motion_balance_6_2(
            {
                "tipo":
                    "foto"
            },
            total
        )
    )

    print(
        f"{total} vídeos -> "
        f"video={video['adjustment']:+.0f} "
        f"foto={foto['adjustment']:+.0f}"
    )


assert (
    vi.motion_balance_6_2(
        {"tipo": "vídeo"},
        2
    )["adjustment"]
    > 0
)

assert (
    vi.motion_balance_6_2(
        {"tipo": "vídeo"},
        7
    )["adjustment"]
    < 0
)


print()
print(
    "MOTION BALANCE: PASS"
)
PY

if [ "$?" -ne 0 ]; then
    exit 1
fi


# =====================================================
# 5. RELEASE CHECK
# =====================================================

echo
echo "--------------------------------------"
echo "5/7 - RELEASE CHECK"
echo "--------------------------------------"

"$BASE/release_check.sh"

if [ "$?" -ne 0 ]; then

    echo
    echo "ERRO: Release Check."
    exit 1

fi


# =====================================================
# 6. GERAÇÃO SHADOW
# =====================================================

echo
echo "--------------------------------------"
echo "6/7 - VI6.2 SHADOW PRODUCTION"
echo "--------------------------------------"

export VISUAL_INTELLIGENCE_6_SHADOW=1

"$BASE/gerar_short.sh"

CODE=$?

if [ "$CODE" -ne 0 ]; then

    echo
    echo "======================================"
    echo " PRODUÇÃO BLOQUEADA"
    echo "======================================"
    echo
    echo "Código: $CODE"
    echo
    echo "Isso NÃO ativa o VI6."
    echo "Algum gate impediu a produção."

    exit "$CODE"
fi


# =====================================================
# 7. RESULTADO VI6.2
# =====================================================

echo
echo "--------------------------------------"
echo "7/7 - VI6.2 RESULT"
echo "--------------------------------------"

REPORT="$(
ls -t \
"$BASE"/roteiros/visual_intelligence_6_*.json \
2>/dev/null |
head -1
)"

if [ -z "${REPORT:-}" ]; then

    echo "ERRO: relatório VI6 ausente."
    exit 1

fi


python - "$REPORT" <<'PY'
import json
import sys

p = sys.argv[1]

with open(
    p,
    encoding="utf-8"
) as f:

    d = json.load(f)


s = d.get(
    "summary",
    {}
)


print()
print("======================================")
print(" VISUAL INTELLIGENCE 6.2 - FINAL")
print("======================================")
print()

campos = [
    (
        "VI version",
        "vi_version"
    ),
    (
        "Storyboard",
        "storyboard_score"
    ),
    (
        "Documentary real",
        "real_documentary"
    ),
    (
        "Safe context",
        "safe_context"
    ),
    (
        "Illustrative",
        "illustrative"
    ),
    (
        "Misleading",
        "misleading"
    ),
    (
        "Quality normal",
        "quality_normal"
    ),
    (
        "Controlled fallback",
        "quality_controlled"
    ),
    (
        "Fallback to 5.x",
        "fallback_to_5x"
    ),
    (
        "Truth anchor failures",
        "truth_anchor_failures"
    ),
    (
        "Videos 6.2",
        "videos_6_2"
    ),
    (
        "Photos 6.2",
        "photos_6_2"
    ),
    (
        "Motion target OK",
        "motion_target_ok"
    ),
    (
        "CTA reused",
        "cta_reuse"
    )
]


for nome, chave in campos:

    print(
        f"{nome}:",
        s.get(
            chave
        )
    )


print()
print("======================================")
print(" 12 DECISÕES VI6.2")
print("======================================")


for cena in d.get(
    "scenes",
    []
):

    w = (
        cena.get(
            "winner"
        )
        or {}
    )


    print()

    print(
        f"CENA "
        f"{cena.get('scene', 0):02d}"
        f"/12 | "
        f"{cena.get('intent', '?')}"
    )


    if cena.get(
        "fallback_to_5x"
    ):

        print(
            "  DECISION: FALLBACK_TO_5X"
        )

    else:

        print(
            "  DECISION:",
            cena.get(
                "decision",
                w.get(
                    "quality_tier"
                )
            )
        )


    if not w:

        print(
            "  WINNER VI6: NONE"
        )

        continue


    print(
        f"  WINNER: "
        f"{w.get('fonte')} / "
        f"{w.get('tipo')}"
    )


    print(
        f"  CLASS={w.get('class')} "
        f"RISK={w.get('risk')} "
        f"SCORE={w.get('score')}"
    )


    print(
        f"  QUALITY="
        f"{w.get('quality_tier')} "
        f"TRUTH="
        f"{w.get('truth_ok')}"
    )


    truth = (
        w.get(
            "truth_anchor"
        )
        or {}
    )


    if truth:

        print(
            "  TRUTH REASON:",
            truth.get(
                "reason"
            )
        )


    mb = (
        w.get(
            "motion_balance"
        )
        or {}
    )


    if mb:

        print(
            f"  MOTION BALANCE: "
            f"{mb.get('adjustment')} "
            f"({mb.get('reason')})"
        )


    print(
        f"  FAMILY="
        f"{w.get('family')} "
        f"TIER="
        f"{w.get('wiki_query_tier')} "
        f"EVIDENCE="
        f"{w.get('evidence_class')}"
    )


    print(
        "  VISUAL:",
        str(
            w.get(
                "descricao",
                ""
            )
        )[:190]
    )


    if w.get(
        "reuse"
    ):

        print(
            "  CTA REUSE: YES"
        )


print()
print(
    "RELATORIO:",
    p
)
PY

echo
echo "======================================"
echo " MASTER VALIDATION 6.2 FINALIZADA"
echo "======================================"
