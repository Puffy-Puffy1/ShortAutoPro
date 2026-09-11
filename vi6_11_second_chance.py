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
