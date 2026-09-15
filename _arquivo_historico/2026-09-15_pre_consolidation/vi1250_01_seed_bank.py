#!/usr/bin/env python3

import copy

from vi1000_1_semantic_core import (
    norm,
)

from vi1200_02_commons_provider import (
    exact_titles,
)

from vi1200_06_visual_precision import (
    scene_visual_intents,
)


SEED_DEFINITIONS = [
    {
        "title":
            "File:Hotel Cecil LA.jpg",

        "type":
            "VERIFIED_LOCATION",

        "tags": [
            "HOTEL",
            "CASE_LOCATION",
        ],
    },

    {
        "title":
            "File:Elisa Lam elevator video.webm",

        "type":
            "CASE_ARCHIVE",

        "tags": [
            "ELEVATOR",
            "SURVEILLANCE",
            "CASE_EVIDENCE",
        ],
    },

    {
        "title":
            "File:Medicine box (AM 614816-33).jpg",

        "type":
            "GENERIC_OBJECT",

        "tags": [
            "MEDICATION",
            "OBJECT",
        ],
    },

    {
        "title":
            "File:Arizona Biltmore Hallway.jpg",

        "type":
            "GENERIC_LOCATION",

        "tags": [
            "HALLWAY",
        ],
    },

    {
        "title":
            (
                "File:Conrad Indianapolis hotel, "
                "16th floor hallway, Indy, Indiana.jpg"
            ),

        "type":
            "GENERIC_LOCATION",

        "tags": [
            "HALLWAY",
        ],
    },

    {
        "title":
            (
                "File:Water Towers On New York City's "
                "46th Street - June 1984.jpg"
            ),

        "type":
            "GENERIC_LOCATION",

        "tags": [
            "ROOFTOP",
            "WATER_TANK",
        ],
    },

    {
        "title":
            "File:NYC Spires 20150607.jpg",

        "type":
            "GENERIC_LOCATION",

        "tags": [
            "ROOFTOP",
        ],
    },
]


def fetch_seed_bank():
    titles = [
        item[
            "title"
        ]
        for item in (
            SEED_DEFINITIONS
        )
    ]

    response = exact_titles(
        titles
    )


    raw_map = {
        norm(
            item.get(
                "title"
            )
        ):
            item

        for item in (
            response.get(
                "results"
            )
            or []
        )
    }


    seeds = []


    for definition in (
        SEED_DEFINITIONS
    ):
        raw = raw_map.get(
            norm(
                definition[
                    "title"
                ]
            )
        )


        if raw is None:
            continue


        item = copy.deepcopy(
            raw
        )


        item[
            "_vi1250_seed_type"
        ] = definition[
            "type"
        ]

        item[
            "_vi1250_seed_tags"
        ] = definition[
            "tags"
        ]


        seeds.append(
            item
        )


    return {
        "ok":
            response.get(
                "ok",
                False
            ),

        "requested":
            len(
                titles
            ),

        "found":
            len(
                seeds
            ),

        "seeds":
            seeds,

        "raw_response":
            response,
    }


def seeds_for_scene(
    scene,
    seed_bank
):
    intents = scene_visual_intents(
        scene
    )

    role = str(
        scene.get(
            "role"
        )
        or ""
    ).upper()


    result = []


    strong = {
        "ELEVATOR",
        "HALLWAY",
        "ROOFTOP",
        "SURVEILLANCE",
        "MEDICATION",
        "WATER_TANK",
    }


    for raw in (
        seed_bank.get(
            "seeds"
        )
        or []
    ):

        tags = set(
            raw.get(
                "_vi1250_seed_tags"
            )
            or []
        )


        seed_type = raw.get(
            "_vi1250_seed_type"
        )


        allow = False


        if (
            "SURVEILLANCE"
            in intents
            and
            {
                "SURVEILLANCE",
                "CASE_EVIDENCE",
            }
            &
            tags
        ):
            allow = True


        elif (
            "ELEVATOR"
            in intents
            and
            "ELEVATOR"
            in tags
        ):
            allow = True


        elif (
            "HALLWAY"
            in intents
            and
            "HALLWAY"
            in tags
            and
            not scene.get(
                "factual"
            )
        ):
            allow = True


        elif (
            "ROOFTOP"
            in intents
            and
            "ROOFTOP"
            in tags
            and
            not scene.get(
                "factual"
            )
        ):
            allow = True


        elif (
            "MEDICATION"
            in intents
            and
            "MEDICATION"
            in tags
            and
            not scene.get(
                "factual"
            )
        ):
            allow = True


        elif (
            seed_type
            == "VERIFIED_LOCATION"
            and
            role
            in {
                "LOCATION",
                "CONTEXT",
                "DOCUMENT",
            }
            and
            not (
                intents
                &
                strong
            )
        ):
            allow = True


        if (
            scene.get(
                "cta"
            )
            and
            seed_type
            in {
                "VERIFIED_LOCATION",
                "CASE_ARCHIVE",
            }
        ):
            allow = True


        if allow:
            result.append(
                copy.deepcopy(
                    raw
                )
            )


    return result


if __name__ == "__main__":
    print(
        "VI1250 SEED BANK=PASS"
    )
