#!/usr/bin/env python3

from vi8_61_query_normalizer import (
    normalize
)

from vi8_62_search_intent_builder import (
    build as intent_terms
)

from vi8_63_shot_search_language import (
    terms as shot_terms
)

from vi8_65_graphic_search_guard import (
    sanitize
)

VERSION = "8.66"


def generate(
    base_query,
    category,
    ideal_shot
):
    base = normalize(
        base_query
    )

    intents = intent_terms(
        category
    )

    shots = shot_terms(
        ideal_shot
    )

    candidates = [
        base,
        f"{base} {intents[0]}",
        f"{base} {shots[0]}",
        f"{base} {intents[0]} {shots[0]}",
    ]

    if len(intents) > 1:
        candidates.append(
            f"{base} {intents[1]}"
        )

    cleaned = []

    seen = set()

    for candidate in candidates:
        candidate = normalize(
            candidate
        )

        candidate = sanitize(
            candidate
        )["query"]

        key = (
            candidate
            .strip()
            .lower()
        )

        if (
            key
            and key not in seen
        ):
            seen.add(key)
            cleaned.append(
                candidate.strip()
            )

    return cleaned[:5]


def self_test():
    result = generate(
        "ransom note",
        "DOCUMENT",
        "close_up"
    )

    assert len(result) >= 3

    print(
        "VI8.66 QUERY VARIANT GENERATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
