#!/usr/bin/env python3

import inspect
import os

from visual_query_planner_v4 import (
    expansion_queries,
)

try:

    from visual_selection_engine_v4 import (
        candidate_key,
        flatten_candidates,
    )

except Exception:

    candidate_key = None
    flatten_candidates = None


def _dedupe(items):

    result = []
    seen = set()

    for candidate in items:

        try:

            key = (
                candidate_key(candidate)
                if candidate_key
                else repr(candidate)
            )

        except Exception:

            key = repr(candidate)

        if key in seen:
            continue

        seen.add(key)
        result.append(candidate)

    return result


def wrap_search_function(
    fn,
):

    if getattr(
        fn,
        "_vse42_query_expanded",
        False,
    ):
        return fn

    signature = inspect.signature(
        fn
    )

    params = list(
        signature.parameters
    )

    query_name = None

    for name in params:

        lname = name.casefold()

        if any(
            token in lname
            for token in (
                "busca",
                "query",
                "search",
                "termo",
                "pesquisa",
            )
        ):
            query_name = name
            break


    def wrapped(
        *args,
        **kwargs
    ):

        primary = fn(
            *args,
            **kwargs
        )

        if (
            os.getenv(
                "SAP_VSE4_QUERY_EXPANSION",
                "1",
            )
            !=
            "1"
        ):
            return primary


        if query_name is None:
            return primary


        try:

            bound = signature.bind_partial(
                *args,
                **kwargs
            )

            query = bound.arguments.get(
                query_name
            )

        except Exception:

            return primary


        if not isinstance(
            query,
            str,
        ):
            return primary


        plans = expansion_queries(
            query,
            max_extra=int(
                os.getenv(
                    "SAP_VSE4_QUERY_EXTRA",
                    "2",
                )
            ),
        )


        if len(plans) <= 1:
            return primary


        # Preserve return type.
        if not isinstance(
            primary,
            (
                list,
                tuple,
            ),
        ):
            return primary


        merged = list(primary)


        for alt in plans[1:]:

            try:

                alt_bound = signature.bind_partial(
                    *args,
                    **kwargs
                )

                alt_bound.arguments[
                    query_name
                ] = alt


                extra = fn(
                    *alt_bound.args,
                    **alt_bound.kwargs
                )


                if isinstance(
                    extra,
                    (
                        list,
                        tuple,
                    ),
                ):

                    merged.extend(
                        extra
                    )


                print(
                    "VSE42_QUERY_EXPANSION="
                    f"{alt}"
                )


            except Exception as exc:

                print(
                    "VSE42_QUERY_EXPANSION_FAIL_OPEN="
                    f"{type(exc).__name__}:"
                    f"{exc}"
                )


        merged = _dedupe(
            merged
        )


        print(
            "VSE42_EXPANDED_POOL="
            f"{len(merged)}"
        )


        if isinstance(
            primary,
            tuple,
        ):
            return tuple(
                merged
            )

        return merged


    wrapped._vse42_query_expanded = True
    wrapped.__name__ = getattr(
        fn,
        "__name__",
        "wrapped_search",
    )

    return wrapped
