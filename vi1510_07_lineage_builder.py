#!/usr/bin/env python3

import os
import re

from pathlib import Path
from urllib.parse import unquote, urlparse

from vi1510_01_common import (
    norm,
    save_json,
)


def url_basename(
    value,
):
    try:

        return Path(
            unquote(
                urlparse(
                    value
                ).path
            )
        ).name.lower()

    except Exception:
        return ""


def canonical_path(
    value,
):
    if not value:
        return ""

    try:
        return str(
            Path(
                value
            )
            .expanduser()
            .resolve()
        )

    except Exception:
        return str(
            value
        )


def link_score(
    asset,
    record,
):
    score = 0

    reasons = []


    asset_path = canonical_path(
        asset[
            "path"
        ]
    )


    asset_name = Path(
        asset_path
    ).name.lower()


    local = canonical_path(
        record.get(
            "local_path"
        )
    )


    if (
        local

        and

        local
        ==
        asset_path
    ):
        score += 100

        reasons.append(
            "exact_local_path"
        )


    if (
        local

        and

        Path(
            local
        ).name.lower()
        ==
        asset_name
    ):
        score += 45

        reasons.append(
            "local_basename"
        )


    if (
        record.get(
            "sha256"
        )

        and

        record[
            "sha256"
        ]
        ==
        asset[
            "sha256"
        ]
    ):
        score += 120

        reasons.append(
            "sha256"
        )


    remote_name = url_basename(
        record.get(
            "source_url"
        )
    )


    if (
        remote_name

        and

        (
            remote_name
            ==
            asset_name

            or

            Path(
                remote_name
            ).stem
            in Path(
                asset_name
            ).stem
        )
    ):
        score += 35

        reasons.append(
            "remote_basename"
        )


    title = norm(
        record.get(
            "title"
        )
    )


    asset_stem = norm(
        re.sub(
            r"[_\-]+",
            " ",
            Path(
                asset_name
            ).stem
        )
    )


    if (
        title

        and

        asset_stem

        and

        (
            title
            in asset_stem

            or

            asset_stem
            in title
        )
    ):
        score += 25

        reasons.append(
            "title_filename"
        )


    if (
        asset.get(
            "scene"
        )

        and

        record.get(
            "scene"
        )
    ):

        try:

            if int(
                record[
                    "scene"
                ]
            ) == int(
                asset[
                    "scene"
                ]
            ):
                score += 15

                reasons.append(
                    "scene_number"
                )

        except Exception:
            pass


    return (
        score,
        reasons,
    )


def build(
    inventory,
    metadata,
    run_dir,
):
    assets = (
        inventory.get(
            "source_assets"
        )
        or []
    )


    records = (
        metadata.get(
            "records"
        )
        or []
    )


    lineage = []


    for asset in assets:

        matches = []


        for index, record in enumerate(
            records
        ):

            score, reasons = link_score(
                asset,
                record
            )


            if score >= 25:

                matches.append({
                    "record_index":
                        index,

                    "score":
                        score,

                    "reasons":
                        reasons,
                })


        matches.sort(
            key=lambda item:
                item[
                    "score"
                ],
            reverse=True,
        )


        lineage.append({
            **asset,

            "linked_records":
                matches[
                    :5
                ],

            "provenance_linked":
                bool(
                    matches
                ),
        })


    linked_assets = sum(
        item[
            "provenance_linked"
        ]

        for item in lineage
    )


    unique_hashes = {
        item[
            "sha256"
        ]

        for item in lineage
    }


    linked_hashes = {
        item[
            "sha256"
        ]

        for item in lineage

        if item[
            "provenance_linked"
        ]
    }


    report = {
        "assets":
            lineage,

        "asset_count":
            len(
                lineage
            ),

        "unique_asset_count":
            len(
                unique_hashes
            ),

        "linked_asset_count":
            linked_assets,

        "linked_unique_asset_count":
            len(
                linked_hashes
            ),

        "record_count":
            len(
                records
            ),
    }


    save_json(
        run_dir
        / "lineage.json",
        report
    )


    return report
