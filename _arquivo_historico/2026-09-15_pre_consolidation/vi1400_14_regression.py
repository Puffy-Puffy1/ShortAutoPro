#!/usr/bin/env python3

from vi1400_04_frame_metrics import (
    H,
    W,
    stats,
)

from vi1400_07_subtitle_qa import (
    ass_time,
    visible_text,
)


def main():
    tests = []


    flat = (
        bytes([
            250
        ])
        *
        (
            W
            *
            H
        )
    )


    textured = bytes(
        (
            index
            *
            37
        )
        %
        256

        for index in range(
            W
            *
            H
        )
    )


    tests.append((
        "WHITE_FRAME_PENALIZED",

        stats(
            flat
        )[
            "visual_strength"
        ]
        <
        stats(
            textured
        )[
            "visual_strength"
        ],
    ))


    tests.append((
        "ASS_TAGS_REMOVED",

        visible_text(
            r"{\b1}Olá\N mundo"
        )
        ==
        "Olá mundo",
    ))


    tests.append((
        "ASS_TIME_PARSE",

        abs(
            ass_time(
                "0:00:01.50"
            )
            -
            1.5
        )
        < 0.001,
    ))


    failed = []


    for name, passed in tests:

        print(
            name,
            "=",
            (
                "PASS"
                if passed
                else "FAIL"
            )
        )


        if not passed:

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
        "VI1400_REGRESSION_CERTIFIED"
    )


if __name__ == "__main__":

    main()
