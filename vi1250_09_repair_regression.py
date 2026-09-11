#!/usr/bin/env python3

import copy

from urllib.error import URLError


import vi1200_01_real_transport as transport


from vi1250_05_portfolio_optimizer import (
    actual_consecutive_run_if_added,
)


def selected(
    group
):
    return {
        "candidate": {
            "source_group":
                group
        }
    }


def hard_budget_test():
    old_policy = copy.deepcopy(
        transport.POLICY
    )

    old_stats = copy.deepcopy(
        transport.STATS
    )

    old_urlopen = transport.urlopen


    try:
        transport.POLICY[
            "network"
        ][
            "maximum_total_requests"
        ] = 2

        transport.POLICY[
            "network"
        ][
            "retries"
        ] = 8


        transport.STATS[
            "requests_attempted"
        ] = 0

        transport.STATS[
            "requests_succeeded"
        ] = 0

        transport.STATS[
            "requests_failed"
        ] = 0

        transport.STATS[
            "metadata_bytes_received"
        ] = 0

        transport.STATS[
            "remote_media_bytes_received"
        ] = 0

        transport.STATS[
            "hosts"
        ] = {}

        transport.STATS[
            "errors"
        ] = []


        def failing_urlopen(
            *args,
            **kwargs
        ):
            raise URLError(
                "synthetic"
            )


        transport.urlopen = (
            failing_urlopen
        )


        transport.get_json(
            (
                "https://commons.wikimedia.org/"
                "w/api.php"
            )
        )


        actual = (
            transport.STATS[
                "requests_attempted"
            ]
        )


        return {
            "passed":
                actual == 2,

            "actual":
                actual,

            "expected":
                2,
        }


    finally:
        transport.urlopen = (
            old_urlopen
        )

        transport.POLICY.clear()

        transport.POLICY.update(
            old_policy
        )

        transport.STATS.clear()

        transport.STATS.update(
            old_stats
        )


def sparse_test():
    chosen = {
        1:
            selected(
                "SOURCE:A"
            ),

        4:
            selected(
                "SOURCE:A"
            ),
    }


    actual = (
        actual_consecutive_run_if_added(
            chosen,
            8,
            "SOURCE:A",
        )
    )


    return {
        "passed":
            actual == 1,

        "actual":
            actual,

        "expected":
            1,
    }


def real_run_test():
    chosen = {
        1:
            selected(
                "SOURCE:A"
            ),

        2:
            selected(
                "SOURCE:A"
            ),
    }


    actual = (
        actual_consecutive_run_if_added(
            chosen,
            3,
            "SOURCE:A",
        )
    )


    return {
        "passed":
            actual == 3,

        "actual":
            actual,

        "expected":
            3,
    }


def gap_test():
    chosen = {
        1:
            selected(
                "SOURCE:A"
            ),

        2:
            selected(
                "SOURCE:A"
            ),

        4:
            selected(
                "SOURCE:A"
            ),
    }


    actual = (
        actual_consecutive_run_if_added(
            chosen,
            5,
            "SOURCE:A",
        )
    )


    return {
        "passed":
            actual == 2,

        "actual":
            actual,

        "expected":
            2,
    }


def main():
    tests = {
        "HARD_REQUEST_BUDGET":
            hard_budget_test(),

        "SPARSE_SCENES_NOT_CONSECUTIVE":
            sparse_test(),

        "TRUE_CONSECUTIVE_RUN_DETECTED":
            real_run_test(),

        "GAP_BREAKS_CONSECUTIVE_RUN":
            gap_test(),
    }


    failed = []


    print()
    print(
        "=============================================="
    )

    print(
        " VI1250.1 REPAIR REGRESSION"
    )

    print(
        "=============================================="
    )


    for name, result in tests.items():

        print(
            name,
            "=",
            (
                "PASS"
                if result[
                    "passed"
                ]
                else "FAIL"
            ),
            "|",
            result
        )


        if not result[
            "passed"
        ]:
            failed.append(
                name
            )


    print(
        "FAILED:",
        failed
    )


    if failed:
        raise SystemExit(
            1
        )


    print(
        "VI1250.1 REPAIR REGRESSION: CERTIFIED"
    )


if __name__ == "__main__":
    main()
