#!/usr/bin/env python3

import os
from collections import Counter

from visual_selection_engine_v4 import (
    score_candidate,
    must_tier,
    provider,
    source_group,
    media_type,
    candidate_key,
)


_HISTORY = {
    "providers": [],
    "groups": [],
    "types": [],
    "keys": [],
}


def _scene_from_context(ctx):

    if not isinstance(
        ctx,
        dict,
    ):
        ctx = {}


    def first(*names):

        for name in names:

            value = ctx.get(
                name
            )

            if value not in (
                None,
                "",
                [],
                {},
            ):
                return value

        return ""


    return {
        "texto":
            first(
                "segmento",
                "texto",
                "scene_text",
                "texto_cena",
            ),

        "visual_query":
            first(
                "busca",
                "visual_query",
                "query",
            ),

        "must_have":
            first(
                "must_have",
                "must",
            )
            or
            [],

        "avoid":
            first(
                "avoid",
                "avoid_terms",
            )
            or
            [],

        "location":
            first(
                "location",
                "localizacao",
                "geo",
            ),
    }


def _effective(result):

    if not isinstance(
        result,
        dict,
    ):
        return 0.0

    for key in (
        "effective",
        "effective_score",
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
            return float(value)

    return 0.0


def rerank_pool(
    pool,
    context=None,
):

    if (
        os.environ.get(
            "SAP_VSE42_RUNTIME",
            "1",
        )
        ==
        "0"
    ):

        return list(
            pool or []
        ), {
            "enabled": False,
            "summary": "kill-switch",
        }


    pool = list(
        pool or []
    )


    if len(pool) <= 1:

        return pool, {
            "enabled": True,
            "summary":
                f"pool={len(pool)}",
        }


    scene = _scene_from_context(
        context
        or
        {}
    )


    state = {
        key: list(value)
        for key, value
        in _HISTORY.items()
    }


    provider_counts = Counter(
        _HISTORY[
            "providers"
        ]
    )

    group_counts = Counter(
        _HISTORY[
            "groups"
        ]
    )

    key_counts = Counter(
        _HISTORY[
            "keys"
        ]
    )


    ranked = []


    for index, candidate in enumerate(
        pool
    ):

        try:

            result = score_candidate(
                candidate,
                scene,
                state,
            )

        except Exception as exc:

            result = {
                "hard_mismatch":
                    False,

                "effective":
                    -100000.0,

                "bridge_error":
                    (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
            }


        hard = bool(
            result.get(
                "hard_mismatch",
                False,
            )
        )


        try:
            tier = int(
                must_tier(
                    candidate,
                    scene,
                )
            )
        except Exception:
            tier = 0


        try:
            prov = provider(
                candidate
            )
        except Exception:
            prov = "unknown"


        try:
            group = source_group(
                candidate
            )
        except Exception:
            group = "unknown"


        try:
            typ = media_type(
                candidate
            )
        except Exception:
            typ = "unknown"


        try:
            key = candidate_key(
                candidate
            )
        except Exception:
            key = (
                f"{prov}:"
                f"{typ}:"
                f"{index}"
            )


        effective = _effective(
            result
        )


        # ----------------------------------------------------
        # Diversity adjustments
        # ----------------------------------------------------

        adjusted = effective


        if (
            _HISTORY["providers"]
            and
            prov
            ==
            _HISTORY["providers"][-1]
        ):
            adjusted -= 12.0


        adjusted -= (
            provider_counts[
                prov
            ]
            *
            3.0
        )


        if (
            group
            and
            group != "unknown"
        ):

            adjusted -= (
                group_counts[
                    group
                ]
                *
                4.0
            )


        if key_counts[
            key
        ]:

            adjusted -= (
                60.0
                *
                key_counts[
                    key
                ]
            )


        # Evita longas sequências só foto ou só vídeo.
        if (
            len(
                _HISTORY[
                    "types"
                ]
            )
            >= 3
            and
            len(
                set(
                    _HISTORY[
                        "types"
                    ][-3:]
                )
            )
            ==
            1
            and
            typ
            ==
            _HISTORY[
                "types"
            ][-1]
        ):

            adjusted -= 7.0


        # hard mismatch sempre perde para candidato válido.
        valid_rank = (
            0
            if hard
            else 1
        )


        ranked.append(
            {
                "candidate":
                    candidate,

                "original_index":
                    index,

                "hard":
                    hard,

                "tier":
                    tier,

                "effective":
                    effective,

                "adjusted":
                    adjusted,

                "provider":
                    prov,

                "group":
                    group,

                "type":
                    typ,

                "key":
                    key,

                "details":
                    result,
            }
        )


    ranked.sort(
        key=lambda item: (
            item[
                "hard"
            ]
            is False,

            item[
                "tier"
            ],

            item[
                "adjusted"
            ],

            -item[
                "original_index"
            ],
        ),
        reverse=True,
    )


    output = [
        item[
            "candidate"
        ]
        for item in ranked
    ]


    top = ranked[0]


    max_tier = max(
        item[
            "tier"
        ]
        for item in ranked
    )


    provider_pool = Counter(
        item[
            "provider"
        ]
        for item in ranked
    )


    meta = {
        "enabled":
            True,

        "pool":
            len(
                ranked
            ),

        "max_tier":
            max_tier,

        "rescue_needed":
            max_tier < 2,

        "top_provider":
            top[
                "provider"
            ],

        "top_type":
            top[
                "type"
            ],

        "top_tier":
            top[
                "tier"
            ],

        "top_hard_mismatch":
            top[
                "hard"
            ],

        "provider_pool":
            dict(
                provider_pool
            ),

        "summary":
            (
                f"pool={len(ranked)} "
                f"top={top['provider']}/"
                f"{top['type']} "
                f"tier={top['tier']} "
                f"hard={top['hard']} "
                f"providers="
                f"{dict(provider_pool)}"
            ),
    }


    return output, meta


def note_selected(candidate):

    try:
        prov = provider(
            candidate
        )
    except Exception:
        prov = "unknown"


    try:
        group = source_group(
            candidate
        )
    except Exception:
        group = "unknown"


    try:
        typ = media_type(
            candidate
        )
    except Exception:
        typ = "unknown"


    try:
        key = candidate_key(
            candidate
        )
    except Exception:
        key = (
            f"{prov}:"
            f"{typ}:"
            f"{len(_HISTORY['keys'])}"
        )


    _HISTORY[
        "providers"
    ].append(
        prov
    )

    _HISTORY[
        "groups"
    ].append(
        group
    )

    _HISTORY[
        "types"
    ].append(
        typ
    )

    _HISTORY[
        "keys"
    ].append(
        key
    )


    # histórico limitado para não crescer indefinidamente
    for name in _HISTORY:

        if len(
            _HISTORY[
                name
            ]
        ) > 30:

            _HISTORY[
                name
            ] = (
                _HISTORY[
                    name
                ][-30:]
            )


def history():

    return {
        key: list(value)
        for key, value
        in _HISTORY.items()
    }
