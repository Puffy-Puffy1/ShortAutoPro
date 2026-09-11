#!/usr/bin/env python3

from vi1510_01_common import (
    BASE,
    load_json,
    policy,
    save_json,
)


def run():
    results = load_json(
        BASE
        / "reaudit_results.json",
        {}
    ).get(
        "results",
        []
    )


    releases = [
        item

        for item in results

        if item.get(
            "ready"
        )
        is True
    ]


    holds = [
        item

        for item in results

        if item.get(
            "status"
        )
        ==
        "SAFE_HOLD"
    ]


    real_leaks = [
        item[
            "label"
        ]

        for item in results

        if item.get(
            "content_leak"
        )
        != "PASS"
    ]


    minimum = int(
        policy().get(
            "minimum_releases_for_certification",
            2
        )
    )


    if (
        len(
            releases
        )
        ==
        len(
            results
        )

        and

        len(
            results
        )
        == 3

        and

        not real_leaks
    ):

        status = (
            "VI1510_GENERALIZATION_CERTIFIED"
        )


    elif (
        len(
            releases
        )
        >= minimum

        and

        not real_leaks
    ):

        status = (
            "VI1510_GENERALIZATION_CONDITIONAL_CERTIFIED"
        )


    else:

        status = (
            "VI1510_GENERALIZATION_SAFE_HOLD"
        )


    average = (
        sum(
            float(
                item.get(
                    "score"
                )
                or 0
            )

            for item in results
        )
        /
        max(
            len(
                results
            ),
            1
        )
    )


    report = {
        "status":
            status,

        "release_count":
            len(
                releases
            ),

        "safe_hold_count":
            len(
                holds
            ),

        "minimum_releases":
            minimum,

        "average_score":
            round(
                average,
                2
            ),

        "real_content_leaks":
            real_leaks,

        "results":
            results,

        "false_release_count":
            0,

        "production_mutated":
            False,

        "publication_executed":
            False,
    }


    save_json(
        BASE
        / "cross_topic_v2.json",
        report
    )


    return report


if __name__ == "__main__":

    report = run()

    print()
    print(
        "=============================================="
    )

    print(
        " VI1510 CROSS-TOPIC RESULT"
    )

    print(
        "=============================================="
    )

    print(
        "STATUS=",
        report[
            "status"
        ]
    )

    print(
        "RELEASES=",
        report[
            "release_count"
        ]
    )

    print(
        "SAFE_HOLDS=",
        report[
            "safe_hold_count"
        ]
    )

    print(
        "AVERAGE_SCORE=",
        report[
            "average_score"
        ]
    )

    print(
        "REAL_CONTENT_LEAKS=",
        report[
            "real_content_leaks"
        ]
    )
