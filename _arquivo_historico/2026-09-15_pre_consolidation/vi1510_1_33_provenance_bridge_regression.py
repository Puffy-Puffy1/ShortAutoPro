#!/usr/bin/env python3

from vi1510_1_25_provenance_bridge import (
    enrich_scene_usage,
)


def check(
    name,
    actual,
    expected,
    failed,
):
    passed = (
        actual
        ==
        expected
    )


    print(
        name,
        "=",
        "PASS"
        if passed
        else "FAIL",
        "| expected=",
        expected,
        "| actual=",
        actual,
    )


    if not passed:

        failed.append(
            name
        )


def main():
    failed = []


    print()
    print(
        "=============================================="
    )

    print(
        " VI1510.1 V2.3 PROVENANCE BRIDGE REGRESSION"
    )

    print(
        "=============================================="
    )


    digest = (
        "a"
        * 64
    )


    scene_usage = {
        "used_assets": [
            {
                "scene":
                    1,

                "path":
                    "/work/rendered_scene_01.jpg",

                "sha256":
                    digest,
            }
        ]
    }


    run = {
        "topic":
            "Generic historical topic",

        "sources": [
            {
                "sha256":
                    digest,

                "source_group":
                    "GENERIC:123",

                "source_url":
                    (
                        "https://example.org/"
                        "historic-photo.jpg"
                    ),

                "title":
                    "Historic Photo",

                "provider":
                    "EXAMPLE",
            }
        ],
    }


    result = enrich_scene_usage(
        scene_usage,
        run,
        {},
    )


    asset = result[
        "used_assets"
    ][0]


    check(
        "SHA_LINKED",
        asset[
            "provenance_bridge"
        ][
            "linked"
        ],
        True,
        failed,
    )


    check(
        "SOURCE_GROUP_TRANSPORTED",
        asset.get(
            "source_group"
        ),
        "GENERIC:123",
        failed,
    )


    check(
        "SOURCE_URL_TRANSPORTED",
        asset.get(
            "source_url"
        ),
        (
            "https://example.org/"
            "historic-photo.jpg"
        ),
        failed,
    )


    # Scene alone must not create provenance.
    unrelated = enrich_scene_usage(
        {
            "used_assets": [
                {
                    "scene":
                        7,

                    "path":
                        "/tmp/a.jpg",

                    "sha256":
                        "b"
                        * 64,
                }
            ]
        },
        {
            "sources": [
                {
                    "scene":
                        7,

                    "sha256":
                        "c"
                        * 64,

                    "source_group":
                        "OTHER:1",
                }
            ]
        },
        {},
    )


    check(
        "SCENE_ONLY_REJECTED",
        unrelated[
            "used_assets"
        ][0][
            "provenance_bridge"
        ][
            "linked"
        ],
        False,
        failed,
    )


    print()
    print(
        "FAILED:",
        failed
    )


    if failed:

        raise SystemExit(
            1
        )


    print(
        "VI1510_1_V2_3_PROVENANCE_BRIDGE_CERTIFIED"
    )


if __name__ == "__main__":
    main()
