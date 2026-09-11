#!/usr/bin/env python3

import os


def enabled():

    return (
        os.getenv(
            "SAP_VSE_V42",
            "1",
        )
        !=
        "0"
    )


def _flatten(value):

    if value is None:
        return []

    if isinstance(
        value,
        str,
    ):

        value = value.strip()

        return (
            [value]
            if value
            else []
        )

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):

        out = []

        for item in value:
            out.extend(
                _flatten(item)
            )

        return out

    if isinstance(
        value,
        dict,
    ):

        out = []

        for item in value.values():
            out.extend(
                _flatten(item)
            )

        return out

    return [
        str(value)
    ]


def build_scene_text(context):

    """
    Constrói contexto semântico usando somente
    variáveis já existentes no midia.py.

    Nenhuma alteração nos dados originais.
    """

    fields = (
        "segmento",
        "texto",
        "text",
        "frase",
        "busca",
        "query",
        "visual_query",
        "must_have",
        "avoid",
        "location",
        "localizacao",
        "tema",
        "topic",
        "visual_mode",
    )

    pieces = []

    seen = set()

    for field in fields:

        if field not in context:
            continue

        for value in _flatten(
            context.get(field)
        ):

            value = value.strip()

            if not value:
                continue

            key = value.casefold()

            if key in seen:
                continue

            seen.add(key)

            pieces.append(
                value
            )

    return " ".join(
        pieces
    )


def build_state(context):

    """
    Reaproveita histórico quando disponível.
    Caso não exista, usa estado neutro.
    """

    state = {
        "providers": [],
        "groups": [],
        "types": [],
        "keys": [],
    }

    possible_states = (
        "state",
        "diversity_state",
        "visual_state",
        "history",
        "historico",
    )

    for name in possible_states:

        value = context.get(
            name
        )

        if not isinstance(
            value,
            dict,
        ):
            continue

        for key in state:

            current = value.get(
                key
            )

            if isinstance(
                current,
                (
                    list,
                    tuple,
                    set,
                ),
            ):

                state[key] = list(
                    current
                )

        break

    return state


def _effective(result):

    if not isinstance(
        result,
        dict,
    ):
        return 0.0

    for key in (
        "effective",
        "effective_score",
        "score_final",
        "final_score",
        "score",
    ):

        value = result.get(
            key
        )

        if isinstance(
            value,
            (
                int,
                float,
            ),
        ):
            return float(
                value
            )

    return 0.0


def _must(result):

    if not isinstance(
        result,
        dict,
    ):
        return 0

    for key in (
        "must_tier",
        "must",
        "must_score",
        "must_hits",
    ):

        value = result.get(
            key
        )

        if isinstance(
            value,
            (
                int,
                float,
            ),
        ):

            if value >= 2:
                return 2

            if value >= 1:
                return 1

    return 0


def rerank_pool(
    pool,
    context,
):

    """
    Final authority do VSE4.2.

    Reordena somente.
    Não baixa.
    Não remove.
    Não modifica candidato.
    """

    if not enabled():

        print(
            "VSE42_BRIDGE=DISABLED"
        )

        return pool


    if not isinstance(
        pool,
        (
            list,
            tuple,
        ),
    ):

        return pool


    pool = list(
        pool
    )


    if len(pool) <= 1:

        return pool


    scene_text = build_scene_text(
        context
    )


    if not scene_text:

        print(
            "VSE42_BRIDGE=FAIL_OPEN_NO_SCENE"
        )

        return pool


    try:

        from visual_selection_engine_v4 import (
            score_candidate,
        )

    except Exception as exc:

        print(
            "VSE42_BRIDGE=FAIL_OPEN_IMPORT "
            f"{type(exc).__name__}: {exc}"
        )

        return pool


    state = build_state(
        context
    )

    ranked = []


    for index, candidate in enumerate(
        pool
    ):

        try:

            result = score_candidate(
                candidate,
                scene_text,
                state,
            )

        except Exception as exc:

            print(
                "VSE42_SCORE_FAIL_OPEN "
                f"index={index} "
                f"{type(exc).__name__}: {exc}"
            )

            result = {}


        hard = bool(
            result.get(
                "hard_mismatch",
                False,
            )
        ) if isinstance(
            result,
            dict,
        ) else False


        ranked.append(
            {
                "index":
                    index,

                "candidate":
                    candidate,

                "result":
                    result,

                "safe":
                    0 if hard else 1,

                "must":
                    _must(
                        result
                    ),

                "effective":
                    _effective(
                        result
                    ),
            }
        )


    # --------------------------------------------------------
    # PRIORIDADE:
    #
    # 1. candidato sem hard mismatch
    # 2. cobertura MUST
    # 3. score efetivo VSE4
    # 4. ordem original como desempate
    # --------------------------------------------------------

    ranked.sort(
        key=lambda item: (
            item["safe"],
            item["must"],
            item["effective"],
            -item["index"],
        ),
        reverse=True,
    )


    before = ranked_by_original = None

    if pool:
        before = pool[0]


    result_pool = [
        item["candidate"]
        for item in ranked
    ]


    after = (
        result_pool[0]
        if result_pool
        else None
    )


    winner = ranked[0]


    print(
        "VSE42_BRIDGE=ACTIVE"
    )

    print(
        "VSE42_POOL_SIZE="
        f"{len(pool)}"
    )

    print(
        "VSE42_SCENE="
        f"{scene_text[:180]}"
    )

    print(
        "VSE42_WINNER_SAFE="
        f"{winner['safe']}"
    )

    print(
        "VSE42_WINNER_MUST="
        f"{winner['must']}"
    )

    print(
        "VSE42_WINNER_EFFECTIVE="
        f"{winner['effective']:.2f}"
    )

    print(
        "VSE42_OVERRIDE="
        +
        (
            "YES"
            if after is not before
            else "NO"
        )
    )


    return result_pool


if __name__ == "__main__":

    print(
        "VISUAL_SELECTION_BRIDGE_V42=READY"
    )



# ============================================================
# SHORTAUTOPRO VSE4.2.2 BRIDGE CONTRACT
# ============================================================
#
# Contrato público usado por midia.py:
#
# rank_pool(
#     pool,
#     escolhido,
#     context
# )
#
# ->
#
# (
#     ranked_pool,
#     winner,
#     metadata,
# )
#
#
# commit_candidate(candidate)
#
# Mantém histórico em memória durante a execução de midia.py.
#
# Kill switch:
#
# SAP_VSE42_BRIDGE=0
#
# ============================================================


_VSE422_STATE = {
    "providers": [],
    "groups": [],
    "types": [],
    "keys": [],
}


_VSE422_LAST_COMMIT = None


def _vse422_enabled():

    import os

    return (
        os.getenv(
            "SAP_VSE42_BRIDGE",
            "1",
        )
        !=
        "0"
    )


def _vse422_scene_from_context(
    context,
):

    if context is None:
        return {}


    if not isinstance(
        context,
        dict,
    ):

        return {
            "texto":
                str(context)
        }


    # Estruturas de cena mais prováveis.
    for name in (
        "scene",
        "cena",
        "segmento",
        "scene_data",
        "scene_info",
    ):

        value = context.get(
            name
        )

        if isinstance(
            value,
            dict,
        ):

            result = dict(
                value
            )

            # Completa metadados externos.
            for key in (
                "texto",
                "text",
                "visual_query",
                "busca",
                "query",
                "must_have",
                "avoid",
                "location",
                "local",
                "topic",
                "tema",
                "visual_mode",
            ):

                if (
                    key not in result
                    and
                    key in context
                ):

                    result[
                        key
                    ] = context[
                        key
                    ]

            return result


        if isinstance(
            value,
            str,
        ) and value.strip():

            return {
                "texto":
                    value,

                "must_have":
                    context.get(
                        "must_have",
                        [],
                    ),

                "avoid":
                    context.get(
                        "avoid",
                        [],
                    ),

                "location":
                    (
                        context.get(
                            "location"
                        )
                        or
                        context.get(
                            "local"
                        )
                    ),

                "visual_query":
                    (
                        context.get(
                            "visual_query"
                        )
                        or
                        context.get(
                            "busca"
                        )
                    ),
            }


    result = {}


    mapping = {
        "texto":
            (
                "texto",
                "text",
                "descricao",
                "description",
            ),

        "visual_query":
            (
                "visual_query",
                "busca",
                "query",
                "search_query",
            ),

        "must_have":
            (
                "must_have",
                "must",
            ),

        "avoid":
            (
                "avoid",
                "avoid_terms",
            ),

        "location":
            (
                "location",
                "local",
                "localizacao",
            ),

        "topic":
            (
                "topic",
                "tema",
            ),

        "visual_mode":
            (
                "visual_mode",
                "modo_visual",
            ),
    }


    for target, aliases in mapping.items():

        for alias in aliases:

            if alias not in context:
                continue

            value = context.get(
                alias
            )

            if value is None:
                continue

            result[
                target
            ] = value

            break


    return result


def _vse422_state():

    return _VSE422_STATE


def reset_state():

    global _VSE422_LAST_COMMIT

    for key in (
        "providers",
        "groups",
        "types",
        "keys",
    ):

        _VSE422_STATE[
            key
        ] = []


    _VSE422_LAST_COMMIT = None


    return True


def get_state():

    return {
        key:
            list(
                value
            )

        for key, value
        in
        _VSE422_STATE.items()
    }


def _vse422_candidate_geo_mismatch(
    candidate,
    scene,
):

    try:

        from visual_selection_engine_v4 import (
            candidate_text,
            geo_hits,
        )


        scene_text = candidate_text(
            scene
        )

        candidate_txt = candidate_text(
            candidate
        )


        scene_geo = set(
            geo_hits(
                scene_text
            )
        )

        candidate_geo = set(
            geo_hits(
                candidate_txt
            )
        )


        # Só consideramos HARD quando os dois lados
        # possuem evidência geográfica explícita.
        if (
            scene_geo
            and
            candidate_geo
            and
            scene_geo.isdisjoint(
                candidate_geo
            )
        ):

            return (
                True,
                sorted(
                    scene_geo
                ),
                sorted(
                    candidate_geo
                ),
            )


        return (
            False,
            sorted(
                scene_geo
            ),
            sorted(
                candidate_geo
            ),
        )


    except Exception:

        return (
            False,
            [],
            [],
        )


def _vse422_direct_rank(
    pool,
    scene,
):

    from visual_selection_engine_v4 import (
        score_candidate,
    )


    ranked = []


    for index, candidate in enumerate(
        pool
    ):

        try:

            score = score_candidate(
                candidate,
                scene,
                _VSE422_STATE,
            )


            if not isinstance(
                score,
                dict,
            ):

                score = {}


        except Exception as exc:

            score = {
                "hard_mismatch":
                    False,

                "must":
                    0,

                "effective":
                    0.0,

                "_score_error":
                    (
                        type(exc).__name__
                        +
                        ":"
                        +
                        str(exc)
                    ),
            }


        hard = bool(
            score.get(
                "hard_mismatch",
                False,
            )
        )


        geo_hard, scene_geo, candidate_geo = (
            _vse422_candidate_geo_mismatch(
                candidate,
                scene,
            )
        )


        if geo_hard:
            hard = True


        must = (
            score.get(
                "must",
                score.get(
                    "must_tier",
                    0,
                ),
            )
        )


        try:
            must = int(
                must
            )
        except Exception:
            must = 0


        effective = score.get(
            "effective",
            score.get(
                "effective_score",
                score.get(
                    "score",
                    0.0,
                ),
            ),
        )


        try:
            effective = float(
                effective
            )
        except Exception:
            effective = 0.0


        # HARD mismatch nunca deve vencer apenas
        # por possuir score/MUST alto.
        safe = (
            0
            if hard
            else 1
        )


        ranked.append(
            {
                "candidate":
                    candidate,

                "index":
                    index,

                "safe":
                    safe,

                "must":
                    must,

                "effective":
                    effective,

                "hard_mismatch":
                    hard,

                "geo_hard":
                    geo_hard,

                "scene_geo":
                    scene_geo,

                "candidate_geo":
                    candidate_geo,

                "score":
                    score,
            }
        )


    ranked.sort(
        key=lambda item: (
            item[
                "safe"
            ],

            item[
                "must"
            ],

            item[
                "effective"
            ],

            -item[
                "index"
            ],
        ),
        reverse=True,
    )


    return ranked


def rank_pool(
    pool,
    escolhido=None,
    context=None,
):

    """
    API pública VSE4.2 usada por midia.py.

    Sempre retorna exatamente:

        (
            ranked_pool,
            winner,
            metadata
        )

    Fail-open:
    em erro retorna pool original + escolhido.
    """

    if pool is None:
        pool = []


    try:
        pool = list(
            pool
        )
    except Exception:
        pool = []


    if not pool:

        return (
            [],
            escolhido,
            {
                "active":
                    False,

                "reason":
                    "EMPTY_POOL",

                "pool_size":
                    0,
            },
        )


    if not _vse422_enabled():

        return (
            pool,
            (
                escolhido
                if escolhido is not None
                else pool[0]
            ),
            {
                "active":
                    False,

                "reason":
                    "KILL_SWITCH",

                "pool_size":
                    len(
                        pool
                    ),
            },
        )


    scene = _vse422_scene_from_context(
        context
    )


    try:

        ranked = _vse422_direct_rank(
            pool,
            scene,
        )


        if not ranked:

            return (
                pool,
                escolhido,
                {
                    "active":
                        True,

                    "reason":
                        "NO_RANK_RESULT",

                    "pool_size":
                        len(
                            pool
                        ),
                },
            )


        ranked_pool = [
            item[
                "candidate"
            ]
            for item in ranked
        ]


        winner = ranked_pool[
            0
        ]


        before = (
            escolhido
            if escolhido is not None
            else pool[
                0
            ]
        )


        top = ranked[
            0
        ]


        metadata = {
            "active":
                True,

            "pool_size":
                len(
                    ranked_pool
                ),

            "override":
                winner is not before,

            "safe":
                top[
                    "safe"
                ],

            "must":
                top[
                    "must"
                ],

            "effective":
                top[
                    "effective"
                ],

            "hard_mismatch":
                top[
                    "hard_mismatch"
                ],

            "geo_hard":
                top[
                    "geo_hard"
                ],

            "scene_geo":
                top[
                    "scene_geo"
                ],

            "candidate_geo":
                top[
                    "candidate_geo"
                ],
        }


        print(
            "  VSE422_BRIDGE=ACTIVE"
        )

        print(
            "  VSE422_POOL_SIZE="
            +
            str(
                metadata[
                    "pool_size"
                ]
            )
        )

        print(
            "  VSE422_WINNER_SAFE="
            +
            str(
                metadata[
                    "safe"
                ]
            )
        )

        print(
            "  VSE422_WINNER_MUST="
            +
            str(
                metadata[
                    "must"
                ]
            )
        )

        print(
            "  VSE422_WINNER_EFFECTIVE="
            +
            f"{metadata['effective']:.2f}"
        )

        print(
            "  VSE422_GEO_HARD="
            +
            str(
                metadata[
                    "geo_hard"
                ]
            )
        )

        print(
            "  VSE422_OVERRIDE="
            +
            (
                "YES"
                if metadata[
                    "override"
                ]
                else "NO"
            )
        )


        return (
            ranked_pool,
            winner,
            metadata,
        )


    except Exception as exc:

        print(
            "  VSE422_BRIDGE_FAIL_OPEN="
            +
            type(exc).__name__
            +
            ":"
            +
            str(exc)
        )


        return (
            pool,
            (
                escolhido
                if escolhido is not None
                else pool[
                    0
                ]
            ),
            {
                "active":
                    False,

                "reason":
                    (
                        type(exc).__name__
                        +
                        ":"
                        +
                        str(exc)
                    ),

                "pool_size":
                    len(
                        pool
                    ),
            },
        )


def commit_candidate(
    candidate,
):

    """
    Registra apenas um candidato já baixado/aceito.

    Isto alimenta diversidade de:
    provider,
    source_group,
    media type,
    asset key.
    """

    global _VSE422_LAST_COMMIT


    if candidate is None:
        return False


    if not _vse422_enabled():
        return False


    try:

        from visual_selection_engine_v4 import (
            provider,
            source_group,
            media_type,
            candidate_key,
        )


        p = provider(
            candidate
        )

        g = source_group(
            candidate
        )

        t = media_type(
            candidate
        )

        k = candidate_key(
            candidate
        )


        # Evita double-commit provocado por duas
        # pontes consecutivas para o mesmo vencedor.
        if (
            k
            and
            k == _VSE422_LAST_COMMIT
        ):

            print(
                "  VSE422_COMMIT=DUPLICATE_NOOP"
            )

            return True


        if p:
            _VSE422_STATE[
                "providers"
            ].append(
                p
            )


        if g:
            _VSE422_STATE[
                "groups"
            ].append(
                g
            )


        if t:
            _VSE422_STATE[
                "types"
            ].append(
                t
            )


        if k:
            _VSE422_STATE[
                "keys"
            ].append(
                k
            )


        # Janela limitada para não crescer indefinidamente.
        for name in (
            "providers",
            "groups",
            "types",
            "keys",
        ):

            _VSE422_STATE[
                name
            ] = (
                _VSE422_STATE[
                    name
                ][
                    -48:
                ]
            )


        _VSE422_LAST_COMMIT = k


        print(
            "  VSE422_COMMIT=PASS"
        )

        print(
            "  VSE422_COMMIT_PROVIDER="
            +
            str(
                p
            )
        )

        print(
            "  VSE422_COMMIT_GROUP="
            +
            str(
                g
            )
        )

        print(
            "  VSE422_COMMIT_TYPE="
            +
            str(
                t
            )
        )


        return True


    except Exception as exc:

        print(
            "  VSE422_COMMIT_FAIL_OPEN="
            +
            type(exc).__name__
            +
            ":"
            +
            str(exc)
        )

        return False


# Compatibilidade para nomes usados por módulos auxiliares.
def note_candidate(
    candidate,
):
    return commit_candidate(
        candidate
    )


def note_selection(
    candidate,
):
    return commit_candidate(
        candidate
    )


def commit(
    candidate,
):
    return commit_candidate(
        candidate
    )

