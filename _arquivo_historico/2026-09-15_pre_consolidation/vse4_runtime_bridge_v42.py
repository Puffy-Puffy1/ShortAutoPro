#!/usr/bin/env python3

import json
import os
from collections import Counter

from visual_selection_engine_v4 import (
    base_score,
    candidate_key,
    candidate_text,
    flatten_candidates,
    media_type,
    must_tier,
    provider,
    score_candidate,
    source_group,
)


ENABLED = (
    os.getenv(
        "SAP_VSE4",
        "1",
    )
    !=
    "0"
)


MIN_SAME_TIER_GAIN = float(
    os.getenv(
        "SAP_VSE42_MIN_GAIN",
        "8.0",
    )
)


def _stringify(value):

    if value is None:
        return ""

    if isinstance(
        value,
        str,
    ):
        return value.strip()

    if isinstance(
        value,
        (
            int,
            float,
            bool,
        ),
    ):
        return str(value)

    try:

        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
        )

    except Exception:

        try:
            return str(value)
        except Exception:
            return ""


def _scene_from_scope(scope):

    """
    Reconstrói o contexto semântico da cena usando
    apenas variáveis locais conhecidas.

    Não modifica locals().
    """

    priority = (
        "scene",
        "cena",
        "segmento",
        "texto",
        "texto_cena",
        "narracao",
        "frase",
        "busca",
        "visual_query",
        "query",
        "must_have",
        "avoid",
        "location",
        "local",
        "cidade",
        "pais",
        "tema",
        "topic",
    )

    parts = []

    seen = set()

    for name in priority:

        if name not in scope:
            continue

        value = _stringify(
            scope.get(name)
        )

        if not value:
            continue

        key = value.casefold()

        if key in seen:
            continue

        seen.add(key)

        parts.append(
            value
        )


    return " | ".join(
        parts
    )


def _state_from_scope(scope):

    # Se o pipeline já possui state compatível,
    # usa uma cópia.
    existing = scope.get(
        "state"
    )

    if isinstance(
        existing,
        dict,
    ):

        return {
            "providers":
                list(
                    existing.get(
                        "providers",
                        [],
                    )
                ),

            "groups":
                list(
                    existing.get(
                        "groups",
                        [],
                    )
                ),

            "types":
                list(
                    existing.get(
                        "types",
                        [],
                    )
                ),

            "keys":
                list(
                    existing.get(
                        "keys",
                        [],
                    )
                ),
        }


    result = {
        "providers": [],
        "groups": [],
        "types": [],
        "keys": [],
    }


    # Compatibilidade com nomes usados por versões
    # anteriores do ShortAutoPro.
    aliases = {

        "providers": (
            "provider_history",
            "providers_history",
            "historico_providers",
            "historico_provider",
        ),

        "groups": (
            "group_history",
            "source_group_history",
            "historico_groups",
        ),

        "types": (
            "type_history",
            "media_type_history",
            "historico_types",
        ),

        "keys": (
            "candidate_history",
            "key_history",
            "historico_candidates",
        ),
    }


    for target, names in aliases.items():

        for name in names:

            value = scope.get(
                name
            )

            if isinstance(
                value,
                (
                    list,
                    tuple,
                ),
            ):

                result[
                    target
                ] = list(
                    value
                )

                break


    return result


def _dedupe(candidates):

    result = []
    seen = set()

    for candidate in candidates:

        if candidate is None:
            continue

        try:
            key = candidate_key(
                candidate
            )
        except Exception:
            key = repr(candidate)

        if not key:
            key = repr(candidate)

        if key in seen:
            continue

        seen.add(key)

        result.append(
            candidate
        )

    return result


def _score(candidate, scene, state):

    data = score_candidate(
        candidate,
        scene,
        state,
    )

    if not isinstance(
        data,
        dict,
    ):
        data = {}


    try:
        effective = float(
            data.get(
                "effective",
                data.get(
                    "effective_score",
                    base_score(candidate),
                ),
            )
        )
    except Exception:
        effective = float(
            base_score(
                candidate
            )
        )


    try:
        tier = int(
            data.get(
                "must_tier",
                must_tier(
                    candidate,
                    scene,
                ),
            )
        )
    except Exception:
        tier = 0


    hard = bool(
        data.get(
            "hard_mismatch",
            False,
        )
    )


    return {
        "candidate":
            candidate,

        "data":
            data,

        "hard":
            hard,

        "tier":
            tier,

        "effective":
            effective,

        "provider":
            provider(
                candidate
            ),

        "group":
            source_group(
                candidate
            ),

        "type":
            media_type(
                candidate
            ),

        "key":
            candidate_key(
                candidate
            ),
    }


def choose_from_scope(
    scope,
    reference,
    pool,
):

    """
    Último gate antes do download.

    Regras:
    1. HARD_MISMATCH nunca vence candidato seguro.
    2. Pode substituir referência errada mesmo que ela
       tenha MUST maior.
    3. Fora de hard mismatch, nunca reduz MUST.
    4. MUST maior vence.
    5. Mesmo MUST exige ganho real de score.
    6. Retorna pool reordenado.
    """

    if not ENABLED:

        return (
            reference,
            list(pool or []),
            {
                "enabled": False,
                "reason": "SAP_VSE4_DISABLED",
            },
        )


    scene = _scene_from_scope(
        scope
    )

    state = _state_from_scope(
        scope
    )


    raw_pool = []

    if reference is not None:
        raw_pool.append(
            reference
        )


    try:

        raw_pool.extend(
            flatten_candidates(
                pool
            )
        )

    except Exception:

        if isinstance(
            pool,
            (
                list,
                tuple,
            ),
        ):
            raw_pool.extend(
                pool
            )


    candidates = _dedupe(
        raw_pool
    )


    if not candidates:

        return (
            reference,
            list(pool or []),
            {
                "enabled": True,
                "reason": "EMPTY_POOL",
            },
        )


    scored = []

    for candidate in candidates:

        try:

            scored.append(
                _score(
                    candidate,
                    scene,
                    state,
                )
            )

        except Exception as exc:

            print(
                "VSE42_SCORE_ERROR="
                f"{type(exc).__name__}:"
                f"{exc}"
            )


    if not scored:

        return (
            reference,
            list(pool or []),
            {
                "enabled": True,
                "reason": "SCORING_FAILED_OPEN",
            },
        )


    reference_score = None

    try:
        ref_key = candidate_key(
            reference
        )
    except Exception:
        ref_key = None


    for item in scored:

        if (
            reference_score is None
            and
            item[
                "key"
            ]
            ==
            ref_key
        ):

            reference_score = item


    if reference_score is None:

        reference_score = scored[
            0
        ]


    # Hard mismatch vai para o final.
    ordered = sorted(
        scored,
        key=lambda x: (
            0 if x["hard"] else 1,
            x["tier"],
            x["effective"],
        ),
        reverse=True,
    )


    safe = [
        item
        for item in ordered
        if not item[
            "hard"
        ]
    ]


    best = (
        safe[0]
        if safe
        else reference_score
    )


    selected = reference_score

    reason = "REFERENCE_PRESERVED"


    if (
        reference_score[
            "hard"
        ]
        and
        not best[
            "hard"
        ]
    ):

        selected = best

        reason = (
            "HARD_MISMATCH_RESCUE"
        )


    elif (
        not best[
            "hard"
        ]
        and
        best[
            "tier"
        ]
        >
        reference_score[
            "tier"
        ]
    ):

        selected = best

        reason = (
            "MUST_TIER_UPGRADE"
        )


    elif (
        not best[
            "hard"
        ]
        and
        best[
            "tier"
        ]
        ==
        reference_score[
            "tier"
        ]
        and
        best[
            "effective"
        ]
        >=
        (
            reference_score[
                "effective"
            ]
            +
            MIN_SAME_TIER_GAIN
        )
    ):

        selected = best

        reason = (
            "SAME_TIER_QUALITY_UPGRADE"
        )


    chosen = selected[
        "candidate"
    ]


    chosen_key = selected[
        "key"
    ]


    # O vencedor fica primeiro.
    new_pool = [
        chosen
    ]

    for item in ordered:

        if item[
            "key"
        ] == chosen_key:
            continue

        new_pool.append(
            item[
                "candidate"
            ]
        )


    provider_counts = Counter(
        item[
            "provider"
        ]
        for item in scored
    )


    telemetry = {

        "enabled":
            True,

        "reason":
            reason,

        "scene":
            scene,

        "pool_size":
            len(scored),

        "provider_counts":
            dict(
                provider_counts
            ),

        "before": {
            "provider":
                reference_score[
                    "provider"
                ],

            "type":
                reference_score[
                    "type"
                ],

            "must":
                reference_score[
                    "tier"
                ],

            "effective":
                round(
                    reference_score[
                        "effective"
                    ],
                    2,
                ),

            "hard_mismatch":
                reference_score[
                    "hard"
                ],
        },

        "after": {
            "provider":
                selected[
                    "provider"
                ],

            "type":
                selected[
                    "type"
                ],

            "must":
                selected[
                    "tier"
                ],

            "effective":
                round(
                    selected[
                        "effective"
                    ],
                    2,
                ),

            "hard_mismatch":
                selected[
                    "hard"
                ],
        },
    }


    print(
        "VSE42_POOL_SIZE="
        f"{telemetry['pool_size']}"
    )

    print(
        "VSE42_POOL_PROVIDERS="
        +
        ",".join(
            f"{k}:{v}"
            for k, v
            in sorted(
                provider_counts.items()
            )
        )
    )

    print(
        "VSE42_BEFORE="
        f"{telemetry['before']}"
    )

    print(
        "VSE42_AFTER="
        f"{telemetry['after']}"
    )

    print(
        "VSE42_OVERRIDE="
        +
        (
            "YES"
            if chosen_key != ref_key
            else "NO"
        )
    )

    print(
        "VSE42_REASON="
        f"{reason}"
    )


    return (
        chosen,
        new_pool,
        telemetry,
    )
