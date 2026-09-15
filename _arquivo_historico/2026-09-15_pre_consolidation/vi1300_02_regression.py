#!/usr/bin/env python3

from vi1300_01_presentation_safety import (
    choose_strategy,
)


def test_scene(
    *,
    content_type,
    source_class,
    constraints=None,
):
    return {
        "content_type":
            content_type,

        "source_class":
            source_class,

        "presentation_constraints":
            constraints
            or [],

        "semantic_mode":
            "DIRECT",

        "generic":
            False,
    }


def main():
    tests = []


    low_video = choose_strategy(
        test_scene(
            content_type="video/webm",
            source_class="CASE_ARCHIVE",
        ),
        {
            "width":
                352,

            "height":
                288,
        },
    )


    tests.append((
        "LOW_RES_ARCHIVE_NOT_FULLSCREEN",
        low_video[
            "fullscreen_allowed"
        ],
        False,
    ))


    tests.append((
        "LOW_RES_ARCHIVE_INSET",
        low_video[
            "strategy"
        ],
        "ARCHIVAL_INSET",
    ))


    high_image = choose_strategy(
        test_scene(
            content_type="image/jpeg",
            source_class="GENERIC",
        ),
        {
            "width":
                1920,

            "height":
                2560,
        },
    )


    tests.append((
        "HIGH_RES_IMAGE_COVER",
        high_image[
            "strategy"
        ],
        "IMAGE_COVER",
    ))


    pdf = choose_strategy(
        test_scene(
            content_type="application/pdf",
            source_class="CASE_ENTITY",
        ),
        {
            "width":
                None,

            "height":
                None,
        },
    )


    tests.append((
        "PDF_DOCUMENT_PREVIEW",
        pdf[
            "strategy"
        ],
        "DOCUMENT_PAGE_PREVIEW",
    ))


    tests.append((
        "PDF_NOT_FULLSCREEN",
        pdf[
            "fullscreen_allowed"
        ],
        False,
    ))


    explicit_no_fullscreen = (
        choose_strategy(
            test_scene(
                content_type="image/jpeg",
                source_class="CASE_ENTITY",
                constraints=[
                    "NO_FULLSCREEN"
                ],
            ),
            {
                "width":
                    4000,

                "height":
                    3000,
            },
        )
    )


    tests.append((
        "EXPLICIT_NO_FULLSCREEN_PRESERVED",
        explicit_no_fullscreen[
            "fullscreen_allowed"
        ],
        False,
    ))


    failed = []


    print()
    print(
        "=============================================="
    )

    print(
        " VI1300 PRESENTATION REGRESSION"
    )

    print(
        "=============================================="
    )


    for name, actual, expected in tests:

        passed = (
            actual == expected
        )


        print(
            name,
            "=",
            (
                "PASS"
                if passed
                else "FAIL"
            ),
            "| expected=",
            expected,
            "| actual=",
            actual
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
        "VI1300_PRESENTATION_REGRESSION_CERTIFIED"
    )


if __name__ == "__main__":
    main()
