#!/usr/bin/env python3

from vi1510_01_common import (
    save_json,
)


def run(
    run,
    inventory,
    run_dir,
):
    generation_start = float(
        run[
            "generation_start"
        ]
    )


    short_id = (
        run.get(
            "short_id"
        )
        or ""
    )


    stale = []

    fresh = []


    for asset in inventory.get(
        "source_assets",
        []
    ):

        sid_match = (
            bool(
                short_id
            )

            and

            short_id
            in asset[
                "path"
            ]
        )


        old = (
            float(
                asset[
                    "mtime"
                ]
            )
            <
            generation_start
            -
            300
        )


        if (
            old

            and

            not sid_match
        ):

            stale.append(
                asset[
                    "path"
                ]
            )


        else:

            fresh.append(
                asset[
                    "path"
                ]
            )


    warnings = []

    blockers = []


    if stale:

        warnings.append(
            "stale_or_reused_assets_present"
        )


    if (
        inventory.get(
            "source_asset_count",
            0
        )
        > 0

        and

        not fresh
    ):

        blockers.append(
            "all_detected_assets_are_stale"
        )


    report = {
        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "fresh_assets":
            fresh,

        "stale_assets":
            stale,

        "warnings":
            warnings,

        "blockers":
            blockers,
    }


    save_json(
        run_dir
        / "stale_asset_guard.json",
        report
    )


    return report
