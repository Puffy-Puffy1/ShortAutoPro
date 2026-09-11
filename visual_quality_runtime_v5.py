#!/usr/bin/env python3

import inspect
import os

from pathlib import Path

import visual_quality_engine_v5 as E


ROOT = (
    Path.home()
    /
    "ShortAutoPro"
)


STATE = {
    "providers": [],
    "groups": [],
    "types": [],
    "keys": [],
}


LAST_CONTEXT = {}

COMMITS = {}


def enabled():

    return E.truth(
        "SAP_VQE5",
        "1",
    )


def value_from(
    bound,
    names,
    default=None,
):

    for name in names:

        if name in bound.arguments:

            value = bound.arguments[
                name
            ]

            if value is not None:
                return value

    return default


def find_name(
    signature,
    possibilities,
):

    names = set(
        signature.parameters
    )

    for name in possibilities:

        if name in names:
            return name

    return None


def context_from_bound(
    bound,
):

    query = value_from(
        bound,
        (
            "busca",
            "query",
            "consulta",
            "termo",
            "search_query",
        ),
        "",
    )


    must = value_from(
        bound,
        (
            "must_have",
            "must",
            "obrigatorios",
        ),
        [],
    )


    avoid = value_from(
        bound,
        (
            "avoid",
            "avoid_terms",
            "evitar",
        ),
        [],
    )


    return {

        "visual_query":
            query,

        "must_have":
            must,

        "avoid":
            avoid,
    }


def merge_unique(
    pools,
):

    result = []
    seen = set()

    for pool in pools:

        if not isinstance(
            pool,
            (
                list,
                tuple,
            ),
        ):
            continue


        for candidate in pool:

            key = E.candidate_key(
                candidate
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            result.append(
                candidate
            )

    return result


def clean_scene_siblings(
    destination,
):

    if not destination:
        return []


    try:

        path = Path(
            destination
        ).resolve()

    except Exception:

        return []


    try:

        relative = path.relative_to(
            ROOT.resolve()
        )

    except Exception:

        return []


    if (
        "imagens"
        not in relative.parts
    ):
        return []


    if not path.name.startswith(
        "scene_"
    ):
        return []


    removed = []

    allowed = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".mp4",
        ".mov",
        ".webm",
    }


    for sibling in path.parent.glob(
        path.stem + ".*"
    ):

        try:

            if (
                sibling.resolve()
                ==
                path
            ):
                continue


            if (
                sibling.suffix.casefold()
                not in allowed
            ):
                continue


            if sibling.is_file():

                sibling.unlink()

                removed.append(
                    str(
                        sibling
                    )
                )

        except Exception:
            pass


    return removed


def runtime_choose(
    pool,
    local_vars=None,
    fallback=None,
):

    if not enabled():

        return fallback


    local_vars = (
        local_vars
        or {}
    )


    scene = {}

    for candidate_name in (
        "scene",
        "cena",
    ):

        candidate_scene = local_vars.get(
            candidate_name
        )

        if isinstance(
            candidate_scene,
            dict,
        ):

            scene.update(
                candidate_scene
            )

            break


    aliases = {

        "texto":
            (
                "texto",
                "text",
            ),

        "visual_query":
            (
                "busca",
                "query",
                "visual_query",
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
            ),
    }


    for target, names in aliases.items():

        if scene.get(
            target
        ):
            continue


        for name in names:

            value = local_vars.get(
                name
            )

            if value:

                scene[
                    target
                ] = value

                break


    for key, value in LAST_CONTEXT.items():

        if not scene.get(
            key
        ):

            scene[
                key
            ] = value


    candidates = [
        candidate
        for candidate in (
            pool
            or []
        )
        if candidate is not None
    ]


    if not candidates:

        return fallback


    best = E.choose_best(
        candidates,
        scene,
        STATE,
    )


    if best is None:

        return fallback


    result = E.score_candidate(
        best,
        scene,
        STATE,
    )


    print(
        "VQE5_FINAL="
        f"{result['provider']}/"
        f"{result['media_type']} "
        f"must={result['must_tier']}/2 "
        f"effective={result['effective']:.1f} "
        f"hard={result['hard_mismatch']}"
    )


    if result[
        "hard_mismatch"
    ]:

        print(
            "VQE5_HARD_REASON="
            +
            result[
                "hard_reason"
            ]
        )


    return best


def install(namespace):

    global LAST_CONTEXT


    if not enabled():

        print(
            "VQE5_RUNTIME=DISABLED"
        )

        return False


    if namespace.get(
        "_SHORTAUTOPRO_VQE5_INSTALLED"
    ):

        return True


    search_name = (
        "buscar_todos_candidatos"
    )


    original_search = namespace.get(
        search_name
    )


    if callable(
        original_search
    ):

        signature = inspect.signature(
            original_search
        )


        query_name = find_name(
            signature,
            (
                "busca",
                "query",
                "consulta",
                "termo",
                "search_query",
            ),
        )


        must_name = find_name(
            signature,
            (
                "must_have",
                "must",
                "obrigatorios",
            ),
        )


        def search_wrapper(
            *args,
            **kwargs
        ):

            global LAST_CONTEXT


            bound = signature.bind_partial(
                *args,
                **kwargs
            )


            scene = context_from_bound(
                bound
            )


            LAST_CONTEXT = dict(
                scene
            )


            original_result = original_search(
                *args,
                **kwargs
            )


            if not isinstance(
                original_result,
                (
                    list,
                    tuple,
                ),
            ):

                return original_result


            all_pools = [
                original_result
            ]


            ranked = E.rerank(
                list(
                    original_result
                ),
                scene,
                STATE,
            )


            best = (
                ranked[0]
                if ranked
                else None
            )


            rescue_on = E.truth(
                "SAP_VQE5_RESCUE",
                "1",
            )


            if (
                rescue_on
                and query_name
                and E.needs_rescue(
                    best,
                    scene,
                    STATE,
                )
            ):

                query = bound.arguments.get(
                    query_name,
                    "",
                )


                must = (
                    bound.arguments.get(
                        must_name,
                        [],
                    )
                    if must_name
                    else []
                )


                try:

                    extra_count = int(
                        os.getenv(
                            "SAP_VQE5_QUERY_EXTRA",
                            "2",
                        )
                    )

                except Exception:

                    extra_count = 2


                for alternative in E.rescue_queries(
                    query,
                    must,
                    extra_count,
                ):

                    try:

                        alternative_bound = (
                            signature.bind_partial(
                                *args,
                                **kwargs
                            )
                        )


                        alternative_bound.arguments[
                            query_name
                        ] = alternative


                        extra = original_search(
                            *alternative_bound.args,
                            **alternative_bound.kwargs
                        )


                        if isinstance(
                            extra,
                            (
                                list,
                                tuple,
                            ),
                        ):

                            all_pools.append(
                                extra
                            )

                            print(
                                "VQE5_RESCUE_QUERY="
                                +
                                alternative
                            )

                    except Exception as exc:

                        print(
                            "VQE5_RESCUE_FAIL_OPEN="
                            +
                            type(
                                exc
                            ).__name__
                        )


            merged = merge_unique(
                all_pools
            )


            ranked = E.rerank(
                merged,
                scene,
                STATE,
            )


            print(
                "VQE5_POOL="
                f"{len(merged)}"
            )


            if isinstance(
                original_result,
                tuple,
            ):

                return tuple(
                    ranked
                )

            return ranked


        namespace[
            search_name
        ] = search_wrapper


    order_name = (
        "ordenar_failover_5_2"
    )


    original_order = namespace.get(
        order_name
    )


    if callable(
        original_order
    ):

        def order_wrapper(
            *args,
            **kwargs
        ):

            result = original_order(
                *args,
                **kwargs
            )


            if not isinstance(
                result,
                (
                    list,
                    tuple,
                ),
            ):

                return result


            ranked = E.rerank(
                list(
                    result
                ),
                LAST_CONTEXT,
                STATE,
            )


            if isinstance(
                result,
                tuple,
            ):

                return tuple(
                    ranked
                )

            return ranked


        namespace[
            order_name
        ] = order_wrapper


    download_name = (
        "baixar_candidato_5_2"
    )


    original_download = namespace.get(
        download_name
    )


    if callable(
        original_download
    ):

        signature = inspect.signature(
            original_download
        )


        scene_name = find_name(
            signature,
            (
                "numero",
                "numero_cena",
                "scene_num",
                "scene_number",
                "indice",
                "idx",
            ),
        )


        candidate_name = find_name(
            signature,
            (
                "candidato",
                "candidate",
                "item",
            ),
        )


        def download_wrapper(
            *args,
            **kwargs
        ):

            bound = signature.bind_partial(
                *args,
                **kwargs
            )


            scene_number = (
                bound.arguments.get(
                    scene_name
                )
                if scene_name
                else None
            )


            candidate = (
                bound.arguments.get(
                    candidate_name
                )
                if candidate_name
                else None
            )


            sid = os.getenv(
                "SHORT_ID",
                "",
            )


            commit_key = (
                f"{sid}:{scene_number}"
                if scene_number
                is not None
                else None
            )


            commit_enabled = E.truth(
                "SAP_VQE5_COMMIT",
                "1",
            )


            if (
                commit_enabled
                and commit_key
                and commit_key in COMMITS
            ):

                print(
                    "VQE5_COMMIT_BLOCKED "
                    f"scene={scene_number}"
                )

                return (
                    False,
                    None,
                )


            result = original_download(
                *args,
                **kwargs
            )


            success = False
            destination = None


            if isinstance(
                result,
                tuple,
            ):

                if result:

                    success = bool(
                        result[0]
                    )

                if len(
                    result
                ) >= 2:

                    destination = result[
                        1
                    ]

            else:

                success = bool(
                    result
                )


            if success:

                if (
                    commit_enabled
                    and commit_key
                ):

                    COMMITS[
                        commit_key
                    ] = E.candidate_key(
                        candidate
                    )


                if candidate is not None:

                    E.note_success(
                        STATE,
                        candidate,
                    )


                removed = clean_scene_siblings(
                    destination
                )


                print(
                    "VQE5_COMMIT="
                    f"scene={scene_number} "
                    f"removed_siblings="
                    f"{len(removed)}"
                )


            return result


        namespace[
            download_name
        ] = download_wrapper


    namespace[
        "_SHORTAUTOPRO_VQE5_INSTALLED"
    ] = True


    print(
        "VQE5_RUNTIME=INSTALLED"
    )

    return True
