#!/usr/bin/env python3

from vi8_11_ideal_shot_generator import generate

VERSION = "8.12"

SIZE_BY_SHOT = {
    "close_up":
        (1200, 1600),

    "medium":
        (1200, 1600),

    "wide":
        (1600, 1000),
}

def build(scene, category):
    query = str(
        scene.get("query")
        or ""
    )

    shots = generate(
        category
    )

    candidates = []

    for index, shot in enumerate(
        shots,
        start=1
    ):
        width, height = (
            SIZE_BY_SHOT.get(
                shot,
                (1200, 1600)
            )
        )

        candidates.append({
            "path":
                f"shadow://scene_{scene.get('scene')}_{shot}_{index}",

            "source":
                "SHADOW_VIRTUAL",

            "media_type":
                "STILL",

            "width":
                width,

            "height":
                height,

            "query":
                query,

            "category":
                category,

            "shot":
                shot,

            "source_score":
                85,

            "metadata": {
                "virtual":
                    True,

                "identity_confirmed":
                    (
                        True
                        if category != "FACE"
                        else None
                    ),
            },
        })

    return candidates

def self_test():
    result = build(
        {
            "scene": 3,
            "query": "house exterior"
        },
        "LOCATION"
    )

    assert len(result) >= 2

    print(
        "VI8.12 VIRTUAL CANDIDATE FACTORY=PASS"
    )

if __name__ == "__main__":
    self_test()
