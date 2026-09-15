#!/usr/bin/env python3

from collections import Counter

import visual_selection_engine_v4 as vse


def wrap_search(fn):

    if getattr(
        fn,
        "_vse42_provider_observer",
        False,
    ):
        return fn


    def wrapped(*args, **kwargs):

        result = fn(
            *args,
            **kwargs
        )

        candidates = [
            x
            for x in vse.flatten_candidates(
                result
            )
            if isinstance(x, dict)
        ]

        counts = Counter(
            vse.provider(x)
            for x in candidates
        )

        summary = ",".join(
            f"{provider}:{count}"
            for provider, count
            in sorted(
                counts.items()
            )
        )

        print(
            "VSE42_PROVIDER_POOL="
            +
            (
                summary
                or "EMPTY"
            )
        )


        for expected in (
            "pexels",
            "pixabay",
            "coverr",
            "wikimedia",
        ):

            if counts.get(
                expected,
                0,
            ) == 0:

                print(
                    "VSE42_PROVIDER_ZERO="
                    + expected
                )


        return result


    wrapped._vse42_provider_observer = True

    wrapped.__name__ = getattr(
        fn,
        "__name__",
        "wrapped_search",
    )

    return wrapped
