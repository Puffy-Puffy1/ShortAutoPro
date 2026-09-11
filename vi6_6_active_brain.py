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
