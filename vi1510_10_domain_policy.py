#!/usr/bin/env python3

from vi1510_01_common import (
    policy,
)


def requirements(
    domain,
):
    config = policy()


    domains = (
        config.get(
            "domains"
        )
        or {}
    )


    return (
        domains.get(
            domain
        )

        or

        domains.get(
            "CUSTOM"
        )

        or

        {
            "minimum_assets":
                4,

            "minimum_unique_assets":
                4,

            "minimum_source_records":
                3,

            "minimum_provenance_coverage":
                0.35,

            "minimum_licensed_records":
                1,

            "minimum_relevant_records":
                1,
        }
    )


if __name__ == "__main__":

    for domain in [
        "HISTORICAL_MYSTERY",
        "HISTORICAL_EVENT",
        "SCIENCE_CONCEPT",
        "CUSTOM",
    ]:

        print(
            domain,
            "=",
            requirements(
                domain
            )
        )
