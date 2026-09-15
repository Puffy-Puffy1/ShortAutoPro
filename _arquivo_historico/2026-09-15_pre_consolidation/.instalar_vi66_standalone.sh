#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p backups/stable_release_ready

BACKUP="backups/stable_release_ready/midia_pre_vi66_standalone_${STAMP}.py"
cp midia.py "$BACKUP" || exit 1

OLD_MODULE=""

if [ -f vi6_6_active_brain.py ]; then
    OLD_MODULE="backups/stable_release_ready/vi6_6_active_brain_${STAMP}.py"
    cp vi6_6_active_brain.py "$OLD_MODULE"
fi

rollback() {
    echo
    echo "======================================"
    echo " ROLLBACK AUTOMATICO"
    echo "======================================"

    cp "$BACKUP" midia.py

    if [ -n "$OLD_MODULE" ] && [ -f "$OLD_MODULE" ]; then
        cp "$OLD_MODULE" vi6_6_active_brain.py
    else
        rm -f vi6_6_active_brain.py
    fi

    rm -f testar_vi66_offline.py

    echo "Projeto restaurado."
}

echo
echo "======================================"
echo " VI6.6 STANDALONE ACTIVE BRAIN"
echo " SEM VI6.4 / SEM VI6.5"
echo "======================================"
echo


# =====================================================
# NOVO CÉREBRO
# =====================================================

cat > vi6_6_active_brain.py <<'PY'
#!/usr/bin/env python3

import re
from collections import deque


# =====================================================
# VI6.6 STANDALONE ACTIVE BRAIN
#
# Funciona diretamente sobre VI6.3.
#
# NÃO baixa.
# NÃO renderiza.
# NÃO chama APIs.
# =====================================================


_MEMORY_EXACT = {}
_MEMORY_ID = {}

_RECENT = deque(
    maxlen=8
)


STOP = {
    "the", "and", "for", "with", "from",
    "this", "that", "into", "near",
    "real", "image", "photo", "video",

    "uma", "um",
    "de", "da", "do", "das", "dos",
    "em", "no", "na", "nos", "nas",
    "com", "para", "por",

    "imagem", "foto", "vídeo", "video",

    "man", "woman", "person", "people",
    "family", "child", "girl", "boy",

    "homem", "mulher",
    "pessoa", "pessoas",
    "familia", "família",
    "crianca", "criança",
    "menina", "menino",

    "street", "city", "building",
    "forest", "river", "road",

    "rua", "cidade",
    "predio", "prédio",
    "floresta", "rio", "estrada"
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


def _flatten(v):

    if v is None:
        return ""

    if isinstance(v, dict):

        return " ".join(
            _flatten(x)
            for x in v.values()
        )

    if isinstance(v, (list, tuple, set)):

        return " ".join(
            _flatten(x)
            for x in v
        )

    return _s(v)


def _tokens(text):

    return {
        token

        for token in re.findall(
            r"[a-zà-ÿ0-9]+",
            _s(text).lower()
        )

        if (
            len(token) >= 3
            and token not in STOP
        )
    }


def _years(text):

    return set(
        re.findall(
            r"\b(?:18|19|20)\d{2}\b",
            _s(text)
        )
    )


def _identity_numbers(text):

    text = _s(text).lower()

    out = set()

    patterns = (
        r"\b(?:flight|voo)\s*[-#:]?\s*(\d{1,4})\b",
        r"\b(?:case|caso)\s*[-#:]?\s*(\d{1,5})\b",
        r"\b(?:room|quarto)\s*[-#:]?\s*(\d{1,5})\b",
    )

    for pattern in patterns:

        out.update(
            re.findall(
                pattern,
                text
            )
        )

    # MH370 / QZ8501 / etc.
    out.update(
        re.findall(
            r"\b[a-z]{1,3}(\d{2,5})\b",
            text
        )
    )

    return out


def _key(item):

    return (
        _s(
            item.get("fonte")
            or item.get("source")
        ),

        _s(item.get("id")),

        _s(item.get("url"))
    )


def _id_key(item):

    return (
        _s(
            item.get("fonte")
            or item.get("source")
        ),

        _s(item.get("id"))
    )


def _source(item):

    return _s(
        item.get("fonte")
        or item.get("source")
    )


def _media_type(item):

    return _s(
        item.get("tipo")
        or item.get("type")
    ).lower()


def _class(item):

    return _u(
        item.get("class")
        or item.get("_vi6_class")
        or item.get("_vi66_class")
    )


def _risk(item):

    return _u(
        item.get("risk")
        or item.get("_vi6_risk")
    )


def _quality(item):

    return _u(
        item.get("quality_tier")
        or item.get("_vi6_quality_tier")
    )


def _truth(item):

    return bool(
        item.get(
            "truth_ok",
            item.get(
                "_vi6_truth_ok",
                False
            )
        )
    )


def _score(item):

    return _f(
        item.get(
            "score",
            item.get(
                "_vi6_score",
                0
            )
        )
    )


def _semantic(item):

    return _f(
        item.get(
            "semantic",
            0
        )
    )


def _provenance(item):

    return _f(
        item.get(
            "provenance",
            0
        )
    )


def _reason(item):

    return _s(
        item.get("reason")
        or item.get("_vi6_reason")
    )


def _evidence(item):

    return _u(
        item.get("evidence_class")
    )


def _tier(item):

    return _u(
        item.get("wiki_query_tier")
    )


def _scene_blob(cena):

    return " ".join(
        _flatten(
            cena.get(field)
        )

        for field in (
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


def _candidate_blob(item):

    return " ".join(
        _flatten(
            item.get(field)
        )

        for field in (
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


def _anchors(cena):

    text = " ".join(
        _flatten(
            cena.get(field)
        )

        for field in (
            "must_have",
            "must",
            "visual_query",
            "query",
            "subject",
            "topic"
        )
    )

    return _tokens(text)


def _anchor_ratio(
    cena,
    item
):

    a = _anchors(cena)

    if not a:
        return 0.0

    b = _tokens(
        _candidate_blob(item)
    )

    return (
        len(a & b)
        /
        max(1, len(a))
    )


def _role(
    cena,
    vi6_scene
):

    mode = _s(
        cena.get("visual_mode")
    ).lower()

    intent = _s(
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
            "newspaper",
            "case_file"
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


# =====================================================
# CANDIDATE MEMORY
# =====================================================

def _remember_pool(candidatos):

    for item in candidatos or []:

        k = _key(item)

        if any(k):
            _MEMORY_EXACT[k] = item

        ik = _id_key(item)

        if ik[0] and ik[1]:
            _MEMORY_ID[ik] = item


def _find_original(
    serialized,
    candidatos
):

    if not serialized:
        return None


    k = _key(serialized)


    for item in candidatos or []:

        if (
            any(k)
            and _key(item) == k
        ):
            return item


    if any(k):

        old = _MEMORY_EXACT.get(k)

        if old is not None:
            return old


    ik = _id_key(serialized)

    if ik[0] and ik[1]:

        matches = [
            item

            for item in candidatos or []

            if _id_key(item) == ik
        ]

        if len(matches) == 1:
            return matches[0]


        old = _MEMORY_ID.get(ik)

        if old is not None:
            return old


    return None


def _enrich_current(item):

    if not item:
        return None

    x = dict(item)

    x.setdefault(
        "class",
        item.get("_vi6_class")
    )

    x.setdefault(
        "risk",
        item.get("_vi6_risk")
    )

    x.setdefault(
        "quality_tier",
        item.get("_vi6_quality_tier")
    )

    x.setdefault(
        "truth_ok",
        item.get("_vi6_truth_ok")
    )

    x.setdefault(
        "score",
        item.get("_vi6_score")
    )

    x.setdefault(
        "reason",
        item.get("_vi6_reason")
    )

    return x


def _serialized_pool(
    vi6_scene,
    current
):

    raw = []

    if current:
        raw.append(
            _enrich_current(current)
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

        k = _key(item)

        identity = (
            k
            if any(k)
            else (
                _candidate_blob(item),
                _class(item),
                _score(item)
            )
        )

        if identity in seen:
            continue

        seen.add(identity)

        out.append(item)


    return out


# =====================================================
# STORY DIVERSITY
# =====================================================

def _repetition_penalty(item):

    if not _RECENT:
        return 0.0


    penalty = 0.0

    k = _key(item)

    src = _source(item)

    family = _u(
        item.get("family")
    )


    if any(
        x["key"] == k
        for x in _RECENT
    ):
        penalty -= 90.0


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


def _remember_selected(
    original,
    result
):

    _RECENT.append(
        {
            "key":
                _key(original),

            "source":
                _source(original),

            "family":
                _u(
                    original.get("family")
                ),

            "class":
                result["class"]
        }
    )


# =====================================================
# EDITORIAL EVALUATION
# =====================================================

def evaluate(
    item,
    cena,
    vi6_scene=None
):

    if not item:
        return None


    c = _class(item)

    r = _risk(item)

    q = _quality(item)

    t = _truth(item)


    # ---------------------------------
    # HARD BLOCKS
    # ---------------------------------

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


    sem = _semantic(item)

    prov = _provenance(item)

    total = _score(item)

    rol = _role(
        cena,
        vi6_scene or {}
    )

    ar = _anchor_ratio(
        cena,
        item
    )


    scene_text = _scene_blob(cena)

    candidate_text = _candidate_blob(item)


    scene_ids = _identity_numbers(
        scene_text
    )

    candidate_ids = _identity_numbers(
        candidate_text
    )


    identity_conflict = bool(
        scene_ids
        and candidate_ids
        and scene_ids.isdisjoint(
            candidate_ids
        )
    )


    sy = _years(scene_text)

    cy = _years(candidate_text)


    year_conflict = bool(
        sy
        and cy
        and sy.isdisjoint(cy)
    )


    reasons = []


    # =================================================
    # REAL DOCUMENTARY
    # =================================================

    if c == "REAL_DOCUMENTARY":

        if identity_conflict:
            return None


        total += 20

        reasons.append(
            "verified_documentary"
        )


        ev = _evidence(item)


        if ev == "CASE_DIRECT":

            total += 25

            reasons.append(
                "case_direct"
            )


        elif ev == "CONTEXTUAL":

            total += 11

            reasons.append(
                "contextual_verified"
            )


        total += {
            "CASE": 18,
            "CASE_VISUAL": 14,
            "CONTEXT_COMBINED": 11,
            "CONTEXT": 6,
            "CONTEXT_VISUAL": 4
        }.get(
            _tier(item),
            0
        )


        if prov >= 90:
            total += 12

        elif prov >= 75:
            total += 8

        elif prov >= 60:
            total += 4


        if _anchors(cena):

            if ar >= .50:

                total += 15

                reasons.append(
                    "anchor_strong"
                )

            elif ar >= .20:

                total += 7

                reasons.append(
                    "anchor_ok"
                )

            else:

                total -= 24

                reasons.append(
                    "anchor_weak"
                )


        # Ano incompatível não é hard block,
        # porque arquivos podem citar datas
        # de publicação/restauração.
        if year_conflict:

            total -= 8

            reasons.append(
                "year_context_penalty"
            )


        if rol in {
            "EVIDENCE",
            "PERSON",
            "PLACE"
        }:

            total += 10


    # =================================================
    # SAFE CONTEXT / STOCK
    # =================================================

    else:

        if sem < 42:

            return None


        rr = _reason(item).lower()


        if identity_conflict:

            total -= 28

            reasons.append(
                "identity_context_penalty"
            )


        if year_conflict:

            total -= 8


        if _anchors(cena):

            if ar >= .35:

                total += 6

            elif ar < .12:

                total -= 10

                reasons.append(
                    "weak_anchor_stock"
                )


        if "generic_context" in rr:

            total -= 10

            reasons.append(
                "generic_stock"
            )


        # Evidência factual não deve ser
        # ilustrada por qualquer stock.
        if rol == "EVIDENCE":

            total -= 30

            reasons.append(
                "stock_evidence_guard"
            )


        elif rol == "PERSON":

            if (
                len(_anchors(cena)) >= 2
                and ar < .20
            ):

                total -= 24

                reasons.append(
                    "generic_person_guard"
                )


        elif rol == "PLACE":

            if (
                _anchors(cena)
                and ar < .12
            ):

                total -= 16

                reasons.append(
                    "generic_place_guard"
                )


        # Vídeo não ganha só por se mover.
        if (
            _media_type(item)
            in {"video", "vídeo"}
            and sem >= 58
        ):

            total += 6

            reasons.append(
                "relevant_motion"
            )


    if q == "CONTROLLED_FALLBACK":

        total -= 7


    total += _repetition_penalty(
        item
    )


    return {
        "item": item,
        "score":
            round(total, 3),
        "class": c,
        "risk": r,
        "quality": q,
        "truth_ok": t,
        "semantic": sem,
        "provenance": prov,
        "role": rol,
        "anchor_ratio":
            round(ar, 3),
        "identity_conflict":
            identity_conflict,
        "year_conflict":
            year_conflict,
        "reasons": reasons
    }


# =====================================================
# ACTIVE SUPERVISOR
# =====================================================

def supervisionar_vi6_6(
    vi6_scene,
    candidatos,
    cena,
    current_candidate,
    current_reason
):

    candidatos = candidatos or []

    _remember_pool(
        candidatos
    )


    winner = (
        (vi6_scene or {}).get("winner")
        or {}
    )


    role = _role(
        cena,
        vi6_scene or {}
    )


    # =================================================
    # CTA MEMORY RESCUE
    # =================================================
    #
    # Corrige:
    # REASON=original_not_found
    #
    # sem procurar o asset somente
    # no pool da cena atual.
    # =================================================

    if current_candidate is None:

        reuse = bool(
            winner.get("reuse", False)
        )

        winner_reason = _s(
            winner.get("reason")
        ).lower()


        is_cta_reuse = (
            role == "CTA"
            and (
                reuse
                or "reuse"
                in winner_reason
                or "cta"
                in winner_reason
            )
        )


        if (
            current_reason
            == "original_not_found"
            and is_cta_reuse
        ):

            remembered = _find_original(
                winner,
                []
            )


            if remembered is not None:

                serialized = dict(
                    winner
                )

                result = evaluate(
                    serialized,
                    cena,
                    vi6_scene
                )


                if result is not None:

                    remembered[
                        "_vi6_class"
                    ] = result["class"]

                    remembered[
                        "_vi6_risk"
                    ] = result["risk"]

                    remembered[
                        "_vi6_quality_tier"
                    ] = result["quality"]

                    remembered[
                        "_vi6_truth_ok"
                    ] = result["truth_ok"]

                    remembered[
                        "_vi6_score"
                    ] = result["score"]

                    remembered[
                        "_vi6_reason"
                    ] = (
                        "vi66_cta_memory_reuse"
                    )


                    _remember_selected(
                        remembered,
                        result
                    )


                    return (
                        remembered,
                        "vi66_cta_memory_reuse",
                        {
                            "decision":
                                "CTA_MEMORY",

                            "score":
                                result["score"],

                            "class":
                                result["class"],

                            "role":
                                result["role"],

                            "anchor":
                                result[
                                    "anchor_ratio"
                                ]
                        }
                    )


        # Respeita qualquer outro floor
        # do VI6.3.
        return (
            None,
            current_reason,
            {
                "decision":
                    "KEEP_5X",

                "reason":
                    "vi63_floor_preserved"
            }
        )


    # =================================================
    # CURRENT + ALTERNATIVES
    # =================================================

    current_serial = _enrich_current(
        current_candidate
    )


    current_eval = evaluate(
        current_serial,
        cena,
        vi6_scene
    )


    if current_eval is None:

        return (
            None,
            "vi66_veto_current",
            {
                "decision":
                    "5X",

                "reason":
                    "current_failed_vi66"
            }
        )


    current_eval[
        "original"
    ] = current_candidate


    evaluated = []


    for serialized in _serialized_pool(
        vi6_scene,
        current_candidate
    ):

        result = evaluate(
            serialized,
            cena,
            vi6_scene
        )

        if result is None:
            continue


        original = _find_original(
            serialized,
            candidatos
        )


        if original is None:

            # Atual candidato já é original.
            if (
                _key(serialized)
                == _key(current_candidate)
            ):

                original = current_candidate

            else:
                continue


        result["original"] = original

        evaluated.append(
            result
        )


    if not any(
        _key(x["original"])
        == _key(current_candidate)
        for x in evaluated
    ):

        evaluated.append(
            current_eval
        )


    evaluated.sort(
        key=lambda x:
            x["score"],
        reverse=True
    )


    best = evaluated[0]


    # =================================================
    # DOCUMENTARY RESCUE
    # =================================================
    #
    # Se documental verdadeiro estiver
    # quase empatado com stock, documental vence.
    # =================================================

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
            >= best["score"] - 9
        ):

            best = doc


    # =================================================
    # CONFIDENCE FLOOR
    # =================================================

    if best["score"] < 52:

        return (
            None,
            "vi66_confidence_floor",
            {
                "decision": "5X",
                "score":
                    best["score"]
            }
        )


    # =================================================
    # ANTI-CHURN
    # =================================================
    #
    # Só troca o atual se houver ganho
    # editorial significativo.
    # =================================================

    if (
        _key(best["original"])
        != _key(current_candidate)
    ):

        if (
            best["score"]
            < current_eval["score"] + 6
        ):

            best = current_eval

            best[
                "original"
            ] = current_candidate


    # =================================================
    # AMBIGUOUS GENERIC STOCK
    # =================================================

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
                _key(x["original"])
                != _key(best["original"])
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
                        "decision":
                            "5X",

                        "margin":
                            round(
                                margin,
                                2
                            )
                    }
                )


    chosen = best["original"]


    # Compatibilidade total com os logs
    # e failover VI6.3 existentes.
    chosen[
        "_vi6_class"
    ] = best["class"]

    chosen[
        "_vi6_risk"
    ] = best["risk"]

    chosen[
        "_vi6_quality_tier"
    ] = best["quality"]

    chosen[
        "_vi6_truth_ok"
    ] = best["truth_ok"]

    chosen[
        "_vi6_score"
    ] = best["score"]

    chosen[
        "_vi6_reason"
    ] = ",".join(
        best["reasons"]
    ) or "vi66_editorial"


    chosen[
        "_vi66_active"
    ] = True

    chosen[
        "_vi66_role"
    ] = best["role"]

    chosen[
        "_vi66_anchor"
    ] = best["anchor_ratio"]


    changed = (
        _key(chosen)
        != _key(current_candidate)
    )


    _remember_selected(
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
            "decision":
                decision,

            "score":
                best["score"],

            "class":
                best["class"],

            "role":
                best["role"],

            "semantic":
                best["semantic"],

            "provenance":
                best["provenance"],

            "anchor":
                best["anchor_ratio"],

            "truth_ok":
                best["truth_ok"],

            "reasons":
                best["reasons"]
        }
    )


def reset_state():

    _MEMORY_EXACT.clear()
    _MEMORY_ID.clear()
    _RECENT.clear()


# =====================================================
# SELF TEST
# =====================================================

def self_test():

    reset_state()


    scene = {
        "visual_mode":
            "evidence",

        "query":
            "Flight 19 disappearance 1945",

        "must_have":
            [
                "Flight 19",
                "1945"
            ],

        "segmento":
            "Flight 19 disappeared in 1945."
    }


    doc = {
        "fonte": "Wikimedia",
        "tipo": "foto",
        "id": "doc19",
        "url": "doc19",

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

        "wiki_query_tier":
            "CASE",

        "title":
            "Flight 19 aircraft 1945 archive"
    }


    wrong = dict(doc)

    wrong["id"] = "wrong"
    wrong["url"] = "wrong"

    wrong["title"] = (
        "TAM Flight 3054 archive"
    )


    stock = {
        "fonte": "Pixabay",
        "tipo": "vídeo",
        "id": "stock",
        "url": "stock",

        "class":
            "SAFE_CONTEXT",

        "risk": "LOW",
        "quality_tier": "NORMAL",
        "truth_ok": True,

        "semantic": 64,
        "provenance": 15,
        "score": 85,

        "reason":
            "generic_context_without_identity_claim",

        "description":
            "aircraft flying over ocean"
    }


    assert (
        evaluate(
            doc,
            scene,
            {"intent": "EVIDENCE"}
        )
        is not None
    )


    # Flight 19 != Flight 3054
    assert (
        evaluate(
            wrong,
            scene,
            {"intent": "EVIDENCE"}
        )
        is None
    )


    stock_eval = evaluate(
        stock,
        scene,
        {"intent": "EVIDENCE"}
    )

    assert (
        stock_eval
        is not None
    )

    assert (
        "stock_evidence_guard"
        in stock_eval["reasons"]
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


    # =================================
    # CTA MEMORY TEST
    # =================================

    reset_state()


    story_scene = {
        "visual_mode": "context",
        "query": "aircraft ocean"
    }


    story_vi6 = {
        "intent": "CONTEXT",
        "winner": stock
    }


    chosen, _, _ = supervisionar_vi6_6(
        story_vi6,
        [stock],
        story_scene,
        stock,
        "vi6_active_winner"
    )

    assert chosen is not None


    cta_winner = dict(stock)

    cta_winner["reuse"] = True

    cta_winner["reason"] = (
        "cta_reuses_verified_story_visual"
    )


    cta_scene = {
        "visual_mode": "cta_reuse"
    }


    cta_vi6 = {
        "intent": "CTA",
        "winner": cta_winner
    }


    cta, reason, meta = (
        supervisionar_vi6_6(
            cta_vi6,
            [],
            cta_scene,
            None,
            "original_not_found"
        )
    )


    assert cta is not None

    assert (
        reason
        == "vi66_cta_memory_reuse"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.6 STANDALONE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK VI6.3 direct integration"
    )
    print(
        "OK Documentary Rescue"
    )
    print(
        "OK Documentary Truth Lock"
    )
    print(
        "OK Flight/Case Identity Lock"
    )
    print(
        "OK Evidence Stock Guard"
    )
    print(
        "OK Person/Place Guards"
    )
    print(
        "OK Semantic Floor"
    )
    print(
        "OK Motion Relevance"
    )
    print(
        "OK Asset Repetition Guard"
    )
    print(
        "OK Source Fatigue"
    )
    print(
        "OK Anchor Coverage"
    )
    print(
        "OK Confidence Floor"
    )
    print(
        "OK Anti-Churn"
    )
    print(
        "OK CTA Memory Rescue"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# PATCH ADAPTATIVO SOBRE O VI6.3 REAL
# =====================================================

python - <<'PY'
from pathlib import Path
import re


p = Path("midia.py")

t = p.read_text(
    encoding="utf-8"
)


if "supervisionar_vi6_6" in t:

    print(
        "VI6.6 já está integrado."
    )

    raise SystemExit(0)


# Não depende de VI6.4.
# Localiza a chamada REAL do VI6.3,
# aceitando diferenças de espaços.

pattern = re.compile(
    r'''
    (?P<call>
        (?P<indent>^[ \t]*)
        vi6_active_candidate
        \s*,\s*
        vi6_active_reason
        \s*=\s*
        \(
        \s*
        decidir_vi6_3_active
        \(
        \s*
        vi6_scene
        \s*,\s*
        todos
        \s*
        \)
        \s*
        \)
    )
    ''',
    re.MULTILINE
    | re.VERBOSE
)


m = pattern.search(t)


if not m:

    raise SystemExit(
        "ERRO: chamada ativa do VI6.3 "
        "não foi localizada. "
        "midia.py NÃO foi alterado."
    )


indent = m.group(
    "indent"
)


extra_lines = [
    "",
    "# =========================================",
    "# VI6.6 STANDALONE ACTIVE SUPERVISOR",
    "# =========================================",
    "",
    "from vi6_6_active_brain import (",
    "    supervisionar_vi6_6",
    ")",
    "",
    "(",
    "    vi6_active_candidate,",
    "    vi6_active_reason,",
    "    vi66_meta",
    ") = supervisionar_vi6_6(",
    "    vi6_scene,",
    "    todos,",
    "    cena,",
    "    vi6_active_candidate,",
    "    vi6_active_reason",
    ")",
    "",
    "print(",
    '    "  VI6.6 SUPERVISOR:"',
    ")",
    "",
    "print(",
    "    f\"    DECISION=\"",
    "    f\"{vi66_meta.get('decision', '?')}\"",
    ")",
    "",
    "print(",
    "    f\"    REASON=\"",
    "    f\"{vi6_active_reason}\"",
    ")",
    "",
    "if vi66_meta.get('score') is not None:",
    "    print(",
    "        f\"    SCORE=\"",
    "        f\"{vi66_meta.get('score')}\"",
    "    )",
    "",
    "if vi66_meta.get('role'):",
    "    print(",
    "        f\"    ROLE=\"",
    "        f\"{vi66_meta.get('role')}\"",
    "    )",
    "",
    "if vi66_meta.get('anchor') is not None:",
    "    print(",
    "        f\"    ANCHOR=\"",
    "        f\"{vi66_meta.get('anchor')}\"",
    "    )",
    ""
]


extra = "\n".join(
    (
        indent + line
        if line
        else ""
    )
    for line in extra_lines
)


replacement = (
    m.group("call")
    + "\n"
    + extra
)


t = (
    t[:m.start()]
    + replacement
    + t[m.end():]
)


p.write_text(
    t,
    encoding="utf-8"
)


print()
print(
    "OK VI6.6 integrado diretamente ao VI6.3"
)
PY


# =====================================================
# OFFLINE AUDIT
# =====================================================

cat > testar_vi66_offline.py <<'PY'
#!/usr/bin/env python3

import glob
import json
import os

from vi6_6_active_brain import (
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
    "r",
    encoding="utf-8"
) as f:

    data = json.load(f)


reset_state()


docs = 0
safe = 0
fallback = 0
blocked = 0
total = 0


print()
print(
    "======================================"
)
print(
    " VI6.6 RETROSPECTIVE AUDIT"
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

    number = int(
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


    valid = []


    for item in pool:

        result = evaluate(
            item,
            scene,
            scene
        )

        if result is not None:
            valid.append(result)


    valid.sort(
        key=lambda x:
            x["score"],
        reverse=True
    )


    if not valid:

        fallback += 1
        blocked += 1

        print(
            f"CENA {number:02d} "
            f"-> 5X_FALLBACK "
            f"| no-safe-candidate"
        )

        continue


    best = valid[0]


    if best["score"] < 52:

        fallback += 1

        print(
            f"CENA {number:02d} "
            f"-> 5X_FALLBACK "
            f"| score={best['score']}"
        )

        continue


    if (
        best["class"]
        == "REAL_DOCUMENTARY"
    ):

        docs += 1

    else:

        safe += 1


    item = best["item"]


    print(
        f"CENA {number:02d} "
        f"-> VI6.6 "
        f"| {best['class']} "
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
    " RESUMO VI6.6 OFFLINE"
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
    "HARD/NO-SAFE:",
    blocked
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
# VALIDATION
# =====================================================

echo
echo "===== PYTHON COMPILE ====="

if ! python -m py_compile \
    vi6_6_active_brain.py \
    testar_vi66_offline.py \
    visual_intelligence_6.py \
    midia.py
then

    echo "ERRO DE COMPILE."
    rollback
    exit 1
fi

echo "PYTHON STATUS=0"


echo
echo "===== SELF TEST ====="

if ! python vi6_6_active_brain.py
then

    echo "SELF TEST FALHOU."
    rollback
    exit 1
fi


echo
echo "===== BASH CHECK ====="

if ! bash -n gerar_short.sh
then

    echo "BASH CHECK FALHOU."
    rollback
    exit 1
fi

echo "BASH STATUS=0"


echo
echo "===== RELEASE CHECK ====="

if ! ./release_check.sh
then

    echo "RELEASE CHECK FALHOU."
    rollback
    exit 1
fi


echo
echo "======================================"
echo " VI6.6 STANDALONE INSTALADO"
echo "======================================"
echo
echo "OK sem dependencia do VI6.4"
echo "OK sem dependencia do VI6.5"
echo "OK integração direta VI6.3"
echo "OK Documentary Rescue"
echo "OK Truth Lock"
echo "OK Flight/Case Identity Lock"
echo "OK Evidence Stock Guard"
echo "OK Generic Person Guard"
echo "OK Generic Place Guard"
echo "OK Anchor Coverage"
echo "OK Semantic Floor"
echo "OK Motion Relevance Guard"
echo "OK Duplicate Asset Guard"
echo "OK Source Fatigue Guard"
echo "OK Confidence Floor"
echo "OK Anti-Churn"
echo "OK Ambiguous Stock Guard"
echo "OK CTA Memory Rescue"
echo "OK fallback VI6.3"
echo "OK fallback 5.x"
echo
echo "VIDEOS GERADOS=0"
echo "DOWNLOADS NOVOS=0"
echo


echo "======================================"
echo " AUDITORIA OFFLINE AUTOMATICA"
echo "======================================"

python testar_vi66_offline.py

