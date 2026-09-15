#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p backups/stable_release_ready

BACKUP="backups/stable_release_ready/midia_pre_vi66_${STAMP}.py"

cp midia.py "$BACKUP" || exit 1

echo
echo "======================================"
echo " VI6.6 VISUAL EDITORIAL STACK"
echo " INSTALAÇÃO OFFLINE"
echo "======================================"
echo


# =====================================================
# 1. NOVO CÉREBRO EDITORIAL 6.6
# =====================================================

cat > vi6_6_editorial_stack.py <<'PY'
#!/usr/bin/env python3

import re
from collections import deque


# =====================================================
# VI6.6 VISUAL EDITORIAL STACK
# =====================================================
#
# Não busca.
# Não baixa.
# Não renderiza.
#
# Atua depois do VI6.4 e antes do download.
#
# Combina:
# - Truth protection
# - Numeric identity protection
# - Documentary rescue
# - Stock generic guard
# - Evidence guard
# - Person guard
# - Place guard
# - Anchor coverage
# - Source fatigue
# - Asset repetition
# - Motion relevance
# - Confidence margin
# - Storyboard diversity
# =====================================================


_RECENT = deque(maxlen=8)


STOP = {
    "the","and","for","with","from","into",
    "this","that","real","photo","image","video",
    "uma","um","de","da","do","das","dos",
    "com","para","por","em","no","na","nos","nas",
    "foto","imagem","vídeo","video",
    "man","woman","person","people",
    "family","child","girl","boy",
    "homem","mulher","pessoa","pessoas",
    "familia","família","criança","crianca",
    "menina","menino",
    "street","city","building","room",
    "forest","river","road",
    "rua","cidade","prédio","predio",
    "floresta","rio","estrada"
}


def s(v):
    return str(v or "").strip()


def u(v):
    return s(v).upper()


def f(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return float(default)


def tokens(text):
    return {
        x
        for x in re.findall(
            r"[a-zà-ÿ0-9]+",
            s(text).lower()
        )
        if len(x) >= 3 and x not in STOP
    }


def numbers(text):
    return set(
        re.findall(
            r"(?<!\d)\d{2,4}(?!\d)",
            s(text)
        )
    )


def flatten(v):

    if v is None:
        return ""

    if isinstance(v, dict):
        return " ".join(
            flatten(x)
            for x in v.values()
        )

    if isinstance(v, (list, tuple, set)):
        return " ".join(
            flatten(x)
            for x in v
        )

    return s(v)


def key(item):

    return (
        s(
            item.get("fonte")
            or item.get("source")
        ),
        s(item.get("id")),
        s(item.get("url"))
    )


def source(item):

    return s(
        item.get("fonte")
        or item.get("source")
    )


def media_type(item):

    return s(
        item.get("tipo")
        or item.get("type")
    ).lower()


def classe(item):

    return u(
        item.get("class")
        or item.get("_vi64_class")
    )


def quality(item):

    return u(
        item.get("quality_tier")
        or item.get("_vi64_quality")
    )


def risk(item):

    return u(
        item.get("risk")
    )


def truth(item):

    return bool(
        item.get(
            "truth_ok",
            item.get(
                "_vi64_truth_ok",
                False
            )
        )
    )


def semantic(item):

    return f(
        item.get(
            "semantic",
            item.get(
                "_vi64_semantic",
                0
            )
        )
    )


def provenance(item):

    return f(
        item.get(
            "provenance",
            item.get(
                "_vi64_provenance",
                0
            )
        )
    )


def base_score(item):

    return f(
        item.get(
            "score",
            item.get(
                "_vi64_policy_score",
                item.get(
                    "_vi64_original_score",
                    0
                )
            )
        )
    )


def reason(item):

    return s(
        item.get("reason")
        or item.get("_vi64_reason")
    )


def evidence(item):

    return u(
        item.get("evidence_class")
    )


def wiki_tier(item):

    return u(
        item.get("wiki_query_tier")
    )


def scene_blob(cena):

    return " ".join(
        flatten(
            cena.get(k)
        )
        for k in (
            "segmento",
            "segment",
            "texto",
            "text",
            "narracao",
            "narração",
            "visual_query",
            "query",
            "must_have",
            "must",
            "subject",
            "topic",
            "visual_mode",
            "visual_intent"
        )
    )


def candidate_blob(item):

    return " ".join(
        flatten(
            item.get(k)
        )
        for k in (
            "descricao",
            "description",
            "titulo",
            "title",
            "wiki_title",
            "commons_title",
            "wiki_query",
            "wiki_anchor_text",
            "filename",
            "name"
        )
    )


def anchors(cena):

    text = " ".join(
        flatten(
            cena.get(k)
        )
        for k in (
            "must_have",
            "must",
            "visual_query",
            "query",
            "subject",
            "topic"
        )
    )

    return tokens(text)


def anchor_ratio(
    cena,
    item
):

    a = anchors(cena)

    if not a:
        return 0.0

    b = tokens(
        candidate_blob(item)
    )

    return (
        len(a & b)
        /
        max(1, len(a))
    )


def role(
    cena,
    vi6_scene
):

    mode = s(
        cena.get("visual_mode")
    ).lower()

    intent = s(
        (vi6_scene or {}).get("intent")
        or cena.get("intent")
    ).lower()

    text = f"{mode} {intent}"


    if "cta" in text:
        return "CTA"


    if any(
        x in text
        for x in (
            "document",
            "evidence",
            "arquivo",
            "case_file",
            "newspaper"
        )
    ):
        return "EVIDENCE"


    if any(
        x in text
        for x in (
            "person",
            "portrait",
            "people",
            "character"
        )
    ):
        return "PERSON"


    if any(
        x in text
        for x in (
            "location",
            "architecture",
            "place",
            "map",
            "transport"
        )
    ):
        return "PLACE"


    if any(
        x in text
        for x in (
            "object",
            "medicine",
            "package",
            "packaging",
            "product"
        )
    ):
        return "OBJECT"


    return "CONTEXT"


def enrich_current(item):

    if not item:
        return None

    x = dict(item)

    x.setdefault(
        "class",
        item.get("_vi64_class")
    )

    x.setdefault(
        "quality_tier",
        item.get("_vi64_quality")
    )

    x.setdefault(
        "truth_ok",
        item.get("_vi64_truth_ok")
    )

    x.setdefault(
        "semantic",
        item.get("_vi64_semantic")
    )

    x.setdefault(
        "provenance",
        item.get("_vi64_provenance")
    )

    x.setdefault(
        "score",
        item.get(
            "_vi64_policy_score",
            item.get(
                "_vi64_original_score"
            )
        )
    )

    return x


def serialized_pool(
    vi6_scene,
    current
):

    raw = []

    if current:
        raw.append(
            enrich_current(current)
        )


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
        )[:10]
    )


    out = []
    seen = set()


    for item in raw:

        if not item:
            continue

        k = key(item)

        identity = (
            k
            if any(k)
            else (
                candidate_blob(item),
                classe(item),
                base_score(item)
            )
        )

        if identity in seen:
            continue

        seen.add(identity)
        out.append(item)


    return out


def find_original(
    item,
    candidatos,
    current
):

    k = key(item)


    if (
        current
        and any(k)
        and key(current) == k
    ):
        return current


    for c in candidatos or []:

        if (
            any(k)
            and key(c) == k
        ):
            return c


    src, ident, url = k


    if src and ident:

        matches = [
            c
            for c in candidatos or []
            if (
                source(c) == src
                and s(c.get("id")) == ident
            )
        ]

        if len(matches) == 1:
            return matches[0]


    return None


def repetition_penalty(item):

    if not _RECENT:
        return 0.0


    penalty = 0.0

    k = key(item)
    src = source(item)
    family = u(
        item.get("family")
    )


    if any(
        x["key"] == k
        for x in _RECENT
    ):
        penalty -= 80.0


    last2 = list(_RECENT)[-2:]
    last3 = list(_RECENT)[-3:]


    if (
        len(last2) == 2
        and all(
            x["source"] == src
            for x in last2
        )
    ):
        penalty -= 8.0


    if (
        len(last3) == 3
        and all(
            x["source"] == src
            for x in last3
        )
    ):
        penalty -= 8.0


    if (
        family
        and family != "OTHER"
        and len(last2) == 2
        and all(
            x["family"] == family
            for x in last2
        )
    ):
        penalty -= 12.0


    return penalty


def remember(
    item,
    result
):

    _RECENT.append(
        {
            "key": key(item),
            "source": source(item),
            "family": u(
                item.get("family")
            ),
            "class": result["class"]
        }
    )


def evaluate(
    item,
    cena,
    vi6_scene
):

    if not item:
        return None


    c = classe(item)
    q = quality(item)
    r = risk(item)
    t = truth(item)


    # =================================
    # HARD BLOCKS
    # =================================

    if bool(
        item.get("blocked", False)
    ):
        return None


    if r == "HIGH":
        return None


    if "MISLEADING" in c:
        return None


    if (
        q
        and q not in {
            "NORMAL",
            "CONTROLLED_FALLBACK"
        }
    ):
        return None


    if c not in {
        "REAL_DOCUMENTARY",
        "SAFE_CONTEXT"
    }:
        return None


    if (
        c == "REAL_DOCUMENTARY"
        and not t
    ):
        return None


    sem = semantic(item)
    prov = provenance(item)
    score = base_score(item)

    rol = role(
        cena,
        vi6_scene
    )

    ar = anchor_ratio(
        cena,
        item
    )


    scene_nums = numbers(
        scene_blob(cena)
    )

    item_nums = numbers(
        candidate_blob(item)
    )


    numeric_conflict = bool(
        scene_nums
        and item_nums
        and scene_nums.isdisjoint(
            item_nums
        )
    )


    reasons = []


    # =================================
    # DOCUMENTARY
    # =================================

    if c == "REAL_DOCUMENTARY":

        # Case-direct com número incompatível
        # é bloqueado.
        if (
            numeric_conflict
            and evidence(item) == "CASE_DIRECT"
        ):
            return None


        score += 20
        reasons.append(
            "verified_documentary"
        )


        ev = evidence(item)

        if ev == "CASE_DIRECT":
            score += 24
            reasons.append(
                "case_direct"
            )

        elif ev == "CONTEXTUAL":
            score += 10
            reasons.append(
                "contextual"
            )


        score += {
            "CASE": 18,
            "CASE_VISUAL": 14,
            "CONTEXT_COMBINED": 11,
            "CONTEXT": 6,
            "CONTEXT_VISUAL": 4
        }.get(
            wiki_tier(item),
            0
        )


        if prov >= 90:
            score += 12

        elif prov >= 75:
            score += 8

        elif prov >= 60:
            score += 4


        if anchors(cena):

            if ar >= .50:
                score += 15
                reasons.append(
                    "anchor_strong"
                )

            elif ar >= .20:
                score += 7
                reasons.append(
                    "anchor_ok"
                )

            else:
                score -= 24
                reasons.append(
                    "anchor_weak"
                )


        if rol in {
            "EVIDENCE",
            "PERSON",
            "PLACE"
        }:
            score += 10


    # =================================
    # SAFE CONTEXT / STOCK
    # =================================

    else:

        if sem < 42:
            return None


        rr = reason(item).lower()


        if numeric_conflict:
            score -= 18
            reasons.append(
                "numeric_context_penalty"
            )


        if anchors(cena):

            if ar >= .35:
                score += 6

            elif ar < .12:
                score -= 10
                reasons.append(
                    "weak_anchor_stock"
                )


        if "generic_context" in rr:
            score -= 10
            reasons.append(
                "generic_stock"
            )


        if rol == "EVIDENCE":

            score -= 28
            reasons.append(
                "stock_evidence_guard"
            )


        elif rol == "PERSON":

            if (
                len(anchors(cena)) >= 2
                and ar < .20
            ):
                score -= 22
                reasons.append(
                    "generic_person_guard"
                )


        elif rol == "PLACE":

            if (
                anchors(cena)
                and ar < .12
            ):
                score -= 14
                reasons.append(
                    "generic_place_guard"
                )


        # Movimento recebe bônus apenas
        # quando a relevância é boa.
        if (
            media_type(item)
            in {"video", "vídeo"}
            and sem >= 58
        ):
            score += 6
            reasons.append(
                "relevant_motion"
            )


    if q == "CONTROLLED_FALLBACK":
        score -= 7


    score += repetition_penalty(
        item
    )


    return {
        "item": item,
        "class": c,
        "quality": q,
        "truth_ok": t,
        "semantic": sem,
        "provenance": prov,
        "score": round(score, 3),
        "role": rol,
        "anchor_ratio": round(ar, 3),
        "numeric_conflict": numeric_conflict,
        "reasons": reasons
    }


def supervisionar_vi6_6(
    vi6_scene,
    candidatos,
    cena,
    current_candidate,
    current_reason,
    meta_6_4=None
):

    # Se 6.4 já caiu no safety floor,
    # 6.6 não força candidato novo.
    if current_candidate is None:

        return (
            None,
            current_reason,
            {
                "decision":
                    "KEEP_FALLBACK",
                "reason":
                    "lower_quality_floor"
            }
        )


    current_serial = enrich_current(
        current_candidate
    )


    current_eval = evaluate(
        current_serial,
        cena,
        vi6_scene
    )


    pool = serialized_pool(
        vi6_scene,
        current_candidate
    )


    evaluated = []


    for item in pool:

        result = evaluate(
            item,
            cena,
            vi6_scene
        )

        if not result:
            continue


        original = find_original(
            item,
            candidatos,
            current_candidate
        )

        if original is None:
            continue


        result["original"] = original

        evaluated.append(
            result
        )


    # Atual candidato reprovado no supervisor.
    if current_eval is None:

        return (
            None,
            "vi66_veto",
            {
                "decision": "5X",
                "reason":
                    "current_failed_editorial_guard"
            }
        )


    current_eval["original"] = (
        current_candidate
    )


    if not any(
        key(x["original"])
        == key(current_candidate)
        for x in evaluated
    ):
        evaluated.append(
            current_eval
        )


    evaluated.sort(
        key=lambda x: x["score"],
        reverse=True
    )


    if not evaluated:

        return (
            None,
            "vi66_no_safe_candidate",
            {
                "decision": "5X"
            }
        )


    best = evaluated[0]


    # =================================
    # DOCUMENTARY RESCUE
    # =================================
    #
    # Documental verdadeiro pode vencer
    # stock se estiver até 8 pontos atrás.
    # =================================

    docs = [
        x
        for x in evaluated
        if (
            x["class"]
            == "REAL_DOCUMENTARY"
            and x["truth_ok"]
        )
    ]


    if docs:

        doc = docs[0]

        if (
            best["class"]
            == "SAFE_CONTEXT"
            and doc["score"]
            >= best["score"] - 8
        ):
            best = doc


    # =================================
    # CONFIDENCE FLOOR
    # =================================

    if best["score"] < 52:

        return (
            None,
            "vi66_confidence_floor",
            {
                "decision": "5X",
                "score": best["score"]
            }
        )


    # =================================
    # ANTI-CHURN
    # =================================
    #
    # Não troca por melhora insignificante.
    # =================================

    if (
        key(best["original"])
        != key(current_candidate)
    ):

        if (
            best["score"]
            < current_eval["score"] + 6
        ):

            best = current_eval
            best["original"] = (
                current_candidate
            )


    # =================================
    # AMBIGUOUS GENERIC GUARD
    # =================================

    if (
        best["class"]
        == "SAFE_CONTEXT"
        and "generic_stock"
        in best["reasons"]
        and best["semantic"] < 52
    ):

        alternatives = [
            x
            for x in evaluated
            if (
                key(x["original"])
                != key(best["original"])
            )
        ]

        if alternatives:

            margin = (
                best["score"]
                - alternatives[0]["score"]
            )

            if margin < 4:

                return (
                    None,
                    "vi66_ambiguous_generic",
                    {
                        "decision": "5X",
                        "margin":
                            round(margin, 2)
                    }
                )


    chosen = best["original"]


    chosen["_vi66_active"] = True
    chosen["_vi66_score"] = best["score"]
    chosen["_vi66_class"] = best["class"]
    chosen["_vi66_role"] = best["role"]
    chosen["_vi66_anchor"] = (
        best["anchor_ratio"]
    )
    chosen["_vi66_truth"] = (
        best["truth_ok"]
    )
    chosen["_vi66_reason"] = (
        ",".join(best["reasons"])
        or "editorial_keep"
    )


    changed = (
        key(chosen)
        != key(current_candidate)
    )


    remember(
        chosen,
        best
    )


    if changed:

        final_reason = (
            "vi66_editorial_override"
        )

        decision = "OVERRIDE"

    elif (
        best["class"]
        == "REAL_DOCUMENTARY"
    ):

        final_reason = (
            "vi66_documentary_keep"
        )

        decision = "KEEP_DOCUMENTARY"

    else:

        final_reason = (
            "vi66_editorial_keep"
        )

        decision = "KEEP"


    return (
        chosen,
        final_reason,
        {
            "decision": decision,
            "score": best["score"],
            "class": best["class"],
            "role": best["role"],
            "semantic":
                best["semantic"],
            "provenance":
                best["provenance"],
            "anchor_ratio":
                best["anchor_ratio"],
            "truth_ok":
                best["truth_ok"],
            "reasons":
                best["reasons"]
        }
    )


def reset_state():
    _RECENT.clear()


# =====================================================
# SELF TEST
# =====================================================

def self_test():

    reset_state()


    scene = {
        "visual_mode": "evidence",
        "query":
            "Flight 19 disappearance 1945",
        "must_have":
            ["Flight 19", "1945"],
        "segmento":
            "Flight 19 disappeared in 1945."
    }


    doc = {
        "fonte": "Wikimedia",
        "tipo": "foto",
        "id": "doc",
        "url": "doc",
        "class":
            "REAL_DOCUMENTARY",
        "risk": "LOW",
        "quality_tier": "NORMAL",
        "truth_ok": True,
        "semantic": 70,
        "provenance": 95,
        "score": 70,
        "evidence_class":
            "CASE_DIRECT",
        "wiki_query_tier": "CASE",
        "title":
            "Flight 19 aircraft 1945 archive"
    }


    wrong = dict(doc)
    wrong["id"] = "wrong"
    wrong["url"] = "wrong"
    wrong["title"] = (
        "TAM Flight 3054 2007"
    )


    stock = {
        "fonte": "Pixabay",
        "tipo": "vídeo",
        "id": "stock",
        "url": "stock",
        "class": "SAFE_CONTEXT",
        "risk": "LOW",
        "quality_tier": "NORMAL",
        "truth_ok": True,
        "semantic": 63,
        "provenance": 15,
        "score": 85,
        "reason":
            "generic_context_without_identity_claim",
        "description":
            "aircraft flying over ocean"
    }


    a = evaluate(
        doc,
        scene,
        {"intent": "EVIDENCE"}
    )

    assert a is not None


    b = evaluate(
        wrong,
        scene,
        {"intent": "EVIDENCE"}
    )

    assert b is None


    c = evaluate(
        stock,
        scene,
        {"intent": "EVIDENCE"}
    )

    assert c is not None

    assert (
        "stock_evidence_guard"
        in c["reasons"]
    )


    high = dict(stock)
    high["risk"] = "HIGH"

    assert (
        evaluate(
            high,
            scene,
            {}
        )
        is None
    )


    misleading = dict(stock)
    misleading["class"] = (
        "MISLEADING_REENACTMENT"
    )

    assert (
        evaluate(
            misleading,
            scene,
            {}
        )
        is None
    )


    no_truth = dict(doc)
    no_truth["truth_ok"] = False

    assert (
        evaluate(
            no_truth,
            scene,
            {}
        )
        is None
    )


    weak = dict(stock)
    weak["semantic"] = 20

    assert (
        evaluate(
            weak,
            scene,
            {}
        )
        is None
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.6 SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Truth Lock"
    )
    print(
        "OK Numeric Identity Lock"
    )
    print(
        "OK Documentary Evidence"
    )
    print(
        "OK Generic Evidence Guard"
    )
    print(
        "OK HIGH Risk Block"
    )
    print(
        "OK Misleading Block"
    )
    print(
        "OK Semantic Floor"
    )
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 2. INTEGRAR DEPOIS DO VI6.4
# =====================================================

python - <<'PY'
from pathlib import Path

p = Path("midia.py")

t = p.read_text(
    encoding="utf-8"
)


if "supervisionar_vi6_6" in t:

    print(
        "VI6.6 já estava integrado."
    )

    raise SystemExit(0)


old = '''            (
                vi6_active_candidate,
                vi6_active_reason,
                vi64_meta
            ) = decidir_vi6_4(
                vi6_scene,
                todos,
                cena
            )
'''


if old not in t:

    raise SystemExit(
        "ERRO: chamada VI6.4 não encontrada. "
        "midia.py NÃO foi alterado."
    )


new = old + '''

            # =========================================
            # VI6.6 VISUAL EDITORIAL STACK
            # =========================================

            from vi6_6_editorial_stack import (
                supervisionar_vi6_6
            )

            (
                vi6_active_candidate,
                vi6_active_reason,
                vi66_meta
            ) = supervisionar_vi6_6(
                vi6_scene,
                todos,
                cena,
                vi6_active_candidate,
                vi6_active_reason,
                vi64_meta
            )

            print(
                "  VI6.6 EDITORIAL:"
            )

            print(
                f"    DECISION="
                f"{vi66_meta.get('decision', '?')}"
            )

            print(
                f"    REASON="
                f"{vi6_active_reason}"
            )

            if (
                vi66_meta.get("score")
                is not None
            ):

                print(
                    f"    SCORE="
                    f"{vi66_meta.get('score')}"
                )

            if vi66_meta.get("role"):

                print(
                    f"    ROLE="
                    f"{vi66_meta.get('role')}"
                )

            if (
                vi66_meta.get(
                    "anchor_ratio"
                )
                is not None
            ):

                print(
                    f"    ANCHOR="
                    f"{vi66_meta.get('anchor_ratio')}"
                )
'''


t = t.replace(
    old,
    new,
    1
)


p.write_text(
    t,
    encoding="utf-8"
)


print(
    "OK VI6.6 integrado ao midia.py"
)
PY


# =====================================================
# 3. OFFLINE AUDITOR
# =====================================================

cat > testar_vi6_6_offline.py <<'PY'
#!/usr/bin/env python3

import glob
import json
import os

from vi6_6_editorial_stack import (
    evaluate,
    reset_state
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
    encoding="utf-8"
) as f:

    data = json.load(f)


reset_state()


docs = 0
safe = 0
fallback = 0
total = 0


print()
print(
    "======================================"
)
print(
    " VI6.6 OFFLINE AUDIT"
)
print(
    " SEM DOWNLOAD / SEM VIDEO"
)
print(
    "======================================"
)
print(
    "REPORT:",
    path
)
print()


for scene in data.get(
    "scenes",
    []
):

    total += 1

    n = int(
        scene.get(
            "scene",
            total
        )
        or total
    )


    pool = []

    winner = (
        scene.get("winner")
        or {}
    )


    if winner:
        pool.append(winner)


    pool.extend(
        (
            scene.get("top")
            or []
        )[:10]
    )


    results = []


    for item in pool:

        r = evaluate(
            item,
            scene,
            scene
        )

        if r:
            results.append(r)


    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )


    if (
        not results
        or results[0]["score"] < 52
    ):

        fallback += 1

        print(
            f"CENA {n:02d} "
            f"-> 5X_FALLBACK"
        )

        continue


    best = results[0]


    if (
        best["class"]
        == "REAL_DOCUMENTARY"
    ):

        docs += 1

    else:
        safe += 1


    item = best["item"]


    print(
        f"CENA {n:02d} "
        f"-> {best['class']} "
        f"| {item.get('fonte', '?')} / "
        f"{item.get('tipo', '?')} "
        f"| role={best['role']} "
        f"| score={best['score']} "
        f"| anchor={best['anchor_ratio']}"
    )


print()
print(
    "======================================"
)
print(
    " RESUMO VI6.6"
)
print(
    "======================================"
)
print(
    "REAL_DOCUMENTARY:",
    docs
)
print(
    "SAFE_CONTEXT:",
    safe
)
print(
    "5X_FALLBACK:",
    fallback
)
print(
    "TOTAL:",
    total
)
print()
print(
    "DOWNLOADS NOVOS: 0"
)
print(
    "VIDEOS GERADOS: 0"
)
print()
PY


# =====================================================
# 4. VALIDAÇÕES
# =====================================================

echo
echo "===== COMPILE ====="

if ! python -m py_compile \
    vi6_6_editorial_stack.py \
    testar_vi6_6_offline.py \
    vi6_4_policy.py \
    visual_intelligence_6.py \
    midia.py
then

    echo
    echo "ERRO DE COMPILE."
    echo "ROLLBACK."

    cp "$BACKUP" midia.py
    rm -f vi6_6_editorial_stack.py
    rm -f testar_vi6_6_offline.py

    exit 1
fi

echo "PYTHON STATUS=0"


echo
echo "===== SELF TEST ====="

if ! python vi6_6_editorial_stack.py
then

    echo
    echo "SELF TEST FALHOU."
    echo "ROLLBACK."

    cp "$BACKUP" midia.py
    rm -f vi6_6_editorial_stack.py
    rm -f testar_vi6_6_offline.py

    exit 1
fi


echo
echo "===== BASH CHECK ====="

if ! bash -n gerar_short.sh
then

    echo
    echo "BASH CHECK FALHOU."
    echo "ROLLBACK."

    cp "$BACKUP" midia.py
    rm -f vi6_6_editorial_stack.py
    rm -f testar_vi6_6_offline.py

    exit 1
fi

echo "BASH STATUS=0"


echo
echo "===== RELEASE CHECK ====="

if ! ./release_check.sh
then

    echo
    echo "RELEASE CHECK FALHOU."
    echo "ROLLBACK."

    cp "$BACKUP" midia.py
    rm -f vi6_6_editorial_stack.py
    rm -f testar_vi6_6_offline.py

    exit 1
fi


echo
echo "======================================"
echo " VI6.6 INSTALADO"
echo "======================================"
echo
echo "OK VI6.5 Editorial Supervisor incorporado"
echo "OK Documentary Rescue"
echo "OK Truth Lock"
echo "OK Numeric Identity Lock"
echo "OK Evidence Stock Guard"
echo "OK Generic Person Guard"
echo "OK Generic Place Guard"
echo "OK Semantic Floor"
echo "OK Anchor Coverage"
echo "OK Motion Relevance"
echo "OK Duplicate Asset Guard"
echo "OK Source Fatigue"
echo "OK Visual Family Fatigue"
echo "OK Confidence Floor"
echo "OK Anti-Churn"
echo "OK Ambiguous Stock Guard"
echo "OK VI6.4 preservado"
echo "OK VI6.3 preservado"
echo "OK 5.x preservado"
echo
echo "VIDEOS GERADOS=0"
echo "DOWNLOADS NOVOS=0"
echo


echo "======================================"
echo " AUDITORIA OFFLINE"
echo "======================================"

python testar_vi6_6_offline.py

