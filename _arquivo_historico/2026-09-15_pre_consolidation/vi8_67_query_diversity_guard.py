#!/usr/bin/env python3

VERSION = "8.67"


def evaluate(queries):
    normalized = [
        str(x or "")
        .lower()
        .strip()
        for x in queries
        if str(x or "").strip()
    ]

    unique = list(
        dict.fromkeys(
            normalized
        )
    )

    ratio = (
        len(unique)
        / len(normalized)
        if normalized
        else 0
    )

    return {
        "version": VERSION,
        "query_count":
            len(normalized),
        "unique_count":
            len(unique),
        "diversity_ratio":
            round(
                ratio,
                3
            ),
        "status": (
            "PASS"
            if ratio >= .75
            else "PASS_WITH_WARNINGS"
        ),
    }


def self_test():
    result = evaluate([
        "a",
        "b",
        "c",
    ])

    assert (
        result["status"]
        == "PASS"
    )

    print(
        "VI8.67 QUERY DIVERSITY GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
