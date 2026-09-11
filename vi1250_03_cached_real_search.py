#!/usr/bin/env python3

import hashlib
import json
import time

from pathlib import Path


from vi1200_02_commons_provider import (
    search as commons_search,
)

from vi1200_03_archive_provider import (
    search as archive_search,
)


BASE = (
    Path.home()
    / "ShortAutoPro"
)

CACHE = (
    BASE
    / "temp/vi1250/cache"
)


def key_for(
    provider,
    query
):
    raw = (
        str(provider)
        + "\n"
        + str(query)
    )

    return hashlib.sha256(
        raw.encode(
            "utf-8"
        )
    ).hexdigest()


def cache_path(
    provider,
    query
):
    return (
        CACHE
        / (
            str(provider).lower()
            + "_"
            + key_for(
                provider,
                query
            )
            + ".json"
        )
    )


def read_cache(
    provider,
    query
):
    path = cache_path(
        provider,
        query
    )


    if not path.exists():
        return None


    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return None


    data[
        "_from_cache"
    ] = True


    return data


def save_cache(
    provider,
    query,
    data
):
    CACHE.mkdir(
        parents=True,
        exist_ok=True
    )


    path = cache_path(
        provider,
        query
    )


    payload = dict(
        data
    )


    payload[
        "_from_cache"
    ] = False


    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def cached_commons(
    query
):
    cached = read_cache(
        "commons",
        query
    )


    if cached is not None:
        return cached


    result = commons_search(
        query,
        limit=5
    )


    save_cache(
        "commons",
        query,
        result
    )


    time.sleep(
        0.12
    )


    return result


def cached_archive(
    query
):
    cached = read_cache(
        "archive",
        query
    )


    if cached is not None:
        return cached


    result = archive_search(
        query,
        limit=4
    )


    save_cache(
        "archive",
        query,
        result
    )


    time.sleep(
        0.12
    )


    return result


def unique_raw(
    values
):
    result = []

    seen = set()


    for raw in values:

        key = (
            raw.get(
                "provider"
            ),
            raw.get(
                "pageid"
            )
            or
            raw.get(
                "identifier"
            )
            or
            raw.get(
                "title"
            ),
        )


        if key in seen:
            continue


        seen.add(
            key
        )

        result.append(
            raw
        )


    return result


def run_expanded_search(
    queries,
    *,
    use_archive=False,
    max_archive_queries=6,
):
    raw = []

    calls = []


    for index, query in enumerate(
        queries
    ):

        commons = cached_commons(
            query
        )


        calls.append({
            "provider":
                "WIKIMEDIA_COMMONS",

            "query":
                query,

            "ok":
                commons.get(
                    "ok",
                    False
                ),

            "count":
                commons.get(
                    "count",
                    0
                ),

            "from_cache":
                commons.get(
                    "_from_cache",
                    False
                ),
        })


        if commons.get(
            "ok"
        ):
            raw.extend(
                commons.get(
                    "results",
                    []
                )
            )


        if (
            use_archive
            and
            index
            <
            max_archive_queries
        ):

            archive = cached_archive(
                query
            )


            calls.append({
                "provider":
                    "INTERNET_ARCHIVE",

                "query":
                    query,

                "ok":
                    archive.get(
                        "ok",
                        False
                    ),

                "count":
                    archive.get(
                        "count",
                        0
                    ),

                "from_cache":
                    archive.get(
                        "_from_cache",
                        False
                    ),
            })


            if archive.get(
                "ok"
            ):
                raw.extend(
                    archive.get(
                        "results",
                        []
                    )
                )


    return {
        "queries":
            queries,

        "calls":
            calls,

        "results":
            unique_raw(
                raw
            ),

        "unique_results":
            len(
                unique_raw(
                    raw
                )
            ),
    }


def health(
    records
):
    calls = [
        item
        for record in records
        for item in (
            record.get(
                "calls"
            )
            or []
        )
    ]


    fresh = [
        item
        for item in calls
        if not item[
            "from_cache"
        ]
    ]


    cached = [
        item
        for item in calls
        if item[
            "from_cache"
        ]
    ]


    succeeded = sum(
        1
        for item in calls
        if item[
            "ok"
        ]
    )


    return {
        "calls":
            len(
                calls
            ),

        "fresh_calls":
            len(
                fresh
            ),

        "cached_calls":
            len(
                cached
            ),

        "successful_calls":
            succeeded,

        "success_ratio":
            round(
                (
                    succeeded
                    /
                    len(
                        calls
                    )
                )
                if calls
                else 0.0,
                3
            ),
    }


if __name__ == "__main__":
    print(
        "VI1250 CACHED SEARCH=PASS"
    )
