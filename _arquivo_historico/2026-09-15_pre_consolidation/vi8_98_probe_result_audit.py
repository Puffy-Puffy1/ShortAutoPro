#!/usr/bin/env python3

VERSION = "8.98"


def evaluate(
    probe_status,
    safety
):

    blockers = []
    warnings = []


    if probe_status in {
        "SEARCH_RETURNED",
        "NETWORK_LOCKED",
        "NO_SEARCH_REQUIRED",
    }:
        pass

    elif probe_status in {
        "TIMEOUT",
        "PROVIDER_ERROR",
        "HOLD",
    }:

        warnings.append(
            "provider_probe_not_successful"
        )


    if safety.get(
        "download_allowed"
    ):

        blockers.append(
            "download_not_locked"
        )


    if safety.get(
        "media_write_allowed"
    ):

        blockers.append(
            "media_write_not_locked"
        )


    return {
        "version": VERSION,

        "status":
            (
                "HOLD"
                if blockers
                else (
                    "PASS_WITH_WARNINGS"
                    if warnings
                    else "PASS"
                )
            ),

        "blockers":
            blockers,

        "warnings":
            warnings,
    }


def self_test():

    result = evaluate(
        "SEARCH_RETURNED",
        {
            "download_allowed":
                False,

            "media_write_allowed":
                False,
        }
    )

    assert result[
        "status"
    ] == "PASS"

    print(
        "VI8.98 PROBE RESULT AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
