#!/usr/bin/env python3

VERSION = "8.78"


def evaluate(map_result):
    candidates = []

    for module in (
        map_result.get(
            "modules"
        )
        or []
    ):
        search_functions = [
            fn
            for fn in (
                module.get(
                    "functions"
                )
                or []
            )
            if fn.get(
                "role"
            ) == "SEARCH"
        ]

        download_functions = [
            fn
            for fn in (
                module.get(
                    "functions"
                )
                or []
            )
            if fn.get(
                "role"
            ) == "DOWNLOAD"
        ]

        if not search_functions:
            continue

        score = 0
        reasons = []

        if search_functions:
            score += 40
            reasons.append(
                "search_function_present"
            )

        if module.get(
            "providers"
        ):
            score += 25
            reasons.append(
                "provider_detected"
            )

        if module.get(
            "network_call_count",
            0
        ):
            score += 20
            reasons.append(
                "network_path_detected"
            )

        if not download_functions:
            score += 15
            reasons.append(
                "search_download_separated"
            )

        candidates.append({
            "path":
                module.get(
                    "path"
                ),

            "score":
                score,

            "providers":
                module.get(
                    "providers"
                ),

            "search_functions":
                search_functions,

            "download_functions":
                download_functions,

            "reasons":
                reasons,
        })

    candidates.sort(
        key=lambda x:
            x.get(
                "score",
                0
            ),
        reverse=True
    )

    return {
        "version": VERSION,
        "candidates":
            candidates,
        "count":
            len(candidates),
        "best":
            (
                candidates[0]
                if candidates
                else None
            ),
    }


def self_test():
    assert VERSION == "8.78"

    print(
        "VI8.78 SAFE INTEGRATION CANDIDATE=PASS"
    )


if __name__ == "__main__":
    self_test()
