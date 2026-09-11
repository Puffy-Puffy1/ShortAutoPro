#!/usr/bin/env python3

import hashlib
import tempfile

from pathlib import Path


from vi1510_1_23_runtime_inventory_v3 import (
    enrich_scene_usage,
    inventory_metadata_records,
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
        failed.append(name)


def main():
    failed = []

    print()
    print(
        "=============================================="
    )
    print(
        " VI1510.1 V3 RUNTIME INVENTORY REGRESSION"
    )
    print(
        "=============================================="
    )

    with tempfile.TemporaryDirectory() as td:

        root = Path(td)

        prepared = (
            root
            / "prepared.jpg"
        )

        prepared.write_bytes(
            b"prepared-asset"
        )

        prepared_sha = hashlib.sha256(
            prepared.read_bytes()
        ).hexdigest()

        original = (
            root
            / "original.jpg"
        )

        original.write_bytes(
            b"original-source"
        )

        run = {
            "topic":
                "Generic historical benchmark",

            "short_id":
                "generic_001",

            "source_assets": [
                {
                    "scene":
                        1,

                    "prepared_asset":
                        str(prepared),

                    "sha256":
                        prepared_sha,

                    "selected_source": {
                        "source_group":
                            "GENERIC:SOURCE:001",

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
                            str(original),
                    },

                    "query":
                        "QUERY MUST NEVER BE EVIDENCE",
                }
            ],
        }

        scene_usage = {
            "used_assets": [
                {
                    "scene":
                        1,

                    "path":
                        str(prepared),

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
            resolved={
                "partitions": [
                    run
                ]
            },
            fallback_inventory=None,
            run_dir=run_dir,
        )

        row = (
            enriched[
                "used_assets"
            ][0]
        )

        check(
            "INVENTORY_ASSET_MATCHED",
            row[
                "runtime_inventory_v3"
            ][
                "matched"
            ],
            True,
            failed,
        )

        check(
            "SOURCE_GROUP_TRANSPORTED",
            row.get(
                "source_group"
            ),
            "GENERIC:SOURCE:001",
            failed,
        )

        check(
            "SOURCE_URL_TRANSPORTED",
            row.get(
                "source_url"
            ),
            (
                "https://example.org/"
                "original.jpg"
            ),
            failed,
        )

        metadata_records = (
            inventory_metadata_records(
                run=run,
                partition=run,
                resolved={
                    "partitions": [
                        run
                    ]
                },
            )
        )

        check(
            "INVENTORY_METADATA_PRESENT",
            bool(
                metadata_records
            ),
            True,
            failed,
        )

        metadata = {
            "records":
                metadata_records
        }

        lineage = run_lineage(
            enriched,
            metadata,
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

        unrelated = {
            "used_assets": [
                {
                    "scene":
                        1,

                    "path":
                        str(
                            root
                            / "unrelated.jpg"
                        ),

                    "sha256":
                        "f"
                        * 64,
                }
            ]
        }

        rejected = enrich_scene_usage(
            unrelated,
            run=run,
            partition=run,
            resolved={
                "partitions": [
                    run
                ]
            },
            run_dir=run_dir,
        )

        check(
            "SCENE_ONLY_REJECTED",
            rejected[
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
        raise SystemExit(1)

    print(
        "STATUS: VI1510_1_V3_RUNTIME_INVENTORY_CERTIFIED"
    )


if __name__ == "__main__":
    main()
