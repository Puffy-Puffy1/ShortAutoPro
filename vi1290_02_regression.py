#!/usr/bin/env python3

from vi1290_01_asset_planner import (
    required_crop,
    upscale_factor,
    image_strategy,
)


POLICY = {
    "target": {
        "width":
            1080,

        "height":
            1920,

        "aspect_ratio":
            0.5625,
    },

    "quality": {
        "maximum_fullscreen_upscale":
            1.35,

        "maximum_context_upscale":
            2.50,

        "minimum_insert_width":
            480,

        "minimum_insert_height":
            270,
    },
}


def main():
    tests = []


    portrait = image_strategy(
        {
            "width":
                2160,

            "height":
                3840,
        },
        POLICY,
        []
    )


    tests.append((
        "NATIVE_VERTICAL_FULLSCREEN",
        portrait[
            "strategy"
        ]
        ==
        "FULLSCREEN_CENTER_CROP"
    ))


    landscape = image_strategy(
        {
            "width":
                4000,

            "height":
                3000,
        },
        POLICY,
        []
    )


    tests.append((
        "HIGH_RES_LANDSCAPE_PLANNABLE",
        landscape[
            "ready"
        ]
        is True
    ))


    low = image_strategy(
        {
            "width":
                352,

            "height":
                288,
        },
        POLICY,
        []
    )


    tests.append((
        "VERY_LOW_RES_HELD",
        low[
            "ready"
        ]
        is False
    ))


    restricted = image_strategy(
        {
            "width":
                3000,

            "height":
                4000,
        },
        POLICY,
        [
            "NO_FULLSCREEN"
        ]
    )


    tests.append((
        "NO_FULLSCREEN_CONSTRAINT_ENFORCED",
        restricted[
            "strategy"
        ]
        !=
        "FULLSCREEN_CENTER_CROP"
    ))


    hotel_cecil = image_strategy(
        {
            "width":
                523,

            "height":
                917,
        },
        POLICY,
        [
            "NO_FULLSCREEN"
        ]
    )


    tests.append((
        "LOW_RES_HOTEL_CONTEXT_NOT_FULLSCREEN",
        hotel_cecil[
            "strategy"
        ]
        !=
        "FULLSCREEN_CENTER_CROP"
    ))


    print()
    print(
        "=============================================="
    )

    print(
        " VI1290 RENDER READINESS REGRESSION"
    )

    print(
        "=============================================="
    )


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
        "VI1290_RENDER_READINESS_REGRESSION_CERTIFIED"
    )


if __name__ == "__main__":
    main()
