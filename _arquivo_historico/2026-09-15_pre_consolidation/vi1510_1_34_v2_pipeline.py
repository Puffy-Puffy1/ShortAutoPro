#!/usr/bin/env python3

import inspect
import json
import re

from datetime import datetime
from pathlib import Path


from vi1510_1_24_partitioned_resolver import (
    resolve as partitioned_resolve,
)

from vi1510_1_25_scene_usage import (
    collect as collect_scene_usage,
)

from vi1510_1_27_source_metadata_v2 import (
    collect as collect_source_metadata,
)

from vi1510_1_28_relevance_v2 import (
    run as run_relevance,
)

# VI1510.1 V2.4 SOURCE-USAGE JOIN IMPORT
from vi1510_1_29_source_usage_join import (
    enrich as run_source_usage_join,
)

from vi1510_1_29_lineage_v2 import (
    run as run_lineage,
)

from vi1510_1_30_evidence_gate_v2 import (
    run as run_evidence_gate,
)

from vi1510_1_31_cross_topic_v3 import (
    run as run_cross_topic,
)


BASE = (
    Path.home()
    / "ShortAutoPro"
)

ROOT = (
    BASE
    / "temp/"
    "vi1510_1"
)

LOG_OUT = (
    BASE
    / "logs/producao/"
    "vi1510_1_v2_pipeline_latest.json"
)


def dump(
    path,
    data,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


def slug(
    value,
):
    text = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        str(
            value
        ),
    )


    text = text.strip(
        "_"
    )


    return (
        text[
            :80
        ]
        or
        "partition"
    )


def extract_partitions(
    resolved,
):
    if isinstance(
        resolved,
        list
    ):

        return resolved


    if isinstance(
        resolved,
        dict
    ):

        for key in [
            "partitions",
            "runs",
            "resolved_runs",
            "items",
            "benchmarks",
        ]:

            value = resolved.get(
                key
            )


            if (
                isinstance(
                    value,
                    list
                )

                and

                value
            ):

                return value


        return [
            resolved
        ]


    return [
        {
            "value":
                resolved
        }
    ]


def partition_name(
    row,
    index,
):
    if isinstance(
        row,
        dict
    ):

        for key in [
            "topic",
            "topic_id",
            "benchmark",
            "benchmark_id",
            "name",
            "id",
            "short_id",
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


ALIASES = {
    "run":
        "partition",

    "item":
        "partition",

    "resolved_run":
        "partition",

    "topic_run":
        "partition",

    "partition_data":
        "partition",

    "resolved":
        "resolved",

    "resolved_runs":
        "resolved",

    "resolution":
        "resolved",

    "run_dir":
        "run_dir",

    "output_dir":
        "run_dir",

    "work_dir":
        "run_dir",

    "directory":
        "run_dir",

    "scene_usage":
        "scene_usage",

    "usage":
        "scene_usage",

    "source_metadata":
        "metadata",

    "metadata":
        "metadata",

    "records":
        "metadata_records",

    "relevance":
        "relevance",

    "relevance_report":
        "relevance",

    "lineage":
        "lineage",

    "lineage_report":
        "lineage",

    "scope":
        "scope",

    "narrative_scope":
        "scope",

    "topic":
        "topic",

    "topic_id":
        "topic",

    "name":
        "topic",

    "base":
        "base",

    "base_dir":
        "base",

    "root":
        "base",
}


def invoke(
    function,
    context,
):
    signature = inspect.signature(
        function
    )


    kwargs = {}


    unresolved = []


    for name, parameter in (
        signature.parameters.items()
    ):

        if parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:

            continue


        if name in context:

            kwargs[
                name
            ] = context[
                name
            ]

            continue


        alias = ALIASES.get(
            name
        )


        if (
            alias

            and

            alias in context
        ):

            kwargs[
                name
            ] = context[
                alias
            ]

            continue


        if (
            parameter.default
            is not
            inspect.Parameter.empty
        ):

            continue


        unresolved.append(
            name
        )


    if unresolved:

        raise RuntimeError(
            (
                function.__module__
                + "."
                + function.__name__
                + " unresolved parameters: "
                + ", ".join(
                    unresolved
                )
                + " signature="
                + str(
                    signature
                )
            )
        )


    return function(
        **kwargs
    )


def main():
    ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )


    print()
    print(
        "=============================================="
    )

    print(
        " VI1510.1 V2 GENERALIZATION PIPELINE"
    )

    print(
        "=============================================="
    )


    resolved = partitioned_resolve()


    partitions = extract_partitions(
        resolved
    )


    print(
        "PARTITIONS RESOLVED:",
        len(
            partitions
        )
    )


    run_reports = []

    blockers = []


    for index, partition in enumerate(
        partitions
    ):

        if not isinstance(
            partition,
            dict
        ):

            partition = {
                "value":
                    partition
            }


        topic = partition_name(
            partition,
            index,
        )


        run_dir = (
            ROOT
            / "runs"
            / (
                f"{index + 1:02d}_"
                + slug(
                    topic
                )
            )
        )


        run_dir.mkdir(
            parents=True,
            exist_ok=True,
        )


        print()
        print(
            "----------------------------------------------"
        )

        print(
            "PARTITION",
            index + 1,
            "|",
            topic
        )

        print(
            "----------------------------------------------"
        )


        context = {
            "partition":
                partition,

            "resolved":
                resolved,

            "run_dir":
                run_dir,

            "base":
                BASE,

            "topic":
                topic,

            "scope":
                (
                    partition.get(
                        "scope"
                    )
                    or
                    partition.get(
                        "narrative_scope"
                    )
                    or
                    partition
                ),
        }


        try:

            scene_usage = invoke(
                collect_scene_usage,
                context,
            )


            context[
                "scene_usage"
            ] = scene_usage


            print(
                "SCENE USAGE:",
                (
                    len(
                        scene_usage.get(
                            "used_assets",
                            []
                        )
                    )
                    if isinstance(
                        scene_usage,
                        dict
                    )
                    else "UNKNOWN"
                )
            )


            metadata = invoke(
                collect_source_metadata,
                context,
            )


            context[
                "metadata"
            ] = metadata


            context[
                "metadata_records"
            ] = (
                metadata.get(
                    "records",
                    []
                )

                if isinstance(
                    metadata,
                    dict
                )

                else []
            )


            print(
                "METADATA RECORDS:",
                len(
                    context[
                        "metadata_records"
                    ]
                )
            )


            # VI1510.1 V2.4 APPLY SOURCE-USAGE JOIN
            scene_usage = run_source_usage_join(
                scene_usage,
                metadata,
                run_dir,
            )

            relevance = invoke(
                run_relevance,
                context,
            )


            context[
                "relevance"
            ] = relevance


            lineage = run_lineage(
                scene_usage,
                metadata,
                run_dir,
            )


            context[
                "lineage"
            ] = lineage


            evidence_gate = (
                run_evidence_gate(
                    scene_usage,
                    metadata,
                    relevance,
                    lineage,
                    run_dir,
                )
            )


            report = {
                "index":
                    index + 1,

                "topic":
                    topic,

                "run_dir":
                    str(
                        run_dir
                    ),

                "scene_usage":
                    scene_usage,

                "metadata":
                    metadata,

                "relevance":
                    relevance,

                "lineage":
                    lineage,

                "evidence_gate":
                    evidence_gate,
            }


            run_reports.append(
                report
            )


            print(
                "LINEAGE:",
                lineage.get(
                    "strictly_linked_unique_assets"
                ),
                "/",
                lineage.get(
                    "unique_used_assets"
                )
            )


            print(
                "EVIDENCE GATE:",
                evidence_gate.get(
                    "status"
                )
            )


        except Exception as exc:

            error = (
                type(
                    exc
                ).__name__
                + ": "
                + str(
                    exc
                )
            )


            blockers.append({
                "partition":
                    index + 1,

                "topic":
                    topic,

                "error":
                    error,
            })


            print(
                "PARTITION HOLD:",
                error
            )


    cross_topic = run_cross_topic(
        run_reports,
        ROOT,
    )


    certified_runs = sum(
        1

        for row in run_reports

        if (
            row.get(
                "evidence_gate",
                {}
            ).get(
                "status"
            )
            ==
            "VI1510_1_EVIDENCE_GATE_V2_CERTIFIED"
        )
    )


    global_blockers = list(
        blockers
    )


    if not run_reports:

        global_blockers.append({
            "error":
                "no_successful_partition_runs"
        })


    if (
        cross_topic.get(
            "status"
        )
        !=
        "VI1510_1_CROSS_TOPIC_V3_CERTIFIED"
    ):

        global_blockers.append({
            "error":
                "cross_topic_v3_not_certified"
        })


    status = (
        "VI1510_1_V2_GENERALIZATION_CERTIFIED"

        if not global_blockers

        else

        "VI1510_1_V2_GENERALIZATION_HOLD"
    )


    summary = {
        "version":
            "1510.1-v2",

        "timestamp":
            datetime.now().isoformat(),

        "status":
            status,

        "resolved_partition_count":
            len(
                partitions
            ),

        "successful_partition_count":
            len(
                run_reports
            ),

        "certified_partition_count":
            certified_runs,

        "runs":
            run_reports,

        "cross_topic":
            cross_topic,

        "blockers":
            global_blockers,

        "network_executed":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "production_mutated":
            False,
    }


    dump(
        ROOT
        / "pipeline_summary.json",
        summary
    )


    dump(
        LOG_OUT,
        {
            "gate":
                summary
        }
    )


    print()
    print(
        "===== VI1510.1 V2 SUMMARY ====="
    )

    print(
        "RESOLVED PARTITIONS:",
        len(
            partitions
        )
    )

    print(
        "SUCCESSFUL PARTITIONS:",
        len(
            run_reports
        )
    )

    print(
        "CERTIFIED PARTITIONS:",
        certified_runs
    )

    print(
        "CROSS TOPIC:",
        cross_topic.get(
            "status"
        )
    )

    print(
        "BLOCKERS:",
        global_blockers
    )


    print()
    print(
        "NETWORK EXECUTED: False"
    )

    print(
        "FFMPEG EXECUTED: False"
    )

    print(
        "VIDEO GENERATED: False"
    )

    print(
        "PRODUCTION MUTATED: False"
    )


    print()
    print(
        "STATUS:",
        status
    )


    if global_blockers:

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
