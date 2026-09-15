#!/usr/bin/env python3

import os

VERSION = "8.97"


def evaluate(
    contract_selection,
    query_selection
):

    blockers = []


    if (
        contract_selection.get(
            "status"
        )
        != "SAFE_CONTRACT_SELECTED"
    ):

        blockers.append(
            "safe_contract_missing"
        )


    if query_selection.get(
        "status"
    ) not in {
        "QUERY_SELECTED",
        "NO_SEARCH_REQUIRED",
    }:

        blockers.append(
            "safe_query_missing"
        )


    network_enabled = (
        os.getenv(
            "VI900_NETWORK_PROBE",
            "OFF"
        ).upper()
        == "ON"
    )


    if blockers:

        status = "HOLD"

    elif (
        query_selection.get(
            "status"
        )
        == "NO_SEARCH_REQUIRED"
    ):

        status = (
            "NO_SEARCH_REQUIRED"
        )

    elif network_enabled:

        status = (
            "CONTROLLED_PROBE_ALLOWED"
        )

    else:

        status = (
            "PROBE_READY_NETWORK_LOCKED"
        )


    return {
        "version": VERSION,

        "status":
            status,

        "blockers":
            blockers,

        "network_enabled":
            network_enabled,

        "download_allowed":
            False,

        "media_write_allowed":
            False,

        "renderer_allowed":
            False,

        "ffmpeg_allowed":
            False,
    }


def self_test():

    assert VERSION == "8.97"

    print(
        "VI8.97 OBSERVATIONAL PROBE GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
