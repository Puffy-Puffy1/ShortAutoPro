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
