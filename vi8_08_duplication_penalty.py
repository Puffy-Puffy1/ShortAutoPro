#!/usr/bin/env python3

VERSION = "8.08"

def penalty(
    candidate,
    previous_candidates
):
    path = str(
        candidate.get("path")
        or ""
    )

    category = candidate.get(
        "category"
    )

    penalty_value = 0
    reasons = []

    for previous in (
        previous_candidates
        or []
    ):
        if (
            path
            and path
            == str(
                previous.get("path")
                or ""
            )
        ):
            penalty_value += 70

            reasons.append(
                "exact_media_repeat"
            )

        elif (
            category
            and category
            == previous.get(
                "category"
            )
        ):
            penalty_value += 10

            reasons.append(
                "category_repeat"
            )

    return {
        "version": VERSION,
        "penalty": min(
            100,
            penalty_value
        ),
        "reasons":
            sorted(
                set(reasons)
            ),
    }

def self_test():
    candidate = {
        "path": "a.jpg",
        "category": "FACE",
    }

    result = penalty(
        candidate,
        [{
            "path": "a.jpg",
            "category": "FACE",
        }]
    )

    assert result["penalty"] >= 70

    print(
        "VI8.08 DUPLICATION PENALTY=PASS"
    )

if __name__ == "__main__":
    self_test()
