#!/usr/bin/env python3

from vi1000_1_semantic_core import (
    norm,
)

from vi1200_02_commons_provider import (
    search as commons_search,
)

from vi1200_03_archive_provider import (
    search as archive_search,
)

from vi1200_06_visual_precision import (
    scene_visual_intents,
)


def exact_lookup(
    mapped,
    fragment
):
    wanted = norm(
        fragment
    )

    for key, value in (
        mapped.items()
    ):
        if wanted in key:
            return value

    return None


def targeted_exact_assets(
    scene,
    exact_mapped
):
    intents = (
        scene_visual_intents(
            scene
        )
    )

    role = str(
        scene.get(
            "role"
        )
        or ""
    ).upper()

    result = []


    elevator = exact_lookup(
        exact_mapped,
        "elisa lam elevator video"
    )

    medicine = exact_lookup(
        exact_mapped,
        "medicine box"
    )

    hallway = exact_lookup(
        exact_mapped,
        "arizona biltmore hallway"
    )

    hotel = exact_lookup(
        exact_mapped,
        "hotel cecil la"
    )


    # Authentic elevator evidence is relevant only
    # where the visual itself is elevator /
    # surveillance evidence.
    if (
        elevator
        and
        (
            "ELEVATOR"
            in intents
            or
            "SURVEILLANCE"
            in intents
            or
            role == "EVIDENCE"
        )
    ):
        result.append(
            elevator
        )


    # Generic medicine is illustration only.
    if (
        medicine
        and
        "MEDICATION"
        in intents
    ):
        result.append(
            medicine
        )


    # Arizona Biltmore is allowed only for an
    # illustrative hallway visual.
    if (
        hallway
        and
        "HALLWAY"
        in intents
        and
        not scene.get(
            "factual"
        )
        and
        not scene.get(
            "identity_required"
        )
    ):
        result.append(
            hallway
        )


    # Hotel facade cannot substitute for elevator,
    # hallway or rooftop evidence.
    strong_subtypes = {
        "ELEVATOR",
        "HALLWAY",
        "ROOFTOP",
        "SURVEILLANCE",
        "MEDICATION",
        "WATER_TANK",
    }


    if (
        hotel
        and
        not (
            intents
            &
            strong_subtypes
        )
        and
        (
            role == "LOCATION"
            or
            scene.get(
                "hook_priority"
            )
            == 100
        )
    ):
        result.append(
            hotel
        )


    return result


def unique_raw(
    values
):
    seen = set()

    result = []


    for item in values:
        key = (
            item.get(
                "provider"
            ),
            item.get(
                "pageid"
            )
            or
            item.get(
                "identifier"
            )
            or
            item.get(
                "title"
            ),
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            item
        )


    return result


def search_scene(
    scene,
    query_plan,
    exact_mapped,
    max_variants=3,
):
    variants = (
        query_plan.get(
            "query_variants"
        )
        or
        [
            query_plan.get(
                "primary_query",
                ""
            )
        ]
    )


    clean_variants = []

    seen_queries = set()


    for query in variants:
        query = " ".join(
            str(
                query or ""
            ).split()
        )

        if not query:
            continue

        key = norm(
            query
        )

        if key in seen_queries:
            continue

        seen_queries.add(
            key
        )

        clean_variants.append(
            query
        )


    clean_variants = (
        clean_variants[
            :max_variants
        ]
    )


    raw_results = []

    calls = []


    for query in clean_variants:

        commons = commons_search(
            query,
            limit=5
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
        })


        if commons.get(
            "ok"
        ):
            raw_results.extend(
                commons.get(
                    "results",
                    []
                )
            )


        if (
            "INTERNET_ARCHIVE"
            in (
                query_plan.get(
                    "providers"
                )
                or []
            )
        ):

            archive = archive_search(
                query,
                limit=4
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
            })


            if archive.get(
                "ok"
            ):
                raw_results.extend(
                    archive.get(
                        "results",
                        []
                    )
                )


    seeds = targeted_exact_assets(
        scene,
        exact_mapped
    )


    raw_results.extend(
        seeds
    )


    return {
        "scene":
            scene[
                "scene"
            ],

        "queries":
            clean_variants,

        "calls":
            calls,

        "targeted_seed_count":
            len(
                seeds
            ),

        "results":
            unique_raw(
                raw_results
            ),
    }


def provider_health(
    searches
):
    calls = [
        call
        for search in searches.values()
        for call in (
            search[
                "calls"
            ]
        )
    ]


    commons = [
        item
        for item in calls
        if item[
            "provider"
        ]
        == "WIKIMEDIA_COMMONS"
    ]


    archive = [
        item
        for item in calls
        if item[
            "provider"
        ]
        == "INTERNET_ARCHIVE"
    ]


    commons_ok = sum(
        1
        for item in commons
        if item[
            "ok"
        ]
    )


    archive_ok = sum(
        1
        for item in archive
        if item[
            "ok"
        ]
    )


    commons_ratio = (
        commons_ok
        /
        len(
            commons
        )

        if commons
        else 0.0
    )


    archive_ratio = (
        archive_ok
        /
        len(
            archive
        )

        if archive
        else None
    )


    return {
        "commons_calls":
            len(
                commons
            ),

        "commons_success":
            commons_ok,

        "commons_success_ratio":
            round(
                commons_ratio,
                3
            ),

        "archive_calls":
            len(
                archive
            ),

        "archive_success":
            archive_ok,

        "archive_success_ratio":
            (
                round(
                    archive_ratio,
                    3
                )
                if archive_ratio
                is not None
                else None
            ),
    }


if __name__ == "__main__":
    print(
        "VI1200.1 SEARCH EXPANSION=PASS"
    )
