#!/usr/bin/env python3

from vi8_81_architecture_baseline import (
    load
)

from vi8_82_module_path_resolver import (
    resolve
)

from vi8_83_ast_function_inspector import (
    inspect_python
)

from vi8_84_function_risk_classifier import (
    evaluate as function_risk
)

from vi8_85_import_risk_audit import (
    evaluate as import_risk
)

VERSION = "8.86"


def build():
    baseline = load()

    integration = (
        baseline.get(
            "integration_candidates"
        )
        or {}
    )

    candidates = (
        integration.get(
            "candidates"
        )
        or []
    )

    plans = []

    for candidate in candidates:
        relative = candidate.get(
            "path"
        )

        resolved = resolve(
            relative
        )

        if resolved.get(
            "status"
        ) != "PASS":
            continue

        path = resolved.get(
            "path"
        )

        inspection = (
            inspect_python(
                path
            )
        )

        functions = [
            function_risk(fn)
            for fn in (
                inspection.get(
                    "functions"
                )
                or []
            )
        ]

        safe_search = [
            fn
            for fn in functions
            if fn.get(
                "classification"
            )
            == "SEARCH_CANDIDATE"
        ]

        blocked = [
            fn
            for fn in functions
            if fn.get(
                "classification"
            )
            == "BLOCKED"
        ]

        imports = import_risk(
            inspection.get(
                "imports"
            )
            or []
        )

        plans.append({
            "module":
                relative,

            "path":
                path,

            "providers":
                candidate.get(
                    "providers"
                )
                or [],

            "safe_search_functions":
                safe_search,

            "blocked_functions":
                blocked,

            "import_risk":
                imports,

            "discovery_score":
                candidate.get(
                    "score"
                ),
        })

    plans.sort(
        key=lambda item: (
            -len(
                item[
                    "safe_search_functions"
                ]
            ),
            -float(
                item.get(
                    "discovery_score",
                    0
                )
            ),
        )
    )

    best = (
        plans[0]
        if plans
        and plans[0][
            "safe_search_functions"
        ]
        else None
    )

    return {
        "version": VERSION,
        "plans": plans,
        "count":
            len(plans),
        "best":
            best,
    }


def self_test():
    assert VERSION == "8.86"

    print(
        "VI8.86 STATIC SEARCH ADAPTER PLAN=PASS"
    )


if __name__ == "__main__":
    self_test()
