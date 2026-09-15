#!/usr/bin/env python3

import hashlib
import tempfile

from pathlib import Path


from vi1510_1_23_runtime_inventory_v3 import (
    enrich_scene_usage,
    inventory_metadata_records,
    recover_inventory,
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
        " VI1510.1 V3.1 GENERIC INVENTORY REGRESSION"
    )

    print(
        "=============================================="
    )


    with tempfile.TemporaryDirectory() as td:

        root = Path(
            td
        )


        prepared = (
            root
            / "prepared_scene.jpg"
        )

        prepared.write_bytes(
            b"prepared-scene"
        )


        prepared_sha = hashlib.sha256(
            prepared.read_bytes()
        ).hexdigest()


        original = (
            root
            / "original_source.jpg"
        )

        original.write_bytes(
            b"original-source"
        )


        # Deliberately NOT called source_assets.
        run = {
            "topic":
                "Generic historical subject",

            "short_id":
                "generic_test",

            "selected_assets": [
                {
                    "scene":
                        1,

                    "prepared_asset":
                        str(
                            prepared
                        ),

                    "sha256":
                        prepared_sha,

                    "selected_source": {
                        "source_group":
                            "GENERIC:SOURCE:31",

                        "source_url":
                            (
                                "https://example.org/"
                                "original-source.jpg"
                            ),

                        "title":
                            "Generic Historical Source",

                        "provider":
                            "EXAMPLE",

                        "license":
                            "CC BY 4.0",

                        "local_path":
                            str(
                                original
                            ),
                    },

                    "query":
                        (
                            "THIS QUERY MUST "
                            "NEVER BECOME EVIDENCE"
                        ),
                }
            ],
        }


        resolved = {
            "partitions": [
                run
            ]
        }


        inventory = recover_inventory(
            run=run,
            partition=run,
            resolved=resolved,
        )


        check(
            "GENERIC_INVENTORY_DISCOVERED",
            len(
                inventory
            ),
            1,
            failed,
        )


        scene_usage = {
            "used_assets": [
                {
                    "scene":
                        1,

                    "path":
                        str(
                            prepared
                        ),

                    "sha256":
                        prepared_sha,
                }
            ]
        }


        run_dir = (
            root
            / "run"
        )

        run_dir.mkdir()


        enriched = enrich_scene_usage(
            scene_usage,
            run=run,
            partition=run,
            resolved=resolved,
            fallback_inventory=None,
            run_dir=run_dir,
        )


        row = (
            enriched[
                "used_assets"
            ][0]
        )


        check(
            "EXACT_ASSET_MATCHED",
            row[
                "runtime_inventory_v3"
            ][
                "matched"
            ],
            True,
            failed,
        )


        check(
            "PATH_OR_SHA_EVIDENCE_PRESENT",
            bool(
                set(
                    row[
                        "runtime_inventory_v3"
                    ][
                        "reasons"
                    ]
                )
                &
                {
                    "runtime_inventory_sha256_exact",
                    "runtime_inventory_path_exact",
                }
            ),
            True,
            failed,
        )


        check(
            "SOURCE_GROUP_TRANSPORTED",
            row.get(
                "source_group"
            ),
            "GENERIC:SOURCE:31",
            failed,
        )


        check(
            "SOURCE_URL_TRANSPORTED",
            row.get(
                "source_url"
            ),
            (
                "https://example.org/"
                "original-source.jpg"
            ),
            failed,
        )


        records = inventory_metadata_records(
            run=run,
            partition=run,
            resolved=resolved,
        )


        check(
            "METADATA_FROM_GENERIC_INVENTORY",
            len(
                records
            ),
            1,
            failed,
        )


        lineage = run_lineage(
            enriched,
            {
                "records":
                    records
            },
            run_dir,
        )


        check(
            "END_TO_END_LINEAGE",
            lineage.get(
                "strictly_linked_assets"
            ),
            1,
            failed,
        )


        # Same scene number, wrong path and wrong hash.
        # It MUST remain unlinked.
        unrelated = enrich_scene_usage(
            {
                "used_assets": [
                    {
                        "scene":
                            1,

                        "path":
                            str(
                                root
                                / "different.jpg"
                            ),

                        "sha256":
                            "f"
                            * 64,
                    }
                ]
            },
            run=run,
            partition=run,
            resolved=resolved,
            fallback_inventory=None,
            run_dir=run_dir,
        )


        check(
            "SCENE_ONLY_STILL_REJECTED",
            unrelated[
                "used_assets"
            ][0][
                "runtime_inventory_v3"
            ][
                "matched"
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
        "STATUS: VI1510_1_V3_1_GENERIC_INVENTORY_CERTIFIED"
    )


if __name__ == "__main__":
    main()
