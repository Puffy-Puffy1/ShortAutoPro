#!/usr/bin/env python3

import hashlib
import importlib
import inspect
import json
import os
import shutil

from pathlib import Path

from media_provenance_capture_v1 import write_provenance
from vi1510_1_27_source_metadata_v2 import normalize_record
from vi1510_1_29_lineage_v2 import run as run_lineage


BASE = Path.home() / "ShortAutoPro"

WORK = (
    BASE
    / "temp"
    / "fresh_provenance_3topic_v1"
)

PROV = (
    BASE
    / "manifests"
    / "fresh_provenance_3topic_v1"
)

shutil.rmtree(
    WORK,
    ignore_errors=True,
)

shutil.rmtree(
    PROV,
    ignore_errors=True,
)

WORK.mkdir(
    parents=True,
    exist_ok=True,
)

PROV.mkdir(
    parents=True,
    exist_ok=True,
)


def pick_function(module, names):
    for name in names:
        fn = getattr(
            module,
            name,
            None,
        )

        if (
            callable(fn)
            and
            getattr(
                fn,
                "__module__",
                None,
            )
            ==
            module.__name__
        ):
            return fn

    return None


def fallback_invoke(fn, context):
    aliases = {
        "resolved_run": "run",
        "partition": "run",
        "resolved": "run",

        "output_dir": "run_dir",
        "out_dir": "run_dir",

        "usage": "scene_usage",
        "scene_rows": "scene_usage",

        "metadata": "source_metadata",
        "metadata_pack": "source_metadata",

        "lineage_result": "lineage",
        "lineage_report": "lineage",

        "gate_result": "evidence_gate",
        "evidence": "evidence_gate",

        "partition_results": "partitions",
        "results": "partitions",
        "runs": "partitions",
        "run_reports": "partitions",
    }

    sig = inspect.signature(
        fn
    )

    kwargs = {}

    for name, param in sig.parameters.items():

        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        if name in context:
            kwargs[name] = context[name]
            continue

        alias = aliases.get(
            name
        )

        if (
            alias
            and
            alias in context
        ):
            kwargs[name] = context[
                alias
            ]

            continue

        if name in {
            "context",
            "ctx",
        }:
            kwargs[name] = context
            continue

        if (
            param.default
            is not
            inspect.Parameter.empty
        ):
            continue

        raise TypeError(
            f"UNRESOLVED PARAMETER: "
            f"{fn.__module__}.{fn.__name__}"
            f" -> {name}"
        )

    return fn(
        **kwargs
    )


pipeline = importlib.import_module(
    "vi1510_1_34_v2_pipeline"
)


def invoke(fn, context):
    existing = getattr(
        pipeline,
        "invoke",
        None,
    )

    if callable(existing):

        try:
            return existing(
                fn,
                context,
            )

        except Exception as exc:
            print(
                "PIPELINE_INVOKE_FALLBACK:",
                type(exc).__name__,
                str(exc)[:180],
            )

    return fallback_invoke(
        fn,
        context,
    )


def bad_values(value):
    bad = []

    if isinstance(
        value,
        dict,
    ):

        for child in value.values():
            bad.extend(
                bad_values(
                    child
                )
            )

    elif isinstance(
        value,
        list,
    ):

        for child in value:
            bad.extend(
                bad_values(
                    child
                )
            )

    elif isinstance(
        value,
        str,
    ):

        upper = value.strip().upper()

        if upper in {
            "FAIL",
            "FAILED",
            "HOLD",
            "REJECT",
            "REJECTED",
            "BLOCKED",
        }:
            bad.append(
                upper
            )

    return bad


relevance_module = importlib.import_module(
    "vi1510_1_28_relevance_v2"
)

relevance_module = importlib.import_module(
    "vi1510_1_28_relevance_v2"
)

gate_module = importlib.import_module(
    "vi1510_1_30_evidence_gate_v2"
)

cross_module = importlib.import_module(
    "vi1510_1_31_cross_topic_v3"
)


relevance_fn = pick_function(
    relevance_module,
    [
        "run",
        "evaluate",
        "score",
        "audit",
        "check",
        "build",
        "validate",
        "collect",
    ],
)


if relevance_fn is None:
    raise RuntimeError(
        "RELEVANCE CALLABLE NOT FOUND"
    )


gate_fn = pick_function(
    gate_module,
    [
        "run",
        "evaluate",
        "gate",
        "audit",
        "check",
        "build",
        "validate",
        "collect",
    ],
)

cross_fn = pick_function(
    cross_module,
    [
        "run",
        "evaluate",
        "cross_topic",
        "cross_topic_audit",
        "audit",
        "check",
        "build",
        "validate",
    ],
)


if gate_fn is None:
    raise RuntimeError(
        "EVIDENCE GATE CALLABLE NOT FOUND"
    )


if cross_fn is None:
    raise RuntimeError(
        "CROSS TOPIC CALLABLE NOT FOUND"
    )


print(
    "RELEVANCE_FUNCTION=",
    relevance_fn.__name__,
)

print(
    "EVIDENCE_GATE_FUNCTION=",
    gate_fn.__name__,
)

print(
    "CROSS_TOPIC_FUNCTION=",
    cross_fn.__name__,
)


topics = [
    "Deep ocean hydrothermal vents",
    "Ancient Roman road engineering",
    "Migration of monarch butterflies",
]

providers = [
    (
        "Wikimedia Commons",
        "https://commons.wikimedia.org/wiki/File:"
    ),
    (
        "Pexels",
        "https://www.pexels.com/photo/"
    ),
    (
        "Pixabay",
        "https://pixabay.com/photos/"
    ),
    (
        "Coverr",
        "https://coverr.co/videos/"
    ),
]


partition_results = []
failed = []


for pindex, topic in enumerate(
    topics,
    1,
):

    run_dir = (
        WORK
        / f"partition_{pindex:02d}"
    )

    provenance_dir = (
        PROV
        / f"partition_{pindex:02d}"
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    provenance_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    os.environ[
        "SAP_PROVENANCE_DIR"
    ] = str(
        provenance_dir
    )


    scene_rows = []
    metadata_records = []


    for scene in range(
        1,
        13,
    ):

        asset = (
            run_dir
            / f"asset_{scene:02d}.jpg"
        )

        asset.write_bytes(
            (
                f"FRESH|P{pindex}|"
                f"SCENE{scene}|{topic}"
            ).encode(
                "utf-8"
            )
        )

        digest = hashlib.sha256(
            asset.read_bytes()
        ).hexdigest()

        provider, prefix = providers[
            (scene - 1)
            %
            len(providers)
        ]

        candidate = {
            "provider":
                provider,

            "title":
                (
                    f"Source {scene:02d} "
                    f"for partition {pindex}"
                ),

            "license":
                "BENCHMARK-LICENSE",

            "artist":
                f"Author {scene:02d}",

            "source_group":
                (
                    f"FRESH:P{pindex}:"
                    f"{scene:02d}"
                ),

            "url":
                (
                    prefix
                    +
                    f"fresh_p{pindex}_"
                    f"{scene:02d}"
                ),

            "query":
                "POISON QUERY MUST NOT BE EVIDENCE",

            "search":
                "POISON SEARCH MUST NOT BE EVIDENCE",

            "topic":
                "POISON TOPIC MUST NOT BE EVIDENCE",
        }


        manifest = write_provenance(
            candidate,
            asset,
            method=(
                "fresh_3topic_generalization"
            ),
        )


        if (
            manifest is None
            or
            not manifest.exists()
        ):

            failed.append(
                f"P{pindex}:S{scene}:MANIFEST"
            )

            continue


        raw = json.loads(
            manifest.read_text(
                encoding="utf-8"
            )
        )


        record = normalize_record(
            raw,
            manifest,
        )


        if not isinstance(
            record,
            dict,
        ):

            failed.append(
                f"P{pindex}:S{scene}:METADATA"
            )

            continue


        serialized = json.dumps(
            record,
            ensure_ascii=False,
        )


        if (
            "POISON QUERY"
            in serialized
            or
            "POISON SEARCH"
            in serialized
            or
            "POISON TOPIC"
            in serialized
        ):

            failed.append(
                f"P{pindex}:S{scene}:LEAK"
            )


        metadata_records.append(
            record
        )

        scene_rows.append({
            "scene":
                scene,

            "path":
                str(
                    asset.resolve()
                ),

            "sha256":
                digest,
        })


    scene_usage = {
        "used_assets":
            scene_rows
    }

    metadata = {
        "records":
            metadata_records
    }


    lineage = run_lineage(
        scene_usage,
        metadata,
        run_dir,
    )


    linked = int(
        lineage.get(
            "strictly_linked_assets"
        )
        or 0
    )


    groups = {
        str(
            row.get(
                "source_group"
            )
            or ""
        )

        for row in metadata_records

        if row.get(
            "source_group"
        )
    }


    run = {
        "label":
            f"FRESH_{pindex}",

        "topic":
            topic,

        "status":
            "RESOLVED",

        "short_id":
            f"fresh_{pindex:02d}",

        "partitioned":
            True,
    }


    context = {
        "run":
            run,

        "partition":
            run,

        "run_dir":
            run_dir,

        "scene_usage":
            scene_usage,

        "source_metadata":
            metadata,

        "metadata":
            metadata,

        "metadata_records":
            metadata_records,

        "lineage":
            lineage,

        "lineage_result":
            lineage,
    }


    relevance = invoke(
        relevance_fn,
        context,
    )


    context[
        "relevance"
    ] = relevance


    relevance = invoke(
        relevance_fn,
        context,
    )


    context[
        "relevance"
    ] = relevance


    evidence_gate = invoke(
        gate_fn,
        context,
    )


    gate_bad = bad_values(
        evidence_gate
    )


    partition_ok = (
        len(
            scene_rows
        )
        ==
        12
        and
        len(
            metadata_records
        )
        ==
        12
        and
        linked
        ==
        12
        and
        len(
            groups
        )
        ==
        12
        and
        not gate_bad
    )


    if not partition_ok:
        failed.append(
            f"PARTITION_{pindex}"
        )


    result = {
        "label":
            run[
                "label"
            ],

        "topic":
            topic,

        "run":
            run,

        "scene_usage":
            scene_usage,

        "source_metadata":
            metadata,

        "lineage":
            lineage,

        "relevance":
            relevance,

        "evidence_gate":
            evidence_gate,

        "status":
            (
                "PASS"
                if partition_ok
                else "FAIL"
            ),
    }


    partition_results.append(
        result
    )


    print()
    print(
        "PARTITION=",
        pindex,
    )

    print(
        "SCENES=",
        len(
            scene_rows
        )
    )

    print(
        "METADATA=",
        len(
            metadata_records
        )
    )

    print(
        "UNIQUE_SOURCE_GROUPS=",
        len(
            groups
        )
    )

    print(
        "STRICT_LINEAGE=",
        linked,
    )

    print(
        "EVIDENCE_BAD_VALUES=",
        gate_bad,
    )

    print(
        "PARTITION_STATUS=",
        result[
            "status"
        ],
    )


cross_context = {
    "partitions":
        partition_results,

    "partition_results":
        partition_results,

    "results":
        partition_results,

    "runs":
        partition_results,

    "run_reports":
        partition_results,

    "run_dir":
        WORK,

    "context":
        {
            "partitions":
                partition_results
        },
}


cross_result = invoke(
    cross_fn,
    cross_context,
)


cross_bad = bad_values(
    cross_result
)


if cross_bad:
    failed.append(
        "CROSS_TOPIC"
    )


print()
print(
    "CROSS_BAD_VALUES=",
    cross_bad,
)


report = {
    "schema":
        "SHORTAUTOPRO_FRESH_3TOPIC_V1",

    "partitions":
        partition_results,

    "cross_topic":
        cross_result,

    "failed":
        failed,

    "network_executed":
        False,

    "ffmpeg_executed":
        False,

    "video_generated":
        False,
}


report_file = (
    WORK
    / "report.json"
)

report_file.write_text(
    json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


print()
print(
    "FAILED=",
    failed,
)


if failed:
    raise SystemExit(
        1
    )


cert = {
    "status":
        "CERTIFIED",

    "partitions":
        3,

    "scenes_per_partition":
        12,

    "strict_lineage_total":
        36,

    "query_as_evidence":
        False,

    "network":
        False,

    "ffmpeg":
        False,

    "video":
        False,
}


(
    WORK
    / "CERTIFIED.json"
).write_text(
    json.dumps(
        cert,
        indent=2,
    ),
    encoding="utf-8",
)


print(
    "STATUS: FRESH_3TOPIC_PROVENANCE_CERTIFIED"
)
