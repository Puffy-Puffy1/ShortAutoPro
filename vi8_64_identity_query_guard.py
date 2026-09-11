#!/usr/bin/env python3

VERSION = "8.64"


def evaluate(
    category,
    base_query,
    subject_name=None
):
    warnings = []
    blockers = []

    category = str(
        category or "GENERAL"
    ).upper()

    query = str(
        base_query or ""
    ).strip()

    if category == "FACE":

        if subject_name:
            if (
                str(subject_name).lower()
                not in query.lower()
            ):
                query = (
                    str(subject_name).strip()
                    + " "
                    + query
                ).strip()

        else:
            warnings.append(
                "face_query_without_confirmed_subject_name"
            )

    return {
        "version": VERSION,
        "query": query,
        "blockers": blockers,
        "warnings": warnings,
        "status": (
            "HOLD"
            if blockers
            else (
                "CAUTION"
                if warnings
                else "PASS"
            )
        ),
    }


def self_test():
    result = evaluate(
        "FACE",
        "portrait",
        "Example Person"
    )

    assert (
        "Example Person"
        in result["query"]
    )

    print(
        "VI8.64 IDENTITY QUERY GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
