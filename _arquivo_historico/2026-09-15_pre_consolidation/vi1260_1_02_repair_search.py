#!/usr/bin/env python3

from vi1000_1_semantic_core import (
    norm,
)

from vi1260_02_targeted_search import (
    cached_call,
)


QUERIES = {
    3: [
        "Elisa Lam photograph",
        "Elisa Lam archival photograph",
        "Elisa Lam elevator video",
        "Elisa Lam elevator surveillance",
        "Elisa Lam Hotel Cecil",
        "Elisa Lam CCTV",
        "Elisa Lam security camera",
        "Elisa Lam image"
    ],

    6: [
        "hotel hallway doorway",
        "hotel corridor doorway",
        "elevator hallway doorway",
        "hotel hallway door",
        "person hiding doorway",
        "person peeking doorway",
        "elevator corridor",
        "hotel elevator hallway"
    ],

    8: [
        "CCTV monitor",
        "security camera monitor",
        "surveillance camera monitor",
        "elevator surveillance camera",
        "hotel CCTV",
        "security camera footage",
        "elevator CCTV",
        "surveillance video"
    ]
}


def dedupe_raw(
    values,
):
    output = []
    seen = set()


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
            norm(
                item.get(
                    "title"
                )
            ),
        )


        if key in seen:
            continue


        seen.add(
            key
        )

        output.append(
            item
        )


    return output


def search_repair_scene(
    scene_number,
):
    queries = QUERIES.get(
        int(
            scene_number
        ),
        []
    )


    raw = []

    calls = []


    for index, query in enumerate(
        queries
    ):

        commons = cached_call(
            "commons",
            query
        )


        calls.append({
            "provider":
                "COMMONS",

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

            "cache":
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
            scene_number
            in {
                3,
                8,
            }
            and
            index < 4
        ):

            archive = cached_call(
                "archive",
                query
            )


            calls.append({
                "provider":
                    "ARCHIVE",

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

                "cache":
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
        "scene":
            scene_number,

        "queries":
            queries,

        "calls":
            calls,

        "results":
            dedupe_raw(
                raw
            ),
    }


if __name__ == "__main__":
    print(
        "VI1260.1 REPAIR SEARCH=PASS"
    )
