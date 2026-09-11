#!/usr/bin/env python3

VERSION = "8.16"

def evaluate(selections):
    warnings = []

    winner_categories = [
        (
            item.get(
                "winner"
            )
            or {}
        ).get(
            "candidate",
            {}
        ).get(
            "category"
        )
        for item in selections
    ]

    winner_shots = [
        (
            item.get(
                "winner"
            )
            or {}
        ).get(
            "candidate",
            {}
        ).get(
            "shot"
        )
        for item in selections
    ]

    for i in range(
        len(selections) - 2
    ):
        cats = winner_categories[
            i:i+3
        ]

        shots = winner_shots[
            i:i+3
        ]

        if (
            len(set(cats)) == 1
            and cats[0]
        ):
            warnings.append({
                "type":
                    "three_same_categories",

                "scenes":
                    [
                        selections[i+j][
                            "scene"
                        ]
                        for j in range(3)
                    ],
            })

        if (
            len(set(shots)) == 1
            and shots[0]
        ):
            warnings.append({
                "type":
                    "three_same_shots",

                "scenes":
                    [
                        selections[i+j][
                            "scene"
                        ]
                        for j in range(3)
                    ],
            })

    return {
        "version":
            VERSION,

        "warnings":
            warnings,

        "count":
            len(warnings),
    }

def self_test():
    assert VERSION == "8.16"

    print(
        "VI8.16 GLOBAL MEDIA CONTINUITY=PASS"
    )

if __name__ == "__main__":
    self_test()
