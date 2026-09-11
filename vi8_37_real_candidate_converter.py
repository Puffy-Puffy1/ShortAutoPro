#!/usr/bin/env python3

VERSION = "8.37"


def convert(
    item,
    scene,
    category
):

    return {
        "path":
            item.get(
                "path"
            ),

        "source":
            "REAL_EXISTING_MEDIA",

        "media_type":
            item.get(
                "media_type"
            ),

        "width":
            item.get(
                "width"
            ),

        "height":
            item.get(
                "height"
            ),

        "query":
            scene.get(
                "query"
            )
            or "",

        "category":
            category,

        "shot":
            scene.get(
                "shot_type"
            )
            or "medium",

        "source_score":
            80,

        "metadata": {
            "real_file":
                True,

            "filename":
                item.get(
                    "name"
                ),

            "orientation":
                item.get(
                    "orientation"
                ),

            "technical_score":
                item.get(
                    "technical_score"
                ),

            "identity_confirmed":
                (
                    None
                    if category
                    == "FACE"
                    else True
                ),
        },
    }


def self_test():

    result = convert(
        {
            "path":
                "scene_01.jpg",

            "media_type":
                "STILL",

            "width":
                1200,

            "height":
                1600,
        },
        {
            "query":
                "house"
        },
        "LOCATION"
    )

    assert (
        result[
            "source"
        ]
        == "REAL_EXISTING_MEDIA"
    )

    print(
        "VI8.37 REAL CANDIDATE CONVERTER=PASS"
    )


if __name__ == "__main__":
    self_test()
