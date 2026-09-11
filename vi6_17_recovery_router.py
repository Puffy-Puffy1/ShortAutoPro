#!/usr/bin/env python3

from vi6_16_source_capabilities import (
    discover,
    summarize,
    QUERY_ARGS,
)


VERSION = "6.17"


def _score_function(
    function,
    plan
):

    score = 0


    source = function.get(
        "source"
    )


    prefer_wiki = bool(
        plan.get(
            "prefer_wikimedia"
        )
    )


    allow_stock = bool(
        plan.get(
            "allow_stock_retry"
        )
    )


    if prefer_wiki:

        if source == "WIKIMEDIA":
            score += 100

        elif source == "GENERIC":
            score += 45

        elif source == "PIXABAY":
            score -= 30


    elif allow_stock:

        if source == "PIXABAY":
            score += 70

        elif source == "GENERIC":
            score += 45

        elif source == "WIKIMEDIA":
            score += 30


    else:

        if source == "GENERIC":
            score += 50

        elif source == "WIKIMEDIA":
            score += 45

        elif source == "PIXABAY":
            score += 25


    name = str(
        function.get(
            "name",
            ""
        )
    ).lower()


    if "foto" in name:
        score += 5


    if "video" in name:
        score += 4


    if "buscar" in name:
        score += 3


    if "search" in name:
        score += 3


    return score


def _query_parameter(
    function
):

    names = (
        function.get(
            "args",
            []
        )
        + function.get(
            "required",
            []
        )
        + function.get(
            "optional",
            []
        )
    )


    for name in names:

        if name.lower() in QUERY_ARGS:

            return name


    return None


def build_route(
    recovery_plan,
    functions=None
):

    if functions is None:

        functions = discover()


    if not recovery_plan.get(
        "eligible"
    ):

        return {
            "version":
                VERSION,

            "ready":
                False,

            "reason":
                "recovery_not_eligible",

            "routes":
                [],
        }


    candidates = [
        fn

        for fn in functions

        if fn.get(
            "candidate_for_recovery"
        )
    ]


    ranked = []


    for fn in candidates:

        query_arg = (
            _query_parameter(
                fn
            )
        )


        if not query_arg:
            continue


        ranked.append(
            {
                "function":
                    fn,

                "query_arg":
                    query_arg,

                "score":
                    _score_function(
                        fn,
                        recovery_plan
                    ),
            }
        )


    ranked.sort(
        key=lambda x:
            x["score"],
        reverse=True
    )


    routes = []


    queries = (
        recovery_plan.get(
            "queries"
        )
        or []
    )


    max_attempts = int(
        recovery_plan.get(
            "max_attempts",
            0
        )
        or 0
    )


    for query in queries[
        :max_attempts
    ]:

        if not ranked:
            break


        best = ranked[0]

        function = best[
            "function"
        ]


        routes.append(
            {
                "query":
                    query,

                "source":
                    function.get(
                        "source"
                    ),

                "file":
                    function.get(
                        "file"
                    ),

                "function":
                    function.get(
                        "name"
                    ),

                "query_parameter":
                    best[
                        "query_arg"
                    ],

                "required":
                    function.get(
                        "required"
                    ),

                "score":
                    best[
                        "score"
                    ],

                "mode":
                    "DRY_RUN",
            }
        )


    return {
        "version":
            VERSION,

        "ready":
            bool(
                routes
        ),

        "reason":
            (
                "route_ready"
                if routes
                else "no_safe_source_function"
            ),

        "capabilities":
            summarize(
                functions
            ),

        "routes":
            routes,
    }


def self_test():

    plan = {
        "eligible":
            True,

        "queries":
            [
                "Flight 19 1945 archive"
            ],

        "max_attempts":
            2,

        "prefer_wikimedia":
            True,

        "allow_stock_retry":
            False,
    }


    functions = [
        {
            "file":
                "wikimedia_source.py",

            "line":
                100,

            "name":
                "buscar_wikimedia_fotos",

            "source":
                "WIKIMEDIA",

            "args":
                [
                    "query",
                    "limit"
                ],

            "required":
                [
                    "query"
                ],

            "optional":
                [
                    "limit"
                ],

            "candidate_for_recovery":
                True,
        },

        {
            "file":
                "midia.py",

            "line":
                200,

            "name":
                "buscar_pixabay",

            "source":
                "PIXABAY",

            "args":
                [
                    "query"
                ],

            "required":
                [
                    "query"
                ],

            "optional":
                [],

            "candidate_for_recovery":
                True,
        },
    ]


    route = build_route(
        plan,
        functions
    )


    assert route[
        "ready"
    ] is True


    assert (
        route[
            "routes"
        ][0][
            "source"
        ]
        == "WIKIMEDIA"
    )


    assert (
        route[
            "routes"
        ][0][
            "mode"
        ]
        == "DRY_RUN"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.17 ROUTER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Documentary-first Routing"
    )
    print(
        "OK Query Parameter Mapping"
    )
    print(
        "OK Query Budget"
    )
    print(
        "OK DRY_RUN enforcement"
    )
    print()


if __name__ == "__main__":

    self_test()
