#!/usr/bin/env python3

VERSION = "8.23"

MAX_REPLACEMENTS = 6
MAX_STRONG_CHANGES = 4


def allocate(items):
    ranked = sorted(
        items,
        key=lambda item:
            item.get(
                "priority_score",
                0
            ),
        reverse=True
    )

    selected = []

    strong_count = 0

    for item in ranked:
        if (
            len(selected)
            >= MAX_REPLACEMENTS
        ):
            break

        recommendation = (
            item.get(
                "recommendation"
            )
            or ""
        )

        confidence = float(
            item.get(
                "confidence",
                0
            )
        )

        if confidence < 65:
            continue

        if recommendation == (
            "KEEP_CURRENT"
        ):
            continue

        if recommendation == (
            "STRONG_REPLACEMENT_CANDIDATE"
        ):
            if (
                strong_count
                >= MAX_STRONG_CHANGES
            ):
                continue

            strong_count += 1

        selected.append(
            item
        )

    return {
        "version":
            VERSION,

        "max_replacements":
            MAX_REPLACEMENTS,

        "max_strong_changes":
            MAX_STRONG_CHANGES,

        "selected":
            selected,

        "selected_scenes":
            [
                item.get(
                    "scene"
                )
                for item
                in selected
            ],

        "selected_count":
            len(selected),
    }


def self_test():
    sample = [
        {
            "scene": 1,
            "priority_score": 100,
            "recommendation":
                "STRONG_REPLACEMENT_CANDIDATE",
            "confidence": 90,
        }
        for _ in range(10)
    ]

    result = allocate(
        sample
    )

    assert (
        result["selected_count"]
        <= MAX_REPLACEMENTS
    )

    print(
        "VI8.23 REPLACEMENT BUDGET=PASS"
    )


if __name__ == "__main__":
    self_test()
