#!/usr/bin/env python3

from pathlib import Path

from vi1510_01_common import (
    save_json,
)


def as_list(
    value,
):
    return (
        value
        if isinstance(
            value,
            list
        )
        else []
    )


def relevance_stats(
    relevance,
):
    rows = []

    if isinstance(
        relevance,
        dict
    ):

        for key in [
            "records",
            "rows",
            "assets",
            "results",
            "evaluations",
        ]:

            value = relevance.get(
                key
            )

            if isinstance(
                value,
                list
            ):

                rows = value

                break


    known = 0
    passed = 0


    for row in rows:

        if not isinstance(
            row,
            dict
        ):
            continue


        decision = None


        for key in [
            "relevant",
            "passed",
            "accepted",
            "approved",
        ]:

            if key in row:

                decision = bool(
                    row[
                        key
                    ]
                )

                break


        if decision is not None:

            known += 1

            if decision:

                passed += 1


    return {
        "rows":
            len(
                rows
            ),

        "known_decisions":
            known,

        "passed":
            passed,

        "ratio":
            (
                round(
                    passed / known,
                    4
                )

                if known

                else None
            ),
    }


def run(
    scene_usage,
    metadata,
    relevance,
    lineage,
    run_dir,
):
    run_dir = Path(
        run_dir
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    used_assets = as_list(
        scene_usage.get(
            "used_assets"
        )
    )


    lineage_assets = as_list(
        lineage.get(
            "assets"
        )
    )


    metadata_records = as_list(
        metadata.get(
            "records"
        )
    )


    unique_used = (
        lineage.get(
            "unique_used_assets"
        )
    )


    if unique_used is None:

        unique_used = len({
            row.get(
                "sha256"
            )

            for row in used_assets

            if row.get(
                "sha256"
            )
        })


    linked_unique = int(
        lineage.get(
            "strictly_linked_unique_assets"
        )
        or 0
    )


    linked_assets = int(
        lineage.get(
            "strictly_linked_assets"
        )
        or 0
    )


    unique_used = int(
        unique_used
        or 0
    )


    used_count = int(
        lineage.get(
            "used_asset_count"
        )
        or len(
            used_assets
        )
    )


    linkage_ratio = (
        linked_unique
        /
        unique_used

        if unique_used

        else 0.0
    )


    relevance_summary = relevance_stats(
        relevance
    )


    blockers = []

    warnings = []


    if used_count <= 0:

        blockers.append(
            "no_used_assets_detected"
        )


    if unique_used <= 0:

        blockers.append(
            "no_unique_used_assets"
        )


    if not metadata_records:

        blockers.append(
            "source_metadata_empty"
        )


    if (
        used_count

        and

        lineage_assets

        and

        len(
            lineage_assets
        )
        !=
        used_count
    ):

        blockers.append(
            "scene_usage_lineage_count_mismatch"
        )


    if (
        unique_used > 0

        and

        linkage_ratio < 0.75
    ):

        blockers.append(
            "strict_lineage_coverage_below_75_percent"
        )


    if (
        unique_used > 0

        and

        linked_unique
        ==
        unique_used
    ):

        lineage_status = (
            "FULL"
        )


    elif linkage_ratio >= 0.75:

        lineage_status = (
            "STRONG"
        )


    else:

        lineage_status = (
            "INSUFFICIENT"
        )


    if (
        relevance_summary[
            "known_decisions"
        ]
        == 0
    ):

        warnings.append(
            "relevance_decision_shape_not_detected"
        )


    if (
        metadata_records

        and

        len(
            metadata_records
        )
        < unique_used
    ):

        warnings.append(
            "fewer_metadata_records_than_unique_assets"
        )


    unlinked = [
        {
            "scene":
                row.get(
                    "scene"
                ),

            "path":
                row.get(
                    "path"
                ),

            "sha256":
                row.get(
                    "sha256"
                ),
        }

        for row
        in lineage_assets

        if not row.get(
            "strictly_linked"
        )
    ]


    certified = (
        not blockers
    )


    status = (
        "VI1510_1_EVIDENCE_GATE_V2_CERTIFIED"

        if certified

        else

        "VI1510_1_EVIDENCE_GATE_V2_HOLD"
    )


    report = {
        "status":
            status,

        "mode":
            lineage.get(
                "mode"
            )
            or
            scene_usage.get(
                "mode"
            ),

        "used_asset_count":
            used_count,

        "unique_used_assets":
            unique_used,

        "strictly_linked_assets":
            linked_assets,

        "strictly_linked_unique_assets":
            linked_unique,

        "strict_lineage_ratio":
            round(
                linkage_ratio,
                4
            ),

        "lineage_strength":
            lineage_status,

        "metadata_record_count":
            len(
                metadata_records
            ),

        "relevance":
            relevance_summary,

        "unlinked_assets":
            unlinked,

        "blockers":
            blockers,

        "warnings":
            warnings,
    }


    save_json(
        run_dir
        / "evidence_gate_v2.json",
        report
    )


    return report


if __name__ == "__main__":

    print(
        "VI1510.1 EVIDENCE GATE V2 MODULE=PASS"
    )
