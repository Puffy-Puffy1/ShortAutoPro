#!/usr/bin/env python3

import re

from pathlib import Path

from vi1400_01_common import (
    TMP,
    load_json,
    policy,
    save_json,
)


def ass_time(
    value,
):
    hours, minutes, seconds = (
        value.strip().split(
            ":"
        )
    )


    return (
        int(
            hours
        )
        * 3600

        +

        int(
            minutes
        )
        * 60

        +

        float(
            seconds
        )
    )


def visible_text(
    value,
):
    value = re.sub(
        r"\{[^}]*\}",
        "",
        value
    )


    value = value.replace(
        r"\N",
        " "
    )


    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


def inspect(
    path,
):
    config = policy()


    max_chars = int(
        config.get(
            "subtitle_max_chars",
            34
        )
    )


    min_duration = float(
        config.get(
            "subtitle_min_duration",
            0.28
        )
    )


    events = []


    for line in Path(
        path
    ).read_text(
        encoding="utf-8",
        errors="ignore"
    ).splitlines():

        if not line.startswith(
            "Dialogue:"
        ):
            continue


        parts = line.split(
            ",",
            9
        )


        if len(
            parts
        ) < 10:

            continue


        try:

            start = ass_time(
                parts[
                    1
                ]
            )


            end = ass_time(
                parts[
                    2
                ]
            )

        except Exception:

            continue


        text = visible_text(
            parts[
                9
            ]
        )


        events.append({
            "start":
                start,

            "end":
                end,

            "duration":
                end
                - start,

            "text":
                text,

            "chars":
                len(
                    text
                ),
        })


    failures = []

    warnings = []


    for index, event in enumerate(
        events,
        1
    ):

        if event[
            "duration"
        ] <= 0:

            failures.append(
                f"event_{index}_invalid_duration"
            )


        if event[
            "chars"
        ] > max_chars:

            warnings.append(
                f"event_{index}_long_text"
            )


        if (
            0
            <
            event[
                "duration"
            ]
            <
            min_duration
        ):

            warnings.append(
                f"event_{index}_too_fast"
            )


    return {
        "path":
            str(
                path
            ),

        "events":
            len(
                events
            ),

        "max_chars":
            max(
                [
                    event[
                        "chars"
                    ]

                    for event
                    in events
                ],
                default=0
            ),

        "failures":
            failures,

        "warnings":
            warnings,
    }


def run():
    artifacts = load_json(
        TMP
        / "artifacts.json"
    )


    candidates = []


    for path in (
        artifacts.get(
            "ass_candidates"
        )
        or []
    ):

        try:

            result = inspect(
                path
            )


            if result[
                "events"
            ] > 0:

                candidates.append(
                    result
                )

        except Exception:

            pass


    best = max(
        candidates,
        key=lambda item:
            item[
                "events"
            ],
        default=None,
    )


    report = {
        "status":
            "PASS",

        "best":
            best,

        "candidates_checked":
            len(
                candidates
            ),

        "warnings":
            [],

        "blockers":
            [],
    }


    if best:

        report[
            "warnings"
        ] = best[
            "warnings"
        ]


        report[
            "blockers"
        ] = best[
            "failures"
        ]


        report[
            "status"
        ] = (
            "PASS"
            if not best[
                "failures"
            ]
            else "HOLD"
        )


    else:

        report[
            "warnings"
        ] = [
            "subtitle_ass_not_discovered_using_prior_vi1330_certification"
        ]


    save_json(
        TMP
        / "subtitle_qa.json",
        report
    )


    return report


if __name__ == "__main__":

    report = run()


    print(
        "VI1400 SUBTITLE QA=",
        report[
            "status"
        ]
    )

    print(
        "BEST=",
        report[
            "best"
        ]
    )

    print(
        "WARNINGS=",
        report[
            "warnings"
        ]
    )
