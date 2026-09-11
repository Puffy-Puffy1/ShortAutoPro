#!/usr/bin/env python3

from vi1330_03_motion_engine import (
    image_filter,
)


def main():
    tests = []


    strategies = [
        "HOTEL_SIGN_TIGHT",
        "HOTEL_FACADE_WIDE",
        "HALLWAY_MONO_PUSH",
        "HALLWAY_RED_DRIFT",
        "ELEVATOR_INTERIOR_PUSH",
        "CCTV_CAMERA_FOCUS",
        "MEDICAL_GRAPH_FOCUS",
        "WORKER_SUBJECT_FOCUS",
        "WATER_TANK_SUBJECT_FOCUS",
        "AUTOPSY_DOCUMENT_FOCUS",
    ]


    outputs = {
        strategy:
            image_filter(
                strategy,
                120
            )

        for strategy in strategies
    }


    tests.append((
        "ALL_STRATEGIES_RETURN_FILTER",
        all(
            isinstance(
                value,
                str
            )
            and
            len(
                value
            )
            > 20

            for value in (
                outputs.values()
            )
        )
    ))


    tests.append((
        "S2_AND_S3_FILTERS_DIFFER",
        outputs[
            "HOTEL_SIGN_TIGHT"
        ]
        !=
        outputs[
            "HOTEL_FACADE_WIDE"
        ]
    ))


    tests.append((
        "WORKER_HAS_CROP",
        "crop="
        in
        outputs[
            "WORKER_SUBJECT_FOCUS"
        ]
    ))


    tests.append((
        "WATER_TANK_HAS_CROP",
        "crop="
        in
        outputs[
            "WATER_TANK_SUBJECT_FOCUS"
        ]
    ))


    tests.append((
        "MEDICAL_GRAPH_HAS_CROP",
        "crop="
        in
        outputs[
            "MEDICAL_GRAPH_FOCUS"
        ]
    ))


    tests.append((
        "DOCUMENT_HAS_CROP",
        "crop="
        in
        outputs[
            "AUTOPSY_DOCUMENT_FOCUS"
        ]
    ))


    failed = []


    print()
    print(
        "=============================================="
    )
    print(
        " VI1330 PUBLICATION QUALITY REGRESSION"
    )
    print(
        "=============================================="
    )


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
        "VI1330_REGRESSION_CERTIFIED"
    )


if __name__ == "__main__":
    main()
