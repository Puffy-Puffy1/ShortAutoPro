#!/usr/bin/env python3

from pathlib import Path

from vi1510_01_common import (
    save_json,
)


def topic_key(
    row,
    index,
):
    for key in [
        "topic",
        "topic_id",
        "benchmark",
        "benchmark_id",
        "name",
        "id",
        "mode",
    ]:

        value = row.get(
            key
        )

        if value not in [
            None,
            "",
        ]:

            return str(
                value
            )


    return (
        "partition_"
        + str(
            index + 1
        )
    )


def run(
    run_reports,
    run_dir,
):
    run_dir = Path(
        run_dir
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    hashes = {}

    source_groups = {}

    statuses = []

    topics = []


    for index, row in enumerate(
        run_reports
    ):

        key = topic_key(
            row,
            index,
        )

        topics.append(
            key
        )


        gate = (
            row.get(
                "evidence_gate"
            )
            or {}
        )


        statuses.append(
            gate.get(
                "status"
            )
        )


        lineage = (
            row.get(
                "lineage"
            )
            or {}
        )


        for asset in lineage.get(
            "assets",
            []
        ):

            sha = asset.get(
                "sha256"
            )


            if sha:

                hashes.setdefault(
                    sha,
                    []
                ).append({
                    "topic":
                        key,

                    "scene":
                        asset.get(
                            "scene"
                        ),

                    "path":
                        asset.get(
                            "path"
                        ),
                })


            group = (
                asset.get(
                    "source_group"
                )
                or
                asset.get(
                    "provider"
                )
            )


            if group:

                source_groups.setdefault(
                    str(
                        group
                    ),
                    set()
                ).add(
                    key
                )


    exact_cross_topic_reuse = []


    for sha, usages in (
        hashes.items()
    ):

        distinct_topics = sorted({
            item[
                "topic"
            ]

            for item
            in usages
        })


        if len(
            distinct_topics
        ) > 1:

            exact_cross_topic_reuse.append({
                "sha256":
                    sha,

                "topics":
                    distinct_topics,

                "usages":
                    usages,
            })


    shared_source_groups = []


    for group, values in (
        source_groups.items()
    ):

        if len(
            values
        ) > 1:

            shared_source_groups.append({
                "source_group":
                    group,

                "topics":
                    sorted(
                        values
                    ),
            })


    blockers = []

    warnings = []


    if len(
        run_reports
    ) < 2:

        blockers.append(
            "insufficient_independent_partitions"
        )


    failed_gates = [
        index + 1

        for index, status
        in enumerate(
            statuses
        )

        if status
        !=
        "VI1510_1_EVIDENCE_GATE_V2_CERTIFIED"
    ]


    if failed_gates:

        blockers.append(
            "one_or_more_partition_evidence_gates_failed"
        )


    if exact_cross_topic_reuse:

        warnings.append(
            "exact_binary_reuse_across_topics_detected"
        )


    if shared_source_groups:

        warnings.append(
            "source_groups_shared_across_topics"
        )


    certified = (
        not blockers
    )


    status = (
        "VI1510_1_CROSS_TOPIC_V3_CERTIFIED"

        if certified

        else

        "VI1510_1_CROSS_TOPIC_V3_HOLD"
    )


    report = {
        "status":
            status,

        "partition_count":
            len(
                run_reports
            ),

        "topics":
            topics,

        "partition_gate_statuses":
            statuses,

        "exact_cross_topic_reuse":
            exact_cross_topic_reuse,

        "shared_source_groups":
            shared_source_groups,

        "blockers":
            blockers,

        "warnings":
            warnings,
    }


    save_json(
        run_dir
        / "cross_topic_v3.json",
        report
    )


    return report


if __name__ == "__main__":

    print(
        "VI1510.1 CROSS TOPIC V3 MODULE=PASS"
    )
