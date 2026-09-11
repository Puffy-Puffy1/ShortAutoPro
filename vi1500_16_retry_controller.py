#!/usr/bin/env python3

import time

from vi1500_01_common import (
    policy,
)

from vi1500_06_generator_adapter import (
    execute,
)

from vi1500_15_failure_recovery import (
    classify_failure,
)


def run_with_retry(
    topic,
    run_id,
    run_dir,
):
    maximum = int(
        policy().get(
            "generator_max_attempts",
            2
        )
    )


    attempts = []


    for attempt in range(
        1,
        maximum + 1
    ):
        result = execute(
            topic,
            run_id,
            run_dir,
        )


        result[
            "attempt"
        ] = attempt


        attempts.append(
            result
        )


        if result.get(
            "status"
        ) in {
            "GENERATOR_COMPLETED",
            "GENERATION_DISABLED",
            "GENERATOR_CONTRACT_UNRESOLVED",
        }:
            break


        recovery = classify_failure(
            result
        )


        if (
            not recovery[
                "transient"
            ]

            or

            attempt >= maximum
        ):
            break


        delay = (
            4
            *
            attempt
        )


        print(
            "GENERATOR RETRY",
            attempt,
            "->",
            delay,
            "seconds"
        )


        time.sleep(
            delay
        )


    return {
        "attempts":
            attempts,

        "final":
            attempts[
                -1
            ],

        "attempt_count":
            len(
                attempts
            ),
    }
