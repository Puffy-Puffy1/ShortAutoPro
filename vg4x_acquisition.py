#!/usr/bin/env python3

import functools
import inspect
import os

from vg4x_common import (
    candidate_key,
    concept_hits,
    dedupe_candidates,
    flatten_candidates,
    norm,
    provider,
)


CONCEPT_QUERY = {
    "police":
        "police investigation documentary",

    "investigation":
        "police investigation evidence",

    "crime_scene":
        "crime scene investigation",

    "evidence":
        "forensic evidence investigation",

    "forensics":
        "forensic investigation laboratory",

    "court":
        "courtroom courthouse justice",

    "apartment":
        "apartment building exterior",

    "building":
        "building exterior documentary",

    "city":
        "city documentary street",

    "hospital":
        "hospital emergency documentary",

    "laboratory":
        "laboratory scientist research",

    "aircraft":
        "aircraft aviation documentary",

    "war":
        "historical war documentary",

    "military":
        "military documentary",

    "space":
        "space astronomy documentary",

    "ocean":
        "ocean documentary",
}


def _bound_arguments(
    function,
    args,
    kwargs,
):

    try:
        return inspect.signature(
            function
        ).bind_partial(
            *args,
            **kwargs,
        ).arguments
    except Exception:
        return {}


def rescue_query(
    busca,
    must_have,
):

    raw = " ".join(
        [
            str(busca or ""),
            *[
                str(x)
                for x in (
                    must_have
                    if isinstance(
                        must_have,
                        (list, tuple, set),
                    )
                    else [must_have]
                )
                if x
            ],
        ]
    )

    concepts = concept_hits(
        raw
    )

    parts = []

    for concept in sorted(concepts):

        term = CONCEPT_QUERY.get(
            concept
        )

        if term:
            parts.append(term)

    # Mantém nomes/lugares da busca original.
    original = norm(
        busca
    )

    if original:
        parts.append(
            original
        )

    result = " ".join(parts)

    # evita query gigantesca
    return result[:180].strip()


def install(namespace):

    if (
        os.getenv(
            "SAP_VG4X_ACQUISITION",
            "1",
        )
        ==
        "0"
    ):
        return {
            "installed": False,
            "reason": "DISABLED",
        }

    original = namespace.get(
        "buscar_todos_candidatos"
    )

    if not callable(original):
        return {
            "installed": False,
            "reason":
                "buscar_todos_candidatos_missing",
        }

    if getattr(
        original,
        "_vg4x_wrapped",
        False,
    ):
        return {
            "installed": True,
            "reason": "ALREADY",
        }

    providers = {
        name:
            namespace.get(name)

        for name in (
            "pexels_video",
            "pexels_foto",
            "coverr_video",
            "pixabay_video",
            "pixabay_foto",
        )
    }

    @functools.wraps(original)
    def wrapped(
        *args,
        **kwargs,
    ):

        result = original(
            *args,
            **kwargs,
        )

        if not isinstance(
            result,
            list,
        ):
            return result

        pool = dedupe_candidates(
            flatten_candidates(
                result
            )
        )

        bound = _bound_arguments(
            original,
            args,
            kwargs,
        )

        busca = (
            bound.get("busca")
            or bound.get("query")
            or ""
        )

        must_have = (
            bound.get("must_have")
            or []
        )

        avoid = (
            bound.get("avoid")
            or []
        )

        counts = {}

        for candidate in pool:
            p = provider(candidate)

            counts[p] = (
                counts.get(p, 0)
                +
                1
            )

        if pool:

            max_share = (
                max(counts.values())
                /
                len(pool)
            )

        else:
            max_share = 1.0

        need_rescue = (
            len(pool) < 18
            or len(counts) <= 1
            or max_share >= 0.88
        )

        if not need_rescue:
            return pool

        query = rescue_query(
            busca,
            must_have,
        )

        if not query:
            return pool

        if (
            norm(query)
            ==
            norm(busca)
            and len(pool) >= 12
        ):
            return pool

        print(
            "VG4X_ACQUISITION_RESCUE=START "
            f"pool={len(pool)} "
            f"providers={counts} "
            f"query={query!r}"
        )

        try:
            max_calls = int(
                os.getenv(
                    "SAP_VG4X_RESCUE_CALLS",
                    "4",
                )
            )
        except ValueError:
            max_calls = 4

        calls = 0

        preferred = (
            "pexels_video",
            "pexels_foto",
            "coverr_video",
            "pixabay_video",
            "pixabay_foto",
        )

        for name in preferred:

            if calls >= max_calls:
                break

            fn = providers.get(name)

            if not callable(fn):
                continue

            p_name = (
                "pexels"
                if name.startswith("pexels")
                else
                "coverr"
                if name.startswith("coverr")
                else
                "pixabay"
            )

            # Prioriza provedores ausentes.
            if (
                counts.get(p_name, 0)
                > 0
                and len(pool) >= 24
            ):
                continue

            try:

                extra = fn(
                    query,
                    must_have,
                    avoid,
                )

                calls += 1

                new_items = flatten_candidates(
                    extra
                )

                before = len(pool)

                pool = dedupe_candidates(
                    pool
                    +
                    new_items
                )

                gained = (
                    len(pool)
                    -
                    before
                )

                print(
                    "VG4X_PROVIDER_RESCUE "
                    f"provider={name} "
                    f"gained={gained}"
                )

            except Exception as exc:

                print(
                    "VG4X_PROVIDER_RESCUE_FAIL_OPEN "
                    f"provider={name} "
                    f"error={type(exc).__name__}:"
                    f"{exc}"
                )

        print(
            "VG4X_ACQUISITION_RESCUE=END "
            f"pool={len(pool)}"
        )

        return pool

    wrapped._vg4x_wrapped = True

    namespace[
        "buscar_todos_candidatos"
    ] = wrapped

    return {
        "installed": True,
        "reason": "OK",
    }
