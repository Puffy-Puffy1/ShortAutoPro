#!/usr/bin/env python3

from vi1510_01_common import (
    BASE,
    policy,
    save_json,
)

from vi1510_03_run_resolver import (
    resolve as old_resolve,
)


def resolve():
    rows = [
        row

        for row in old_resolve()

        if row.get(
            "status"
        )
        ==
        "RESOLVED"
    ]


    rows.sort(
        key=lambda row:
            float(
                row[
                    "generation_start"
                ]
            )
    )


    config = policy()

    before = float(
        config.get(
            "artifact_window_before_seconds",
            15
        )
    )

    after = float(
        config.get(
            "artifact_window_after_seconds",
            45
        )
    )


    for index, row in enumerate(
        rows
    ):

        generation_start = float(
            row[
                "generation_start"
            ]
        )


        video_mtime = float(
            row[
                "video_mtime"
            ]
        )


        row[
            "window_start"
        ] = (
            generation_start
            -
            before
        )


        natural_end = (
            video_mtime
            +
            after
        )


        next_start = None


        if index + 1 < len(
            rows
        ):

            next_start = float(
                rows[
                    index + 1
                ][
                    "generation_start"
                ]
            )


        if next_start is not None:

            row[
                "window_end"
            ] = min(
                natural_end,
                next_start
                -
                0.5
            )


        else:

            row[
                "window_end"
            ] = natural_end


        row[
            "next_run_start"
        ] = next_start


        row[
            "partitioned"
        ] = True


    save_json(
        BASE
        / "resolved_runs_partitioned.json",
        {
            "runs":
                rows
        }
    )


    return rows


if __name__ == "__main__":

    rows = resolve()


    print(
        "VI1510.1 PARTITIONED RUN RESOLVER=PASS"
    )


    for row in rows:

        print(
            row[
                "label"
            ],
            "|",
            row[
                "short_id"
            ],
            "| START=",
            round(
                row[
                    "window_start"
                ],
                3
            ),
            "| END=",
            round(
                row[
                    "window_end"
                ],
                3
            ),
        )

# ======================================================
# VI1510.1 V4 UPSTREAM PROVENANCE PACKING
# ======================================================

from vi1510_1_22_upstream_provenance_v4 import (
    attach_source_assets as _vi1510_v4_attach_source_assets,
)


_vi1510_v4_previous_resolve = resolve


def resolve():

    rows = _vi1510_v4_previous_resolve()

    rows = _vi1510_v4_attach_source_assets(
        rows
    )

    save_json(
        BASE
        / "resolved_runs_partitioned.json",
        {
            "runs":
                rows
        },
    )

    return rows
