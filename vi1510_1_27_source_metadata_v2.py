#!/usr/bin/env python3

import json

from pathlib import Path
from urllib.parse import urlparse

from vi1510_01_common import (
    ROOT,
    in_window,
    norm,
    save_json,
)

from vi1510_1_26_evidence_text import (
    evidence_blob,
)


PROVENANCE_KEYS = {
    "provider",
    "license",
    "licenseshortname",
    "artist",
    "source",
    "source_url",
    "url",
    "remote_url",
    "media_url",
    "original_url",
    "descriptionurl",
    "source_group",
    "pageid",
    "credit",
    "credits",
}


def looks_like_source(
    value,
):
    if not isinstance(
        value,
        dict
    ):
        return False


    keys = {
        str(
            key
        ).lower()

        for key in value.keys()
    }


    return bool(
        keys
        &
        PROVENANCE_KEYS
    )


def walk_sources(
    value,
):
    if isinstance(
        value,
        dict
    ):

        if looks_like_source(
            value
        ):

            yield value


        for item in value.values():

            yield from walk_sources(
                item
            )


    elif isinstance(
        value,
        list
    ):

        for item in value:

            yield from walk_sources(
                item
            )


def first(
    value,
    keys,
):
    for key in keys:

        item = value.get(
            key
        )


        if item not in {
            None,
            "",
        }:

            return item


    return None


def normalize_record(
    value,
    origin,
):
    url = first(
        value,
        [
            "source",
            "source_url",
            "remote_url",
            "media_url",
            "original_url",
            "descriptionurl",
            "url",
        ],
    )


    license_value = first(
        value,
        [
            "license",
            "LicenseShortName",
            "license_short_name",
        ],
    )


    local_path = first(
        value,
        [
            "local_path",
            "asset",
            "path",
            "downloaded_path",
        ],
    )


    raw_evidence = evidence_blob(
        value
    )


    return {
        "provider":
            str(
                value.get(
                    "provider"
                )
                or ""
            ),

        "title":
            str(
                value.get(
                    "title"
                )
                or
                value.get(
                    "name"
                )
                or
                value.get(
                    "ObjectName"
                )
                or ""
            ),

        "license":
            str(
                license_value
                or ""
            ),

        "artist":
            str(
                value.get(
                    "artist"
                )
                or ""
            ),

        "source_group":
            str(
                value.get(
                    "source_group"
                )
                or ""
            ),

        "source_url":
            str(
                url
                or ""
            ),

        "remote_url":
            str(
                value.get(
                    "remote_url"
                )
                or ""
            ),

        "media_url":
            str(
                value.get(
                    "media_url"
                )
                or ""
            ),

        "original_url":
            str(
                value.get(
                    "original_url"
                )
                or ""
            ),

        "download_url":
            str(
                value.get(
                    "download_url"
                )
                or ""
            ),

        "final_url":
            str(
                value.get(
                    "final_url"
                )
                or ""
            ),

        "local_path":
            str(
                local_path
                or ""
            ),

        "sha256":
            str(
                value.get(
                    "sha256"
                )
                or ""
            ),

        "scene":
            value.get(
                "scene"
            )
            or
            value.get(
                "scene_id"
            ),

        "evidence_text":
            raw_evidence,

        "query_used_as_evidence":
            (
                value.get(
                    "query_used_as_evidence"
                )
                is True
            ),

        "origin":
            str(
                origin
            ),
    }


def parse_credit_line(
    line,
    origin,
):
    parts = [
        part.strip()

        for part
        in line.split(
            "|"
        )
    ]


    if len(
        parts
    ) < 3:
        return None


    source_url = ""


    for part in reversed(
        parts
    ):

        if part.startswith(
            (
                "https://",
                "http://",
            )
        ):

            source_url = part
            break


    raw = {
        "provider":
            parts[
                0
            ],

        "title":
            parts[
                1
            ]
            if len(
                parts
            ) > 1
            else "",

        "license":
            parts[
                2
            ]
            if len(
                parts
            ) > 2
            else "",

        "artist":
            parts[
                3
            ]
            if len(
                parts
            ) > 3
            else "",

        "source":
            source_url,
    }


    return normalize_record(
        raw,
        origin
    )


def collect(
    run,
    run_dir,
):
    start = float(
        run[
            "window_start"
        ]
    )

    end = float(
        run[
            "window_end"
        ]
    )

    short_id = (
        run.get(
            "short_id"
        )
        or ""
    )


    paths = set()


    roots = [
        ROOT
        / "credits",

        ROOT
        / "manifests",

        ROOT
        / "imagens",

        ROOT
        / "temp",

        ROOT
        / "roteiros",
    ]


    for base in roots:

        if not base.exists():
            continue


        for path in base.rglob(
            "*"
        ):

            if (
                not path.is_file()

                or

                path.suffix.lower()
                not in {
                    ".json",
                    ".txt",
                }
            ):

                continue


            lower = str(
                path
            ).lower()


            if any(
                marker
                in lower

                for marker in [
                    "/vi1400/",
                    "/vi1500/",
                    "/vi1510/",
                ]
            ):

                continue


            sid_match = (
                bool(
                    short_id
                )

                and

                short_id
                in str(
                    path
                )
            )


            source_name = any(
                word
                in path.name.lower()

                for word in [
                    "credit",
                    "source",
                    "manifest",
                    "media",
                    "asset",
                    "plan",
                    "roteiro",
                    "scene",
                    "cena",
                ]
            )


            if (
                sid_match

                or

                (
                    source_name

                    and

                    in_window(
                        path,
                        start,
                        end,
                    )
                )
            ):

                paths.add(
                    path.resolve()
                )


    records = []


    for path in sorted(
        paths
    ):

        try:

            if path.suffix.lower() == ".json":

                data = json.loads(
                    path.read_text(
                        encoding="utf-8",
                        errors="ignore"
                    )
                )


                for source in walk_sources(
                    data
                ):

                    records.append(
                        normalize_record(
                            source,
                            path
                        )
                    )


            else:

                for line in path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                ).splitlines():

                    record = parse_credit_line(
                        line,
                        path
                    )


                    if record:

                        records.append(
                            record
                        )


        except Exception:

            continue


    dedup = {}


    for record in records:

        key = (
            norm(
                record[
                    "provider"
                ]
            ),
            norm(
                record[
                    "title"
                ]
            ),
            norm(
                record[
                    "source_url"
                ]
            ),
            norm(
                record[
                    "local_path"
                ]
            ),
            norm(
                record[
                    "source_group"
                ]
            ),
        )


        if not any(
            key
        ):

            continue


        dedup[
            key
        ] = record


    records = list(
        dedup.values()
    )


    independent = set()


    for record in records:

        url = record[
            "source_url"
        ]


        try:

            host = (
                urlparse(
                    url
                ).hostname
                or ""
            ).lower()


        except Exception:

            host = ""


        identity = (
            host
            or
            norm(
                record[
                    "provider"
                ]
            ),

            norm(
                record[
                    "title"
                ]
                or
                record[
                    "source_group"
                ]
                or
                record[
                    "source_url"
                ]
            ),
        )


        if any(
            identity
        ):

            independent.add(
                identity
            )


    report = {
        "files_checked": [
            str(
                path
            )

            for path
            in sorted(
                paths
            )
        ],

        "records":
            records,

        "record_count":
            len(
                records
            ),

        "independent_source_count":
            len(
                independent
            ),
    }


    save_json(
        run_dir
        / "source_metadata_v2.json",
        report
    )


    return report


# ======================================================
# VI1510.1 V3 RUNTIME INVENTORY METADATA WRAPPER
# ======================================================

from vi1510_1_23_runtime_inventory_v3 import (
    inventory_metadata_records as _vi1510_v3_inventory_metadata_records,
)


_vi1510_v3_previous_metadata_collect = collect


def collect(
    run,
    run_dir,
    resolved=None,
    partition=None,
    fallback_inventory=None,
):
    report = _vi1510_v3_previous_metadata_collect(
        run,
        run_dir,
    )

    current = list(
        report.get(
            "records",
            []
        )
    )

    extra = _vi1510_v3_inventory_metadata_records(
        run=run,
        partition=partition,
        resolved=resolved,
        fallback_inventory=fallback_inventory,
    )

    dedup = {}

    for record in (
        current
        +
        extra
    ):
        key = (
            norm(
                record.get("provider")
                or ""
            ),
            norm(
                record.get("title")
                or ""
            ),
            norm(
                record.get("source_group")
                or ""
            ),
            norm(
                record.get("source_url")
                or ""
            ),
            norm(
                record.get("local_path")
                or ""
            ),
            str(
                record.get("sha256")
                or ""
            ).lower(),
        )

        dedup[key] = record

    records = list(
        dedup.values()
    )

    report[
        "records"
    ] = records

    report[
        "record_count"
    ] = len(records)

    report[
        "runtime_inventory_v3"
    ] = {
        "added_records":
            max(
                0,
                len(records)
                -
                len(current),
            ),

        "query_used_as_evidence":
            False,
    }

    save_json(
        Path(run_dir)
        / "source_metadata_v2.json",
        report,
    )

    return report
