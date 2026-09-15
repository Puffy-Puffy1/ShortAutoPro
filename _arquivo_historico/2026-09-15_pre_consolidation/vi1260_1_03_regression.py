#!/usr/bin/env python3

from vi1260_1_01_strict_semantic_audit import (
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


def item(
    *,
    title,
    mime,
    text,
    source_class,
    mode="DIRECT",
):
    return {
        "candidate": {
            "title":
                title,

            "mime":
                mime,

            "description":
                text,

            "evidence_text":
                text,

            "metadata_text":
                text,

            "entity_mentions": [
                "Elisa Lam"
            ],

            "source_class":
                source_class,

            "source_group":
                "TEST:"
                + title,

            "generic":
                source_class
                == "GENERIC",

            "license":
                "CC BY 4.0",

            "width":
                2400,

            "height":
                3200,

            "remote_url":
                "https://upload.wikimedia.org/test.jpg",
        },

        "evaluation": {
            "passed":
                True,

            "mode":
                mode,

            "query_used_as_evidence":
                False,
        },

        "rank":
            50,
    }


def scene(
    number,
):
    return {
        "scene":
            number
    }


def main():
    tests = []


    autopsy = strict_item(
        scene(
            3
        ),
        item(
            title=(
                "File:Autopsy Report "
                "of Elisa Lam.pdf"
            ),
            mime="application/pdf",
            text=(
                "Autopsy Report of Elisa Lam"
            ),
            source_class="CASE_ENTITY",
        ),
        ENTITIES,
    )


    tests.append((
        "SCENE3_AUTOPSY_DOCUMENT_REJECTED",
        autopsy[
            "evaluation"
        ][
            "passed"
        ],
        False,
    ))


    elevator = strict_item(
        scene(
            3
        ),
        item(
            title=(
                "File:Elisa Lam elevator video.webm"
            ),
            mime="video/webm",
            text=(
                "Elisa Lam elevator "
                "surveillance video"
            ),
            source_class="CASE_ARCHIVE",
        ),
        ENTITIES,
    )


    tests.append((
        "SCENE3_CASE_PERSON_VIDEO_ALLOWED",
        elevator[
            "evaluation"
        ][
            "passed"
        ],
        True,
    ))


    railroad = strict_item(
        scene(
            6
        ),
        item(
            title=(
                "File:Railroad station entrance.jpg"
            ),
            mime="image/jpeg",
            text=(
                "Main entrance to a railroad station"
            ),
            source_class="CASE_ENTITY",
        ),
        ENTITIES,
    )


    tests.append((
        "SCENE6_RAILROAD_STATION_REJECTED",
        railroad[
            "evaluation"
        ][
            "passed"
        ],
        False,
    ))


    hallway = strict_item(
        scene(
            6
        ),
        item(
            title=(
                "File:Hotel hallway doorway.jpg"
            ),
            mime="image/jpeg",
            text=(
                "Hotel hallway corridor "
                "with doorway"
            ),
            source_class="GENERIC",
        ),
        ENTITIES,
    )


    tests.append((
        "SCENE6_HALLWAY_DOORWAY_ALLOWED",
        hallway[
            "evaluation"
        ][
            "passed"
        ],
        True,
    ))


    pdf8 = strict_item(
        scene(
            8
        ),
        item(
            title=(
                "File:Investigation report.pdf"
            ),
            mime="application/pdf",
            text=(
                "Investigation document"
            ),
            source_class="CASE_ENTITY",
        ),
        ENTITIES,
    )


    tests.append((
        "SCENE8_DOCUMENT_REJECTED",
        pdf8[
            "evaluation"
        ][
            "passed"
        ],
        False,
    ))


    cctv = strict_item(
        scene(
            8
        ),
        item(
            title=(
                "File:CCTV surveillance monitor.jpg"
            ),
            mime="image/jpeg",
            text=(
                "CCTV security camera "
                "surveillance monitor"
            ),
            source_class="GENERIC",
        ),
        ENTITIES,
    )


    tests.append((
        "SCENE8_SURVEILLANCE_CONTEXT_ALLOWED",
        cctv[
            "evaluation"
        ][
            "passed"
        ],
        True,
    ))


    failed = []


    print()
    print(
        "=============================================="
    )

    print(
        " VI1260.1 STRICT REGRESSION"
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


    print(
        "FAILED:",
        failed
    )


    if failed:
        raise SystemExit(
            1
        )


    print(
        "VI1260_1_STRICT_REGRESSION_CERTIFIED"
    )


if __name__ == "__main__":
    main()
