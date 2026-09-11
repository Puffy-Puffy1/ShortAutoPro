#!/usr/bin/env python3

import tempfile

from pathlib import Path


from vi1510_1_25_scene_usage import (
    extract_scene_sets,
)

from vi1510_1_29_lineage_v2 import (
    run as run_lineage,
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
        " VI1510.1 V2.6 SCENE PROVENANCE REGRESSION"
    )
    print(
        "=============================================="
    )


    with tempfile.TemporaryDirectory() as td:

        root = Path(
            td
        )

        asset = (
            root
            / "prepared_scene.jpg"
        )

        asset.write_bytes(
            b"prepared"
        )

        source = (
            root
            / "original.jpg"
        )

        source.write_bytes(
            b"original"
        )

        origin = (
            root
            / "scene_plan.json"
        )

        scene_data = {
            "scenes": [
                {
                    "scene":
                        1,

                    "prepared_asset":
                        str(
                            asset
                        ),

                    "selected_source": {
                        "source_group":
                            "GENERIC:SOURCE:1",

                        "source_url":
                            (
                                "https://example.org/"
                                "original.jpg"
                            ),

                        "title":
                            "Generic Historical Photograph",

                        "provider":
                            "EXAMPLE",

                        "license":
                            "CC BY 4.0",

                        "local_path":
                            str(
                                source
                            ),
                    },

                    "query": {
                        "source_url":
                            "https://bad.example/query.jpg",

                        "source_group":
                            "QUERY:MUST:NOT:COUNT",
                    },
                }
            ]
        }


        sets = extract_scene_sets(
            scene_data,
            origin,
        )


        rows = [
            row

            for group in sets

            for row in group

            if (
                Path(
                    row.get(
                        "path",
                        ""
                    )
                )
                ==
                asset
            )
        ]


        check(
            "USED_ASSET_FOUND",
            len(
                rows
            ),
            1,
            failed,
        )


        if rows:

            row = rows[
                0
            ]

            check(
                "PROVENANCE_CAPTURED",
                (
                    row.get(
                        "scene_provenance",
                        {}
                    ).get(
                        "status"
                    )
                ),
                "CAPTURED",
                failed,
            )

            check(
                "SOURCE_GROUP_CAPTURED",
                row.get(
                    "source_group"
                ),
                "GENERIC:SOURCE:1",
                failed,
            )

            check(
                "SOURCE_URL_CAPTURED",
                row.get(
                    "source_url"
                ),
                (
                    "https://example.org/"
                    "original.jpg"
                ),
                failed,
            )

            check(
                "QUERY_NOT_CAPTURED",
                (
                    row.get(
                        "source_group"
                    )
                    !=
                    "QUERY:MUST:NOT:COUNT"
                ),
                True,
                failed,
            )


            metadata = {
                "records": [
                    {
                        "source_group":
                            "GENERIC:SOURCE:1",

                        "source_url":
                            (
                                "https://example.org/"
                                "original.jpg"
                            ),

                        "title":
                            "Generic Historical Photograph",

                        "provider":
                            "EXAMPLE",

                        "license":
                            "CC BY 4.0",

                        "local_path":
                            str(
                                source
                            ),
                    }
                ]
            }


            out = (
                root
                / "lineage"
            )

            lineage = run_lineage(
                {
                    "used_assets": [
                        row
                    ]
                },
                metadata,
                out,
            )


            check(
                "REAL_LINEAGE_LINK",
                lineage.get(
                    "strictly_linked_assets"
                ),
                1,
                failed,
            )


        ambiguous_scene = {
            "scene":
                2,

            "prepared_asset":
                str(
                    asset
                ),

            "sources": [
                {
                    "source_group":
                        "GENERIC:A",

                    "source_url":
                        "https://example.org/a.jpg",
                },
                {
                    "source_group":
                        "GENERIC:B",

                    "source_url":
                        "https://example.org/b.jpg",
                },
            ],
        }


        from vi1510_1_25_scene_usage import (
            _vi1510_v26_scene_provenance,
        )


        ambiguous = (
            _vi1510_v26_scene_provenance(
                ambiguous_scene,
                asset,
            )
        )


        check(
            "AMBIGUOUS_NOT_CAPTURED",
            (
                ambiguous[
                    "scene_provenance"
                ][
                    "status"
                ]
            ),
            "AMBIGUOUS",
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
        "STATUS: VI1510_1_V2_6_SCENE_PROVENANCE_CERTIFIED"
    )


if __name__ == "__main__":
    main()
