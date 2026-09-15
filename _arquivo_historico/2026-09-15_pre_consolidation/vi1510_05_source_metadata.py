#!/usr/bin/env python3

import json
import re

from pathlib import Path
from urllib.parse import urlparse

from vi1510_01_common import (
    ROOT,
    in_window,
    norm,
    save_json,
)


SOURCE_KEYS = {
    "provider",
    "license",
    "source",
    "url",
    "remote_url",
    "media_url",
    "original_url",
    "descriptionurl",
    "title",
    "source_group",
    "artist",
    "sha256",
    "path",
    "asset",
    "local_path",
}


def source_like(
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


    if not (
        keys
        &
        SOURCE_KEYS
    ):
        return False


    has_identity = any(
        value.get(
            key
        )

        for key in [
            "title",
            "source_group",
            "provider",
            "source",
            "url",
            "remote_url",
            "media_url",
            "original_url",
            "descriptionurl",
        ]
    )


    return bool(
        has_identity
    )


def walk(
    value,
):
    if isinstance(
        value,
        dict
    ):

        if source_like(
            value
        ):
            yield value


        for item in value.values():
            yield from walk(
                item
            )


    elif isinstance(
        value,
        list
    ):

        for item in value:
            yield from walk(
                item
            )


def first(
    value,
    names,
):
    for name in names:

        item = value.get(
            name
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
    source_url = first(
        value,
        [
            "source",
            "remote_url",
            "media_url",
            "original_url",
            "descriptionurl",
            "url",
        ]
    )


    local_path = first(
        value,
        [
            "path",
            "asset",
            "local_path",
            "downloaded_path",
            "file",
        ]
    )


    description = first(
        value,
        [
            "description",
            "metadata_text",
            "evidence_text",
            "extract",
            "caption",
        ]
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
                or ""
            ),

        "license":
            str(
                value.get(
                    "license"
                )
                or
                value.get(
                    "license_short_name"
                )
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
                source_url
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

        "description":
            str(
                description
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
                "http://",
                "https://",
            )
        ):
            source_url = part
            break


    return {
        "provider":
            parts[
                0
            ],

        "title":
            (
                parts[
                    1
                ]
                if len(
                    parts
                ) > 1
                else ""
            ),

        "license":
            (
                parts[
                    2
                ]
                if len(
                    parts
                ) > 2
                else ""
            ),

        "artist":
            (
                parts[
                    3
                ]
                if len(
                    parts
                ) > 3
                else ""
            ),

        "source_group":
            "",

        "source_url":
            source_url,

        "local_path":
            "",

        "sha256":
            "",

        "description":
            "",

        "scene":
            None,

        "query_used_as_evidence":
            False,

        "origin":
            str(
                origin
            ),
    }


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


    old_artifacts = (
        run.get(
            "old_artifacts"
        )
        or {}
    )


    for path_text in (
        old_artifacts.get(
            "new_metadata"
        )
        or []
    ):

        path = Path(
            path_text
        )

        if path.exists():
            paths.add(
                path.resolve()
            )


    roots = [
        ROOT
        / "manifests",

        ROOT
        / "credits",

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


            text = str(
                path
            ).lower()


            if any(
                part in text

                for part in [
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


            fresh = in_window(
                path,
                start,
                end,
            )


            source_named = any(
                word
                in path.name.lower()

                for word in [
                    "credit",
                    "source",
                    "manifest",
                    "media",
                    "asset",
                    "selection",
                    "provenance",
                ]
            )


            if (
                sid_match

                or

                (
                    fresh
                    and
                    source_named
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


                for item in walk(
                    data
                ):

                    records.append(
                        normalize_record(
                            item,
                            path
                        )
                    )


            else:

                for line in path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                ).splitlines():

                    item = parse_credit_line(
                        line,
                        path
                    )

                    if item:
                        records.append(
                            item
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


        if url:

            try:
                host = urlparse(
                    url
                ).hostname or ""

            except Exception:
                host = ""

        else:
            host = ""


        identity = (
            host.lower(),
            norm(
                record[
                    "title"
                ]
                or
                record[
                    "source_group"
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
            in paths
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
        / "source_metadata.json",
        report
    )


    return report
