#!/usr/bin/env python3

from vi1260_1_01_strict_semantic_audit import (
    media_kind,
    strict_item,
)


ENTITIES = {
    "primary_person": {
        "name":
            "Elisa Lam"
    },

    "primary_location": {
        "name":
            "Hotel Cecil"
    },
}


def candidate_item(
    *,
    title,
    mime,
    text,
    source_class,
    source_group,
    generic=False,
    technical_ok=True,
):
    width = (
        2400
        if technical_ok
        else 352
    )

    height = (
        3200
        if technical_ok
        else 288
    )


    return {
        "candidate": {
            "title":
                title,

            "mime":
                mime,

            "description":
                text,

            "metadata_text":
                text,

            "evidence_text":
                text,

            "entity_mentions": [
                "Elisa Lam",
                "Hotel Cecil",
            ],

            "source_class":
                source_class,

            "source_group":
                source_group,

            "generic":
                generic,

            "license":
                "CC BY 4.0",

            "width":
                width,

            "height":
                height,

            "remote_url":
                "https://upload.wikimedia.org/test"
                + (
                    ".webm"
                    if "video/"
                    in mime
                    else ".jpg"
                ),
        },

        "evaluation": {
            "passed":
                True,

            "mode":
                "DIRECT",

            "query_used_as_evidence":
                False,
        },

        "rank":
            50.0,
    }


def scene(
    number,
):
    return {
        "scene":
            number
    }


def check(
    name,
    actual,
    expected,
    failed,
):
    passed = (
        actual == expected
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
        actual
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
        " VI1260.2 SEMANTIC REPAIR REGRESSION"
    )

    print(
        "=============================================="
    )


    # MIME may be inferred from extension.
    extension_only = {
        "title":
            "File:Elisa Lam elevator video.webm",

        "raw_metadata": {},
    }


    check(
        "MEDIA_KIND_WEBM_EXTENSION",
        media_kind(
            extension_only
        ),
        "VIDEO",
        failed
    )


    scene3_archive = strict_item(
        scene(3),
        candidate_item(
            title=(
                "File:Elisa Lam elevator video.webm"
            ),
            mime="video/webm",
            text=(
                "Elisa Lam elevator surveillance video"
            ),
            source_class="CASE_ARCHIVE",
            source_group=(
                "CASE:ELISA_LAM_ELEVATOR_VIDEO"
            ),
            technical_ok=False,
        ),
        ENTITIES,
    )


    check(
        "SCENE3_LOW_RES_CASE_ARCHIVE_CONTEXT_ALLOWED",
        scene3_archive[
            "evaluation"
        ][
            "passed"
        ],
        True,
        failed
    )


    check(
        "SCENE3_LOW_RES_NOT_FULLSCREEN",
        (
            "NO_FULLSCREEN"
            in
            scene3_archive[
                "evaluation"
            ].get(
                "presentation_constraints",
                []
            )
        ),
        True,
        failed
    )


    scene3_pdf = strict_item(
        scene(3),
        candidate_item(
            title=(
                "File:Autopsy Report of Elisa Lam.pdf"
            ),
            mime="application/pdf",
            text=(
                "Autopsy Report of Elisa Lam"
            ),
            source_class="CASE_ENTITY",
            source_group="CASE:AUTOPSY",
        ),
        ENTITIES,
    )


    check(
        "SCENE3_AUTOPSY_STILL_REJECTED",
        scene3_pdf[
            "evaluation"
        ][
            "passed"
        ],
        False,
        failed
    )


    scene6_station = strict_item(
        scene(6),
        candidate_item(
            title=(
                "File:Railroad station entrance.jpg"
            ),
            mime="image/jpeg",
            text=(
                "Main entrance to railroad station"
            ),
            source_class="GENERIC",
            source_group="GENERIC:STATION",
            generic=True,
        ),
        ENTITIES,
    )


    check(
        "SCENE6_STATION_STILL_REJECTED",
        scene6_station[
            "evaluation"
        ][
            "passed"
        ],
        False,
        failed
    )


    scene6_hallway = strict_item(
        scene(6),
        candidate_item(
            title=(
                "File:Conrad Indianapolis hotel hallway.jpg"
            ),
            mime="image/jpeg",
            text=(
                "Hotel hallway corridor interior"
            ),
            source_class="GENERIC",
            source_group="GENERIC:HALLWAY2",
            generic=True,
        ),
        ENTITIES,
    )


    check(
        "SCENE6_HALLWAY_CONTEXT_ALLOWED",
        scene6_hallway[
            "evaluation"
        ][
            "passed"
        ],
        True,
        failed
    )


    check(
        "SCENE6_DOES_NOT_CLAIM_HIDING",
        (
            "DO_NOT_CLAIM_HIDING_ACTION"
            in
            scene6_hallway[
                "evaluation"
            ].get(
                "presentation_constraints",
                []
            )
        ),
        True,
        failed
    )


    scene8_archive = strict_item(
        scene(8),
        candidate_item(
            title=(
                "File:Elisa Lam elevator video.webm"
            ),
            mime="video/webm",
            text=(
                "Elisa Lam elevator surveillance video"
            ),
            source_class="CASE_ARCHIVE",
            source_group=(
                "CASE:ELISA_LAM_ELEVATOR_VIDEO"
            ),
            technical_ok=False,
        ),
        ENTITIES,
    )


    check(
        "SCENE8_ARCHIVAL_EVIDENCE_CONTEXT_ALLOWED",
        scene8_archive[
            "evaluation"
        ][
            "passed"
        ],
        True,
        failed
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
        "VI1260_2_SEMANTIC_REPAIR_REGRESSION_CERTIFIED"
    )


if __name__ == "__main__":
    main()
