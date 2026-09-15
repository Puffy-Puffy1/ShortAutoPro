#!/usr/bin/env python3

VERSION = "8.13"

def from_scene(scene, category):
    shot = str(
        scene.get("shot_type")
        or "medium"
    ).lower()

    if shot == "wide":
        width, height = (
            1600,
            1000
        )

    elif shot == "close_up":
        width, height = (
            1200,
            1600
        )

    else:
        width, height = (
            1200,
            1600
        )

    return {
        "path":
            f"current://scene_{scene.get('scene')}",

        "source":
            "CURRENT_SELECTION",

        "media_type":
            "STILL",

        "width":
            width,

        "height":
            height,

        "query":
            scene.get("query")
            or "",

        "category":
            category,

        "shot":
            shot,

        "source_score":
            75,

        "metadata": {
            "virtual":
                False,

            "identity_confirmed":
                (
                    True
                    if category != "FACE"
                    else None
                ),
        },
    }

def self_test():
    result = from_scene(
        {
            "scene": 2,
            "shot_type": "wide",
            "query": "street"
        },
        "LOCATION"
    )

    assert result["shot"] == "wide"

    print(
        "VI8.13 CURRENT MEDIA MODEL=PASS"
    )

if __name__ == "__main__":
    self_test()
