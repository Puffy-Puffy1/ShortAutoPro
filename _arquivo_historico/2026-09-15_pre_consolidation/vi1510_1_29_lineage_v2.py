#!/usr/bin/env python3

import re

from pathlib import Path

from urllib.parse import (
    parse_qsl,
    unquote,
    urlencode,
    urlsplit,
    urlunsplit,
)


from vi1510_01_common import (
    norm,
    save_json,
)


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
        ).strip()


def canonical_url(
    value,
):
    value = str(
        value
        or ""
    ).strip()


    if not value:
        return ""


    try:

        parts = urlsplit(
            value
        )


        if parts.scheme not in {
            "http",
            "https",
        }:

            return ""


        query = [
            (
                key,
                val,
            )

            for key, val
            in parse_qsl(
                parts.query,
                keep_blank_values=True,
            )

            if not key.lower().startswith(
                "utm_"
            )
        ]


        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                unquote(
                    parts.path
                ),
                urlencode(
                    query,
                    doseq=True,
                ),
                "",
            )
        ).rstrip("/")


    except Exception:

        return ""


def filename_from_url(
    value,
):
    url = canonical_url(
        value
    )


    if not url:
        return ""


    try:

        return Path(
            urlsplit(
                url
            ).path
        ).name.lower()


    except Exception:

        return ""


def canonical_title(
    value,
):
    value = unquote(
        str(
            value
            or ""
        )
    )


    value = re.sub(
        r"^file\s*:\s*",
        "",
        value,
        flags=re.I,
    )


    value = Path(
        value
    ).stem


    value = norm(
        value
    )


    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )


    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def candidate_urls(
    value,
):
    keys = [
        "source_url",
        "remote_url",
        "media_url",
        "original_url",
        "download_url",
        "final_url",
        "url",
        "descriptionurl",
    ]


    urls = set()


    for key in keys:

        item = value.get(
            key
        )


        normalized = canonical_url(
            item
        )


        if normalized:

            urls.add(
                normalized
            )


    raw = (
        value.get(
            "raw_metadata"
        )
        or {}
    )


    if isinstance(
        raw,
        dict
    ):

        for key in keys:

            normalized = canonical_url(
                raw.get(
                    key
                )
            )


            if normalized:

                urls.add(
                    normalized
                )


    return urls


def candidate_paths(
    value,
):
    keys = [
        "path",
        "local_path",
        "source_local_path",
        "asset",
        "downloaded_path",
    ]


    paths = set()


    for key in keys:

        item = canonical_path(
            value.get(
                key
            )
        )


        if item:

            paths.add(
                item
            )


    raw = (
        value.get(
            "raw_metadata"
        )
        or {}
    )


    if isinstance(
        raw,
        dict
    ):

        for key in keys:

            item = canonical_path(
                raw.get(
                    key
                )
            )


            if item:

                paths.add(
                    item
                )


    return paths


def candidate_hashes(
    value,
):
    hashes = set()


    for key in [
        "sha256",
        "source_sha256",
        "hash",
        "file_sha256",
    ]:

        item = str(
            value.get(
                key
            )
            or ""
        ).strip().lower()


        if re.fullmatch(
            r"[0-9a-f]{64}",
            item,
        ):

            hashes.add(
                item
            )


    raw = (
        value.get(
            "raw_metadata"
        )
        or {}
    )


    if isinstance(
        raw,
        dict
    ):

        item = str(
            raw.get(
                "sha256"
            )
            or ""
        ).strip().lower()


        if re.fullmatch(
            r"[0-9a-f]{64}",
            item,
        ):

            hashes.add(
                item
            )


    return hashes


def source_group(
    value,
):
    return norm(
        value.get(
            "source_group"
        )
        or ""
    )


def title_identity(
    value,
):
    return canonical_title(
        value.get(
            "title"
        )
        or
        value.get(
            "name"
        )
        or ""
    )


def independent_similarity(
    asset,
    record,
):
    score = 0

    reasons = []


    asset_hashes = (
        candidate_hashes(
            asset
        )
    )


    record_hashes = (
        candidate_hashes(
            record
        )
    )


    if (
        asset_hashes

        and

        record_hashes

        and

        asset_hashes
        &
        record_hashes
    ):

        score += 300

        reasons.append(
            "sha256_exact"
        )


    asset_paths = (
        candidate_paths(
            asset
        )
    )


    record_paths = (
        candidate_paths(
            record
        )
    )


    if (
        asset_paths

        and

        record_paths

        and

        asset_paths
        &
        record_paths
    ):

        score += 250

        reasons.append(
            "local_path_exact"
        )


    asset_group = source_group(
        asset
    )


    record_group = source_group(
        record
    )


    if (
        asset_group

        and

        record_group

        and

        asset_group
        ==
        record_group
    ):

        score += 220

        reasons.append(
            "source_group_exact"
        )


    asset_urls = candidate_urls(
        asset
    )


    record_urls = candidate_urls(
        record
    )


    if (
        asset_urls

        and

        record_urls

        and

        asset_urls
        &
        record_urls
    ):

        score += 200

        reasons.append(
            "canonical_url_exact"
        )


    asset_title = title_identity(
        asset
    )


    record_title = title_identity(
        record
    )


    if (
        asset_title

        and

        record_title

        and

        len(
            asset_title
        ) >= 8

        and

        asset_title
        ==
        record_title
    ):

        score += 170

        reasons.append(
            "canonical_title_exact"
        )


    asset_names = {
        Path(
            item
        ).name.lower()

        for item in asset_paths

        if item
    }


    asset_names.update({
        filename_from_url(
            item
        )

        for item in asset_urls

        if filename_from_url(
            item
        )
    })


    record_names = {
        Path(
            item
        ).name.lower()

        for item in record_paths

        if item
    }


    record_names.update({
        filename_from_url(
            item
        )

        for item in record_urls

        if filename_from_url(
            item
        )
    })


    if (
        asset_names

        and

        record_names

        and

        asset_names
        &
        record_names
    ):

        score += 120

        reasons.append(
            "filename_exact"
        )


    return (
        score,
        reasons,
    )


def scene_agreement(
    asset,
    record,
):
    try:

        if (
            asset.get(
                "scene"
            )
            is not None

            and

            record.get(
                "scene"
            )
            is not None

            and

            int(
                asset[
                    "scene"
                ]
            )
            ==
            int(
                record[
                    "scene"
                ]
            )
        ):

            return True


    except Exception:

        pass


    return False


# VI1510.1 V2.4 STRUCTURAL SOURCE-USAGE JOIN
def structural_join_match(
    asset,
    record_index,
):
    bridge = (
        asset.get(
            "source_usage_join"
        )
        or {}
    )


    if (
        bridge.get(
            "linked"
        )
        is not True
    ):
        return False


    if bridge.get(
        "confidence"
    ) != "STRONG":
        return False


    try:

        return (
            int(
                bridge.get(
                    "record_index"
                )
            )
            ==
            int(
                record_index
            )
        )

    except Exception:

        return False


def similarity(
    asset,
    record,
):
    score, reasons = independent_similarity(
        asset,
        record,
    )


    # Scene number alone can NEVER establish lineage.
    if (
        score > 0

        and

        scene_agreement(
            asset,
            record
        )
    ):

        score += 25

        reasons.append(
            "scene_agreement_bonus"
        )


    return (
        score,
        reasons,
    )


def run(
    scene_usage,
    metadata,
    run_dir,
):
    records = (
        metadata.get(
            "records"
        )
        or []
    )


    rows = []


    for asset in scene_usage.get(
        "used_assets",
        []
    ):

        matches = []


        for index, record in enumerate(
            records
        ):

            score, reasons = similarity(
                asset,
                record,
            )


            if structural_join_match(
                asset,
                index,
            ):

                score += 260

                reasons.append(
                    "source_usage_structural_join"
                )


            # Minimum 100 means scene bonus alone
            # cannot possibly certify a link.
            if score >= 100:

                matches.append({
                    "record_index":
                        index,

                    "score":
                        score,

                    "reasons":
                        reasons,

                    "title":
                        record.get(
                            "title"
                        ),

                    "source_group":
                        record.get(
                            "source_group"
                        ),

                    "source_url":
                        record.get(
                            "source_url"
                        ),
                })


        matches.sort(
            key=lambda item:
                item[
                    "score"
                ],
            reverse=True,
        )


        rows.append({
            **asset,

            "linked_records":
                matches[
                    :5
                ],

            "strictly_linked":
                bool(
                    matches
                ),

            "best_lineage_score":
                (
                    matches[
                        0
                    ][
                        "score"
                    ]

                    if matches

                    else 0
                ),

            "best_lineage_reasons":
                (
                    matches[
                        0
                    ][
                        "reasons"
                    ]

                    if matches

                    else []
                ),
        })


    report = {
        "mode":
            "VI1510_1_LINEAGE_V3_CANONICAL",

        "assets":
            rows,

        "used_asset_count":
            len(
                rows
            ),

        "unique_used_assets":
            len({
                row.get(
                    "sha256"
                )
                or
                canonical_path(
                    row.get(
                        "path"
                    )
                )

                for row in rows
            }),

        "strictly_linked_assets":
            sum(
                bool(
                    row[
                        "strictly_linked"
                    ]
                )

                for row in rows
            ),

        "strictly_linked_unique_assets":
            len({
                (
                    row.get(
                        "sha256"
                    )
                    or
                    canonical_path(
                        row.get(
                            "path"
                        )
                    )
                )

                for row in rows

                if row[
                    "strictly_linked"
                ]
            }),

        "unlinked_scenes":
            sorted({
                row.get(
                    "scene"
                )

                for row in rows

                if (
                    not row[
                        "strictly_linked"
                    ]

                    and

                    row.get(
                        "scene"
                    )
                    is not None
                )
            }),

        "scene_only_never_evidence":
            True,

        "minimum_independent_score":
            100,
    }


    save_json(
        run_dir
        / "lineage_v2.json",
        report
    )


    return report


if __name__ == "__main__":

    print(
        "VI1510.1 LINEAGE V3 MODULE=PASS"
    )
