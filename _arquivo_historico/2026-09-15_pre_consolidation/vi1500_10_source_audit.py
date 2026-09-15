#!/usr/bin/env python3

import json

from pathlib import Path

from vi1500_01_common import (
    ROOT,
    policy,
    save_json,
)


def candidate_like(
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

        for key in value
    }


    return bool(
        keys
        &
        {
            "title",
            "source_group",
            "provider",
            "license",
            "remote_url",
            "media_url",
            "original_url",
        }
    )


def walk(
    value,
):
    if isinstance(
        value,
        dict
    ):
        if candidate_like(
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


def run(
    start_time,
    run_dir,
):
    config = policy()


    records = []

    files_checked = []


    roots = [
        ROOT / "temp",
        ROOT / "logs",
        ROOT / "manifests",
        ROOT / "credits",
    ]


    for base in roots:
        if not base.exists():
            continue


        for path in base.rglob(
            "*.json"
        ):
            text_path = str(
                path
            ).lower()


            if (
                "/vi1500/"
                in text_path

                or

                "/vi1400/"
                in text_path
            ):
                continue


            try:
                if (
                    path.stat().st_mtime
                    <
                    start_time
                    - 2
                ):
                    continue


                data = json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )


                files_checked.append(
                    str(
                        path
                    )
                )


                records.extend(
                    walk(
                        data
                    )
                )


            except Exception:
                pass


    dedup = {}


    query_evidence_violations = []


    for record in records:
        key = (
            str(
                record.get(
                    "source_group"
                )
                or
                record.get(
                    "title"
                )
                or
                record.get(
                    "remote_url"
                )
                or
                record.get(
                    "media_url"
                )
                or id(
                    record
                )
            )
        )


        dedup[
            key
        ] = record


        if (
            record.get(
                "query_used_as_evidence"
            )
            is True
        ):
            query_evidence_violations.append(
                key
            )


    records = list(
        dedup.values()
    )


    unique_sources = {
        str(
            record.get(
                "source_group"
            )
            or
            record.get(
                "title"
            )
            or
            ""
        )

        for record in records

        if (
            record.get(
                "source_group"
            )
            or
            record.get(
                "title"
            )
        )
    }


    blockers = []

    warnings = []


    if query_evidence_violations:
        blockers.append(
            "query_used_as_evidence"
        )


    if len(
        records
    ) < int(
        config.get(
            "minimum_source_records",
            6
        )
    ):
        blockers.append(
            "insufficient_source_records"
        )


    if len(
        unique_sources
    ) < int(
        config.get(
            "minimum_unique_sources",
            4
        )
    ):
        blockers.append(
            "insufficient_unique_sources"
        )


    missing_license = sum(
        1

        for record in records

        if not record.get(
            "license"
        )
    )


    if (
        records
        and
        missing_license
        >
        len(
            records
        )
        * 0.5
    ):
        warnings.append(
            "many_source_records_without_license_field"
        )


    report = {
        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "source_records":
            len(
                records
            ),

        "unique_sources":
            len(
                unique_sources
            ),

        "files_checked":
            files_checked,

        "query_evidence_violations":
            query_evidence_violations,

        "warnings":
            warnings,

        "blockers":
            blockers,
    }


    save_json(
        run_dir
        / "source_audit.json",
        report
    )


    return report
