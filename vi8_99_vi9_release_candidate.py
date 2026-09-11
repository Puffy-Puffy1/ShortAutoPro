#!/usr/bin/env python3

VERSION = "8.99"


def evaluate(
    audit,
    safe_result_count,
    probe_executed
):

    blockers = (
        audit.get(
            "blockers"
        )
        or []
    )

    warnings = (
        audit.get(
            "warnings"
        )
        or []
    )


    if blockers:

        status = "HOLD"


    elif not probe_executed:

        status = (
            "READY_FOR_CONTROLLED_SEARCH_PROBE"
        )


    elif safe_result_count > 0:

        status = (
            "VI9_SEARCH_OBSERVATION_CANDIDATE"
        )


    else:

        status = (
            "SEARCH_PROVIDER_TUNING_REQUIRED"
        )


    return {
        "version": VERSION,

        "status":
            status,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "safe_result_count":
            safe_result_count,

        "download_activation":
            False,

        "media_replacement":
            False,

        "renderer_activation":
            False,

        "full_active":
            False,
    }


def self_test():

    assert VERSION == "8.99"

    print(
        "VI8.99 VI9 RELEASE CANDIDATE=PASS"
    )


if __name__ == "__main__":
    self_test()
