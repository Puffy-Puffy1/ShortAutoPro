#!/usr/bin/env python3

VERSION = "8.87"

ALLOWED_QUERY_ARGS = {
    "query",
    "q",
    "term",
    "search_term",
    "keywords",
    "keyword",
    "limit",
    "max_results",
    "count",
}


def build(module_plan):
    if not module_plan:
        return {
            "version": VERSION,
            "status": "HOLD",
            "reason":
                "no_module_plan",
            "contracts": [],
        }

    contracts = []

    for fn in (
        module_plan.get(
            "safe_search_functions"
        )
        or []
    ):
        args = [
            str(arg)
            for arg in (
                fn.get(
                    "args"
                )
                or []
            )
            if arg not in {
                "self",
                "cls",
            }
        ]

        unsupported = [
            arg
            for arg in args
            if arg.lower()
            not in ALLOWED_QUERY_ARGS
        ]

        if unsupported:
            status = (
                "STATIC_REVIEW_REQUIRED"
            )
        else:
            status = (
                "READ_ONLY_SIGNATURE_ACCEPTABLE"
            )

        contracts.append({
            "module":
                module_plan.get(
                    "module"
                ),

            "function":
                fn.get(
                    "name"
                ),

            "args":
                args,

            "unsupported_args":
                unsupported,

            "status":
                status,

            "invoke_now":
                False,

            "network_now":
                False,

            "download_now":
                False,
        })

    return {
        "version": VERSION,
        "status": (
            "READY"
            if contracts
            else "HOLD"
        ),
        "contracts":
            contracts,
    }


def self_test():
    result = build({
        "module": "x.py",
        "safe_search_functions": [{
            "name":
                "search_images",
            "args":
                ["query", "limit"],
        }],
    })

    assert (
        result[
            "contracts"
        ][0]["status"]
        == "READ_ONLY_SIGNATURE_ACCEPTABLE"
    )

    print(
        "VI8.87 SAFE CALL CONTRACT=PASS"
    )


if __name__ == "__main__":
    self_test()
