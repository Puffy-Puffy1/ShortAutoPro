#!/usr/bin/env python3

VERSION = "8.92"


def build(contract, query):

    args = (
        contract.get("args")
        or []
    )

    kwargs = {}

    query_assigned = False

    for arg in args:

        low = str(arg).lower()

        if low in {
            "query",
            "q",
            "term",
            "search_term",
            "keywords",
            "keyword",
        }:
            kwargs[arg] = query
            query_assigned = True

        elif low in {
            "limit",
            "max_results",
            "count",
        }:
            kwargs[arg] = 5

        else:
            return {
                "version": VERSION,
                "status": "HOLD",
                "reason":
                    f"unsupported_arg:{arg}",
                "kwargs": {},
            }

    if not query_assigned:
        return {
            "version": VERSION,
            "status": "HOLD",
            "reason":
                "query_argument_missing",
            "kwargs": {},
        }

    return {
        "version": VERSION,
        "status":
            "ARGS_READY",
        "reason": None,
        "kwargs":
            kwargs,
    }


def self_test():

    result = build(
        {
            "args": [
                "query",
                "limit",
            ]
        },
        "test"
    )

    assert (
        result["status"]
        == "ARGS_READY"
    )

    print(
        "VI8.92 QUERY ARGUMENT BUILDER=PASS"
    )


if __name__ == "__main__":
    self_test()
