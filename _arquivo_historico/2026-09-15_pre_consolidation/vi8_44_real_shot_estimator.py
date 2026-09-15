#!/usr/bin/env python3

VERSION = "8.44"


def estimate(
    item,
    category,
    scene
):
    orientation = str(
        item.get(
            "orientation"
        )
        or ""
    ).upper()

    editorial = str(
        scene.get(
            "shot_type"
        )
        or ""
    ).lower()

    # Editorial metadata stays primary.
    if editorial in {
        "close_up",
        "medium",
        "wide",
    }:
        return editorial

    if category in {
        "FACE",
        "DOCUMENT",
        "EVIDENCE",
        "OBJECT",
    }:
        if orientation == "PORTRAIT":
            return "close_up"

        return "medium"

    if category == "LOCATION":
        if orientation == "LANDSCAPE":
            return "wide"

        return "medium"

    return "medium"


def self_test():
    result = estimate(
        {
            "orientation":
                "LANDSCAPE"
        },
        "LOCATION",
        {}
    )

    assert result == "wide"

    print(
        "VI8.44 REAL SHOT ESTIMATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
