#!/usr/bin/env python3

import inspect
import os
import re
from collections import Counter

from visual_selection_engine_v4 import (
    candidate_key,
    candidate_text,
    flatten_candidates,
    media_type,
    must_tier,
    norm,
    provider,
    score_candidate,
    source_group,
)


ENABLED = (
    os.getenv(
        "SAP_VSE_V42",
        "1",
    )
    !=
    "0"
)


STATE = {
    "providers": [],
    "groups": [],
    "types": [],
    "keys": [],
}


TRANSLATE = {
    "apartamento": "apartment",
    "predio": "building",
    "edificio": "building",
    "fachada": "building exterior",
    "policia": "police",
    "policial": "police officer",
    "investigacao": "investigation",
    "investigar": "investigation",
    "crime": "crime",
    "cena do crime": "crime scene",
    "tribunal": "court",
    "julgamento": "court trial",
    "juiz": "judge",
    "pericia": "forensic",
    "pericial": "forensic",
    "laudo": "forensic report",
    "evidencia": "evidence",
    "evidencias": "evidence",
    "indicio": "evidence",
    "indicios": "evidence",
    "documento": "document",
    "documentos": "documents",
    "hospital": "hospital",
    "ambulancia": "ambulance",
    "cidade": "city",
    "rua": "street",
    "casa": "house",
    "quarto": "room",
    "familia": "family",
    "pai": "father",
    "mae": "mother",
    "crianca": "child",
    "menina": "girl",
    "menino": "boy",
    "carro": "car",
    "moto": "motorcycle",
    "aviao": "airplane",
    "navio": "ship",
    "laboratorio": "laboratory",
    "cientista": "scientist",
    "computador": "computer",
    "tecnologia": "technology",
    "dinheiro": "money",
    "guerra": "war",
    "soldado": "soldier",
    "floresta": "forest",
    "oceano": "ocean",
    "tempestade": "storm",
    "espaco": "space",
    "foguete": "rocket",
}


def _safe_list(value):

    if value is None:
        return []

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return list(value)

    return [value]


def _scene_context(local_ctx):

    keys = (
        "texto",
        "text",
        "segmento",
        "scene",
        "cena",
        "busca",
        "visual_query",
        "must_have",
        "avoid",
        "location",
        "local",
        "tema",
        "topic",
        "visual_mode",
        "descricao",
        "description",
    )

    scene = {}

    for key in keys:

        if key not in local_ctx:
            continue

        value = local_ctx.get(
            key
        )

        if value is None:
            continue

        scene[
            key
        ] = value


    # Alguns pipelines usam segmento como dict.
    segmento = local_ctx.get(
        "segmento"
    )

    if isinstance(
        segmento,
        dict,
    ):

        for key, value in segmento.items():

            if (
                key not in scene
                and value is not None
            ):
                scene[
                    key
                ] = value


    return scene


def _dedup(candidates):

    output = []
    seen = set()

    for candidate in flatten_candidates(
        candidates
    ):

        if candidate is None:
            continue

        try:
            key = candidate_key(
                candidate
            )
        except Exception:
            key = repr(
                candidate
            )

        if key in seen:
            continue

        seen.add(
            key
        )

        output.append(
            candidate
        )

    return output


def _safe_score(candidate, scene):

    try:

        result = score_candidate(
            candidate,
            scene,
            STATE,
        )

        if not isinstance(
            result,
            dict,
        ):
            result = {
                "effective": 0.0,
                "hard_mismatch": False,
            }

    except Exception as exc:

        result = {
            "effective": -999999.0,
            "hard_mismatch": False,
            "runtime_error":
                f"{type(exc).__name__}: {exc}",
        }


    try:
        tier = must_tier(
            candidate,
            scene,
        )
    except Exception:
        tier = 0


    result[
        "_must_tier"
    ] = int(
        tier or 0
    )

    result[
        "_provider"
    ] = provider(
        candidate
    )

    result[
        "_group"
    ] = source_group(
        candidate
    )

    result[
        "_type"
    ] = media_type(
        candidate
    )

    result[
        "_candidate"
    ] = candidate

    return result


def _effective(result):

    try:
        return float(
            result.get(
                "effective",
                0.0,
            )
        )
    except Exception:
        return 0.0


def _provider_summary(candidates):

    counts = Counter()

    for candidate in candidates:

        try:
            p = provider(
                candidate
            )
        except Exception:
            p = "unknown"

        counts[
            p
        ] += 1


    return ",".join(
        f"{name}:{count}"
        for name, count
        in sorted(
            counts.items()
        )
    ) or "empty"


def _translated(text):

    result = norm(
        text
    )

    for source, target in sorted(
        TRANSLATE.items(),
        key=lambda item:
            len(item[0]),
        reverse=True,
    ):

        source_n = norm(
            source
        )

        pattern = (
            r"\b"
            +
            re.escape(source_n)
            +
            r"\b"
        )

        result = re.sub(
            pattern,
            target,
            result,
        )

    return " ".join(
        result.split()
    )


def _rescue_queries(scene, local_ctx):

    must = _safe_list(
        local_ctx.get(
            "must_have",
            scene.get(
                "must_have",
                [],
            ),
        )
    )

    location = (
        local_ctx.get(
            "location"
        )
        or
        scene.get(
            "location"
        )
        or
        ""
    )

    visual_query = (
        local_ctx.get(
            "visual_query"
        )
        or
        scene.get(
            "visual_query"
        )
        or
        local_ctx.get(
            "busca"
        )
        or
        scene.get(
            "busca"
        )
        or
        ""
    )


    must_text = " ".join(
        str(x)
        for x in must
        if x
    )


    candidates = []


    q1 = _translated(
        " ".join(
            x
            for x in (
                must_text,
                str(location),
            )
            if x
        )
    )

    if q1:
        candidates.append(
            q1
        )


    q2 = _translated(
        " ".join(
            x
            for x in (
                str(visual_query),
                must_text,
            )
            if x
        )
    )

    if q2:
        candidates.append(
            q2
        )


    clean = []
    seen = set()

    for query in candidates:

        query = " ".join(
            query.split()
        ).strip()

        if not query:
            continue

        key = query.casefold()

        if key in seen:
            continue

        seen.add(
            key
        )

        clean.append(
            query
        )


    return clean[:2]


def _call_search(
    search_fn,
    query,
    local_ctx,
):

    try:

        signature = inspect.signature(
            search_fn
        )

    except Exception as exc:

        print(
            "VSE42_RESCUE_CALL=FAIL "
            f"signature={type(exc).__name__}"
        )

        return []


    kwargs = {}


    for name, param in signature.parameters.items():

        lname = name.casefold()


        if lname in {
            "busca",
            "query",
            "q",
            "visual_query",
            "search",
        }:

            kwargs[
                name
            ] = query

            continue


        if name in local_ctx:

            kwargs[
                name
            ] = local_ctx[
                name
            ]

            continue


        aliases = {

            "must_have":
                (
                    "must_have",
                    []
                ),

            "avoid":
                (
                    "avoid",
                    []
                ),

            "visual_mode":
                (
                    "visual_mode",
                    None
                ),

            "segmento":
                (
                    "segmento",
                    None
                ),

            "rota_fonte":
                (
                    "rota_fonte",
                    None
                ),
        }


        if lname in aliases:

            source_name, fallback = aliases[
                lname
            ]

            value = local_ctx.get(
                source_name,
                fallback,
            )

            if (
                value is not None
                or
                param.default
                is inspect.Parameter.empty
            ):

                kwargs[
                    name
                ] = value

            continue


        if (
            param.default
            is not
            inspect.Parameter.empty
        ):
            continue


        print(
            "VSE42_RESCUE_CALL=SKIP "
            f"missing_param={name}"
        )

        return []


    try:

        result = search_fn(
            **kwargs
        )

    except Exception as exc:

        print(
            "VSE42_RESCUE_CALL=FAIL "
            f"{type(exc).__name__}: {exc}"
        )

        return []


    return _dedup(
        result
    )


def _choose(
    reference,
    candidates,
    scene,
):

    pool = _dedup(
        [
            reference,
            candidates,
        ]
    )


    scored = [
        _safe_score(
            candidate,
            scene,
        )
        for candidate in pool
    ]


    safe = [
        result
        for result in scored
        if not result.get(
            "hard_mismatch",
            False,
        )
    ]


    reference_result = None

    ref_key = None

    try:
        ref_key = candidate_key(
            reference
        )
    except Exception:
        pass


    for result in scored:

        try:
            key = candidate_key(
                result[
                    "_candidate"
                ]
            )
        except Exception:
            key = None

        if key == ref_key:
            reference_result = result
            break


    if reference_result is None:

        reference_result = _safe_score(
            reference,
            scene,
        )


    if not safe:

        return (
            reference,
            pool,
            reference_result,
            "NO_SAFE_ALTERNATIVE",
        )


    best = max(
        safe,
        key=lambda result:
            (
                _effective(
                    result
                ),
                result.get(
                    "_must_tier",
                    0,
                ),
            ),
    )


    best_candidate = best[
        "_candidate"
    ]


    ref_hard = bool(
        reference_result.get(
            "hard_mismatch",
            False,
        )
    )

    ref_must = int(
        reference_result.get(
            "_must_tier",
            0,
        )
    )

    best_must = int(
        best.get(
            "_must_tier",
            0,
        )
    )

    ref_eff = _effective(
        reference_result
    )

    best_eff = _effective(
        best
    )


    # 1. Contradição forte sempre perde para candidato seguro.
    if ref_hard:

        return (
            best_candidate,
            pool,
            best,
            "HARD_MISMATCH_REPLACED",
        )


    # 2. Nunca derruba MUST por pequena diferença de score.
    if best_must < ref_must:

        return (
            reference,
            pool,
            reference_result,
            "PRESERVE_HIGHER_MUST",
        )


    # 3. Ganho de MUST com score ainda competitivo.
    if (
        best_must > ref_must
        and
        best_eff
        >=
        ref_eff - 12.0
    ):

        return (
            best_candidate,
            pool,
            best,
            "MUST_UPGRADE",
        )


    # 4. Mesmo tier: precisa melhoria real.
    if (
        best_must == ref_must
        and
        best_eff
        >=
        ref_eff + 8.0
    ):

        return (
            best_candidate,
            pool,
            best,
            "SEMANTIC_UPGRADE",
        )


    return (
        reference,
        pool,
        reference_result,
        "REFERENCE_PRESERVED",
    )


def enhance_selection(
    reference,
    candidates,
    local_ctx,
    search_fn=None,
):

    if not ENABLED:

        return (
            reference,
            _dedup(
                candidates
            ),
            {
                "enabled": False,
                "reason":
                    "DISABLED",
            },
        )


    scene = _scene_context(
        local_ctx
    )


    initial_pool = _dedup(
        candidates
    )


    print(
        "VSE42_POOL_PROVIDERS="
        +
        _provider_summary(
            initial_pool
        )
    )


    chosen, pool, result, reason = _choose(
        reference,
        initial_pool,
        scene,
    )


    chosen_must = int(
        result.get(
            "_must_tier",
            0,
        )
    )

    chosen_hard = bool(
        result.get(
            "hard_mismatch",
            False,
        )
    )


    rescue_attempted = False
    rescue_added = 0


    if (
        search_fn is not None
        and
        (
            chosen_must < 2
            or
            chosen_hard
        )
    ):

        queries = _rescue_queries(
            scene,
            local_ctx,
        )


        if queries:

            rescue_attempted = True

            print(
                "VSE42_MUST_RESCUE=START "
                f"must={chosen_must}/2"
            )


        expanded = list(
            pool
        )


        for query in queries:

            print(
                "VSE42_RESCUE_QUERY="
                +
                query
            )


            fresh = _call_search(
                search_fn,
                query,
                local_ctx,
            )


            print(
                "VSE42_RESCUE_POOL_PROVIDERS="
                +
                _provider_summary(
                    fresh
                )
            )


            before = len(
                _dedup(
                    expanded
                )
            )


            expanded.extend(
                fresh
            )

            expanded = _dedup(
                expanded
            )


            rescue_added += (
                len(expanded)
                -
                before
            )


        if rescue_added > 0:

            new_chosen, new_pool, new_result, new_reason = _choose(
                chosen,
                expanded,
                scene,
            )


            old_must = int(
                result.get(
                    "_must_tier",
                    0,
                )
            )

            new_must = int(
                new_result.get(
                    "_must_tier",
                    0,
                )
            )


            if (
                new_must > old_must
                or
                new_result.get(
                    "hard_mismatch",
                    False,
                )
                is False
                and
                result.get(
                    "hard_mismatch",
                    False,
                )
                is True
                or
                (
                    new_must == old_must
                    and
                    _effective(
                        new_result
                    )
                    >=
                    _effective(
                        result
                    )
                    + 8.0
                )
            ):

                chosen = new_chosen
                pool = new_pool
                result = new_result
                reason = (
                    "RESCUE_"
                    +
                    new_reason
                )


    try:

        p = provider(
            chosen
        )

        t = media_type(
            chosen
        )

    except Exception:

        p = "unknown"
        t = "unknown"


    print(
        "VSE42_FINAL="
        f"{p}/{t} "
        f"must={result.get('_must_tier', 0)}/2 "
        f"effective={_effective(result):.1f} "
        f"hard={result.get('hard_mismatch', False)}"
    )

    print(
        "VSE42_REASON="
        +
        reason
    )

    print(
        "VSE42_RESCUE_ATTEMPTED="
        +
        (
            "YES"
            if rescue_attempted
            else
            "NO"
        )
    )

    print(
        "VSE42_RESCUE_ADDED="
        +
        str(
            rescue_added
        )
    )


    return (
        chosen,
        _dedup(
            pool
        ),
        {
            "enabled":
                True,

            "reason":
                reason,

            "must_tier":
                result.get(
                    "_must_tier",
                    0,
                ),

            "hard_mismatch":
                result.get(
                    "hard_mismatch",
                    False,
                ),

            "effective":
                _effective(
                    result
                ),

            "provider":
                p,

            "media_type":
                t,

            "pool_providers":
                _provider_summary(
                    pool
                ),

            "rescue_attempted":
                rescue_attempted,

            "rescue_added":
                rescue_added,
        },
    )


def note_commit(
    candidate,
    local_ctx=None,
):

    try:

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


        STATE[
            "providers"
        ].append(
            p
        )

        STATE[
            "groups"
        ].append(
            g
        )

        STATE[
            "types"
        ].append(
            t
        )

        STATE[
            "keys"
        ].append(
            k
        )


        for key in (
            "providers",
            "groups",
            "types",
            "keys",
        ):

            STATE[
                key
            ] = STATE[
                key
            ][-24:]


        print(
            "VSE42_COMMIT="
            f"{p}/{t}"
        )

        print(
            "VSE42_HISTORY_PROVIDERS="
            +
            ",".join(
                STATE[
                    "providers"
                ]
            )
        )

        return True


    except Exception as exc:

        print(
            "VSE42_COMMIT=FAIL "
            f"{type(exc).__name__}: {exc}"
        )

        return False


def reset_state():

    for key in STATE:
        STATE[
            key
        ].clear()


def self_test():

    reset_state()


    scene = {
        "texto":
            "Investigação em apartamento "
            "na cidade de São Paulo",

        "must_have": [
            "apartamento",
            "São Paulo",
        ],

        "location":
            "São Paulo Brazil",
    }


    wrong = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "Empire State Building "
            "New York Manhattan",

        "must":
            "2/2",

        "score":
            220,

        "width":
            1920,

        "height":
            1080,
    }


    correct = {
        "provider":
            "Wikimedia",

        "tipo":
            "foto",

        "title":
            "Apartment building "
            "Sao Paulo Brazil",

        "must":
            "1/2",

        "score":
            120,

        "width":
            1920,

        "height":
            1080,
    }


    chosen, pool, meta = enhance_selection(
        wrong,
        [
            wrong,
            correct,
        ],
        scene,
        None,
    )


    assert (
        candidate_key(
            chosen
        )
        ==
        candidate_key(
            correct
        )
    )

    assert (
        meta[
            "hard_mismatch"
        ]
        is False
    )


    note_commit(
        chosen
    )


    assert (
        STATE[
            "providers"
        ]
        ==
        [
            "wikimedia"
        ]
    )


    print(
        "VSE42_RUNTIME_SELF_TEST=PASS"
    )


if __name__ == "__main__":
    self_test()
