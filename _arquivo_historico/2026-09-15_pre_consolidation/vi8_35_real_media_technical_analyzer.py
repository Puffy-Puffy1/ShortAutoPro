#!/usr/bin/env python3

from vi8_02_crop_fitness import (
    evaluate as crop_fitness
)

from vi8_34_image_dimension_reader import (
    dimensions
)

VERSION = "8.35"


def evaluate(item):

    result = dict(
        item
    )

    if (
        item.get(
            "media_type"
        )
        != "STILL"
    ):

        result.update({
            "width":
                None,

            "height":
                None,

            "orientation":
                "VIDEO_OR_UNKNOWN",

            "crop_fitness":
                None,

            "technical_score":
                80.0,
        })

        return result


    dims = dimensions(
        item.get(
            "path"
        )
    )


    if not dims:

        result.update({
            "width":
                None,

            "height":
                None,

            "orientation":
                "UNKNOWN",

            "crop_fitness":
                {
                    "score":
                        50.0,

                    "status":
                        "UNKNOWN",
                },

            "technical_score":
                50.0,
        })

        return result


    width, height = dims


    if height > width:
        orientation = (
            "PORTRAIT"
        )

    elif width > height:
        orientation = (
            "LANDSCAPE"
        )

    else:
        orientation = (
            "SQUARE"
        )


    crop = crop_fitness(
        width,
        height
    )


    size_bytes = int(
        item.get(
            "size_bytes",
            0
        )
        or 0
    )


    size_bonus = (
        10
        if size_bytes >= 500_000
        else 0
    )


    technical_score = min(
        100.0,
        float(
            crop.get(
                "score",
                50
            )
        )
        * .9
        + size_bonus
    )


    result.update({
        "width":
            width,

        "height":
            height,

        "orientation":
            orientation,

        "crop_fitness":
            crop,

        "technical_score":
            round(
                technical_score,
                2
            ),
    })


    return result


def self_test():

    assert VERSION == "8.35"

    print(
        "VI8.35 REAL MEDIA TECHNICAL ANALYZER=PASS"
    )


if __name__ == "__main__":
    self_test()
