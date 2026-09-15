#!/usr/bin/env python3

from urllib.parse import urlparse

from vi1510_01_common import (
    norm,
    save_json,
)

from vi1510_10_domain_policy import (
    requirements,
)


UNKNOWN_LICENSES = {
    "",
    "unknown",
    "none",
    "n/a",
}


def independent_identity(
    record,
):
    url = str(
        record.get(
            "source_url"
        )
        or ""
    )


    try:
        host = (
            urlparse(
                url
            ).hostname
            or ""
        ).lower()

    except Exception:
        host = ""


    return (
        host,
        norm(
            record.get(
                "title"
            )
            or
            record.get(
                "source_group"
            )
        ),
    )


def run(
    run_info,
    lineage,
    metadata,
    run_dir,
):
    req = requirements(
        run_info.get(
            "domain",
            "CUSTOM"
        )
    )


    assets = (
        lineage.get(
            "assets"
        )
        or []
    )


    unique_hashes = {
        asset[
            "sha256"
        ]

        for asset in assets
    }


    linked_hashes = {
        asset[
            "sha256"
        ]

        for asset in assets

        if asset.get(
            "provenance_linked"
        )
    }


    records = (
        metadata.get(
            "records"
        )
        or []
    )


    independent = {
        independent_identity(
            record
        )

        for record in records

        if any(
            independent_identity(
                record
            )
        )
    }


    licensed_records = sum(
        1

        for record in records

        if norm(
            record.get(
                "license"
            )
        )
        not in UNKNOWN_LICENSES
    )


    query_evidence = [
        index

        for index, record in enumerate(
            records
        )

        if record.get(
            "query_used_as_evidence"
        )
        is True
    ]


    unique_count = len(
        unique_hashes
    )


    strict_linked_count = len(
        linked_hashes
    )


    # Some pipelines keep credits in a global manifest
    # instead of one sidecar per asset. We do not pretend
    # those records are exact links, but use them as
    # documented portfolio coverage.
    documented_equivalent = max(
        strict_linked_count,
        min(
            unique_count,
            len(
                independent
            ),
        ),
    )


    coverage = (
        documented_equivalent
        /
        unique_count

        if unique_count
        else 0.0
    )


    blockers = []

    warnings = []


    if len(
        assets
    ) < int(
        req[
            "minimum_assets"
        ]
    ):

        blockers.append(
            "insufficient_actual_source_assets"
        )


    if unique_count < int(
        req[
            "minimum_unique_assets"
        ]
    ):

        blockers.append(
            "insufficient_unique_source_assets"
        )


    if len(
        independent
    ) < int(
        req[
            "minimum_source_records"
        ]
    ):

        blockers.append(
            "insufficient_independent_source_records"
        )


    if coverage < float(
        req[
            "minimum_provenance_coverage"
        ]
    ):

        blockers.append(
            "provenance_coverage_below_domain_requirement"
        )


    if licensed_records < int(
        req[
            "minimum_licensed_records"
        ]
    ):

        warnings.append(
            "licensed_source_records_below_target"
        )


    if query_evidence:

        blockers.append(
            "query_used_as_evidence"
        )


    report = {
        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "domain":
            run_info.get(
                "domain"
            ),

        "requirements":
            req,

        "asset_count":
            len(
                assets
            ),

        "unique_asset_count":
            unique_count,

        "strict_linked_unique_assets":
            strict_linked_count,

        "independent_source_records":
            len(
                independent
            ),

        "licensed_records":
            licensed_records,

        "documented_equivalent_assets":
            documented_equivalent,

        "provenance_coverage":
            round(
                coverage,
                4
            ),

        "query_evidence_violations":
            query_evidence,

        "warnings":
            warnings,

        "blockers":
            blockers,
    }


    save_json(
        run_dir
        / "provenance_gate.json",
        report
    )


    return report
