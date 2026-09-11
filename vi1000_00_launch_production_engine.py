#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import re

from collections import Counter
from pathlib import Path


VERSION = "1000.00"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

LOG = (
    BASE /
    "logs/producao"
)

CONFIG = (
    BASE /
    "config/vi1000_launch_policy.json"
)

LAUNCH_DIR = (
    BASE /
    "temp/vi1000_launch"
)

BLUEPRINT = (
    LAUNCH_DIR /
    "launch_blueprint.json"
)

BATCH = (
    LAUNCH_DIR /
    "batch_blueprint.json"
)

ACTIVE_MANIFEST = (
    LAUNCH_DIR /
    "active_manifest.json"
)

OUT = (
    LOG /
    "vi1000_00_launch_production_engine_latest.json"
)

VI900_MANIFEST = (
    BASE /
    "temp/vi900_publish/portfolio_manifest.json"
)


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def load_json(path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def normalize(value):
    text = str(
        value or ""
    ).lower()

    text = (
        text
        .replace("_", " ")
        .replace("-", " ")
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def discover_scene_maps():
    root = (
        BASE /
        "roteiros"
    )

    if not root.exists():
        return []

    result = []

    for path in root.glob(
        "scene_map_*.json"
    ):
        match = re.match(
            r"scene_map_(.+)\.json$",
            path.name
        )

        if not match:
            continue

        result.append({
            "short_id":
                match.group(1),

            "path":
                path,

            "mtime":
                path.stat().st_mtime,
        })

    result.sort(
        key=lambda item:
            item["mtime"],
        reverse=True
    )

    return result


def resolve_short_id(
    requested=None
):
    if requested:
        return requested

    env = (
        os.getenv(
            "SHORT_ID"
        )
        or
        os.getenv(
            "SHORTAUTO_SHORT_ID"
        )
    )

    if env:
        return env

    discovered = (
        discover_scene_maps()
    )

    if not discovered:
        return None

    return discovered[0][
        "short_id"
    ]


def scene_map_path(
    short_id
):
    candidates = [
        BASE /
        "roteiros" /
        f"scene_map_{short_id}.json",

        BASE /
        f"scene_map_{short_id}.json",
    ]

    for path in candidates:
        if path.exists():
            return path

    return None


def motion_plan_path(
    short_id
):
    candidates = [
        BASE /
        "roteiros" /
        f"motion_plan_{short_id}.json",

        BASE /
        f"motion_plan_{short_id}.json",
    ]

    for path in candidates:
        if path.exists():
            return path

    return None


def extract_scenes(data):
    scenes = []

    if isinstance(
        data,
        list
    ):
        raw = data

    elif isinstance(
        data,
        dict
    ):
        raw = (
            data.get(
                "scenes"
            )
            or
            data.get(
                "scene_map"
            )
            or
            data.get(
                "items"
            )
            or []
        )

        if not raw:
            for key, value in (
                data.items()
            ):
                if not isinstance(
                    value,
                    dict
                ):
                    continue

                match = re.search(
                    r"(\d+)",
                    str(key)
                )

                if not match:
                    continue

                item = dict(
                    value
                )

                item[
                    "_scene_number"
                ] = int(
                    match.group(1)
                )

                raw.append(
                    item
                )

    else:
        raw = []

    for index, item in enumerate(
        raw,
        start=1
    ):
        if not isinstance(
            item,
            dict
        ):
            continue

        scene = (
            item.get(
                "scene"
            )
            or
            item.get(
                "scene_number"
            )
            or
            item.get(
                "numero"
            )
            or
            item.get(
                "_scene_number"
            )
            or
            index
        )

        try:
            scene = int(
                scene
            )

        except Exception:
            scene = index

        # IMPORTANT:
        # ShortAutoPro's actual narrated field
        # is "segment".
        segment = str(
            item.get(
                "segment"
            )
            or
            item.get(
                "trecho"
            )
            or
            item.get(
                "texto"
            )
            or
            item.get(
                "narration"
            )
            or ""
        )

        scenes.append({
            "scene":
                scene,

            "segment":
                segment,

            "raw":
                item,
        })

    scenes.sort(
        key=lambda item:
            item[
                "scene"
            ]
    )

    return scenes


DOCUMENT_TERMS = {
    "autópsia",
    "autopsia",
    "laudo",
    "documento",
    "relatório",
    "relatorio",
    "registro",
    "record",
    "report",
    "document",
    "police report",
}


EVIDENCE_TERMS = {
    "câmera",
    "camera",
    "filmagem",
    "vídeo",
    "video",
    "imagens",
    "surveillance",
    "footage",
    "evidence",
    "prova",
}


HUMAN_TERMS = {
    "mulher",
    "homem",
    "pessoa",
    "estudante",
    "funcionário",
    "funcionario",
    "funcionários",
    "funcionarios",
    "woman",
    "man",
    "person",
    "student",
}


OBJECT_TERMS = {
    "medicação",
    "medicacao",
    "remédio",
    "remedio",
    "medicamento",
    "caixa d'água",
    "caixa dagua",
    "water tank",
    "water tower",
    "bottle",
    "medicine",
}


LOCATION_TERMS = {
    "hotel",
    "corredor",
    "hallway",
    "elevador",
    "elevator",
    "telhado",
    "topo",
    "rooftop",
    "prédio",
    "predio",
    "building",
    "quarto",
    "room",
}


FACTUAL_TERMS = (
    DOCUMENT_TERMS
    | EVIDENCE_TERMS
)


def has_any(
    text,
    terms
):
    return any(
        term in text
        for term in terms
    )


def classify_scene(
    scene,
    total
):
    text = normalize(
        scene[
            "segment"
        ]
    )

    if has_any(
        text,
        DOCUMENT_TERMS
    ):
        role = "DOCUMENT"

    elif has_any(
        text,
        EVIDENCE_TERMS
    ):
        role = "EVIDENCE"

    elif has_any(
        text,
        OBJECT_TERMS
    ):
        role = "OBJECT"

    elif has_any(
        text,
        HUMAN_TERMS
    ):
        role = "HUMAN"

    elif has_any(
        text,
        LOCATION_TERMS
    ):
        role = "LOCATION"

    else:
        role = "CONTEXT"


    factual = has_any(
        text,
        FACTUAL_TERMS
    )


    identity_risk = (
        role == "HUMAN"
    )


    if factual:
        epistemic_mode = (
            "CASE_SPECIFIC_REQUIRED"
        )

    elif role == "HUMAN":
        epistemic_mode = (
            "ILLUSTRATIVE_NO_IDENTITY_ATTRIBUTION"
        )

    elif role in {
        "LOCATION",
        "OBJECT",
        "CONTEXT",
    }:
        epistemic_mode = (
            "ILLUSTRATIVE_ALLOWED"
        )

    else:
        epistemic_mode = (
            "CONTEXTUAL"
        )


    hook_priority = (
        100
        if scene[
            "scene"
        ] == 1
        else
        0
    )


    cta = (
        scene[
            "scene"
        ]
        == total
    )


    return {
        "scene":
            scene[
                "scene"
            ],

        "segment":
            scene[
                "segment"
            ],

        "role":
            role,

        "epistemic_mode":
            epistemic_mode,

        "identity_risk":
            identity_risk,

        "factual_claim":
            factual,

        "hook_priority":
            hook_priority,

        "cta":
            cta,
    }


def extract_anchor_terms(
    scenes
):
    combined = " ".join(
        scene[
            "segment"
        ]
        for scene in scenes
    )

    candidates = re.findall(
        r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ]"
        r"[A-Za-zÀ-ÿ]+"
        r"(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ]"
        r"[A-Za-zÀ-ÿ]+){0,3}",
        combined
    )

    stop = {
        "Cinco",
        "Mas",
        "Após",
        "Apos",
        "Quando",
        "Segundo",
        "Funcionários",
        "Funcionarios",
        "O",
        "A",
        "Os",
        "As",
        "Um",
        "Uma",
    }

    cleaned = []

    for value in candidates:
        value = value.strip()

        if value in stop:
            continue

        if len(
            value
        ) < 3:
            continue

        if value not in cleaned:
            cleaned.append(
                value
            )

    return cleaned[:8]


def ideal_query(
    scene,
    anchors
):
    role = scene[
        "role"
    ]

    segment = normalize(
        scene[
            "segment"
        ]
    )

    anchor = (
        anchors[0]
        if anchors
        else ""
    )


    if (
        scene[
            "epistemic_mode"
        ]
        == "CASE_SPECIFIC_REQUIRED"
    ):
        if role == "DOCUMENT":
            query = (
                f"{anchor} official report document"
            )

        elif role == "EVIDENCE":
            query = (
                f"{anchor} archival surveillance evidence"
            )

        else:
            query = (
                f"{anchor} archival {role.lower()}"
            )

    elif role == "LOCATION":
        if (
            "corredor"
            in segment
            or
            "hallway"
            in segment
        ):
            query = (
                "hotel hallway corridor interior"
            )

        elif (
            "elevador"
            in segment
            or
            "elevator"
            in segment
        ):
            query = (
                "hotel elevator interior doors"
            )

        elif (
            "telhado"
            in segment
            or
            "topo"
            in segment
            or
            "rooftop"
            in segment
        ):
            query = (
                "hotel rooftop building"
            )

        else:
            query = (
                "hotel building exterior"
            )

    elif role == "HUMAN":
        query = (
            "anonymous person back view "
            "contextual reenactment"
        )

    elif role == "OBJECT":
        if (
            "medic"
            in segment
            or
            "reméd"
            in segment
        ):
            query = (
                "generic medication "
                "prescription bottle neutral"
            )

        else:
            query = (
                "contextual object b-roll"
            )

    elif role == "DOCUMENT":
        query = (
            f"{anchor} archival document"
        )

    else:
        query = (
            f"{anchor} contextual archival"
            if anchor
            else
            "contextual documentary b-roll"
        )


    return re.sub(
        r"\s+",
        " ",
        query
    ).strip()


def provider_route(
    scene
):
    role = scene[
        "role"
    ]

    factual = scene[
        "factual_claim"
    ]

    if factual:
        if role == "DOCUMENT":
            return [
                "WIKIMEDIA_COMMONS",
                "INTERNET_ARCHIVE",
                "WIKIPEDIA_CONTEXT_ONLY",
            ]

        return [
            "WIKIMEDIA_COMMONS",
            "INTERNET_ARCHIVE",
        ]

    if role in {
        "LOCATION",
        "OBJECT",
    }:
        return [
            "WIKIMEDIA_COMMONS",
            "CURRENT_MEDIA",
        ]

    if role == "HUMAN":
        return [
            "WIKIMEDIA_COMMONS",
            "CURRENT_MEDIA",
        ]

    return [
        "CURRENT_MEDIA",
        "WIKIMEDIA_COMMONS",
    ]


def build_search_specs(
    classified,
    anchors
):
    specs = []

    for scene in classified:
        specs.append({
            "scene":
                scene[
                    "scene"
                ],

            "role":
                scene[
                    "role"
                ],

            "query":
                ideal_query(
                    scene,
                    anchors
                ),

            "providers":
                provider_route(
                    scene
                ),

            "query_is_evidence":
                False,

            "identity_guard":
                scene[
                    "identity_risk"
                ],

            "case_specific_required":
                (
                    scene[
                        "epistemic_mode"
                    ]
                    ==
                    "CASE_SPECIFIC_REQUIRED"
                ),

            "illustration_label_required":
                (
                    scene[
                        "epistemic_mode"
                    ]
                    ==
                    "ILLUSTRATIVE_ALLOWED"
                    or
                    scene[
                        "role"
                    ]
                    in {
                        "HUMAN",
                        "OBJECT",
                    }
                ),
        })

    return specs


def derive_source_group(
    scene,
    entry
):
    group = entry.get(
        "source_group"
    )

    if group:
        return group

    title = normalize(
        entry.get(
            "source_title"
        )
        or
        entry.get(
            "title"
        )
    )

    if (
        "elisa lam"
        in title
        and
        "elevator"
        in title
    ):
        return (
            "authentic_case_archive"
        )

    if (
        "hotel cecil"
        in title
    ):
        return (
            "verified_specific_location"
        )

    digest = entry.get(
        "expected_sha256"
    )

    if digest:
        return (
            "asset_"
            + digest[:16]
        )

    return (
        f"scene_{scene}_current"
    )


def maximum_run(
    groups
):
    previous = None
    current = 0
    maximum = 0

    for group in groups:
        if group == previous:
            current += 1

        else:
            previous = group
            current = 1

        maximum = max(
            maximum,
            current
        )

    return maximum


def audit_manifest(
    manifest,
    policy
):
    scenes = (
        manifest.get(
            "scenes",
            {}
        )
    )

    sequence = []

    counts = Counter()

    hash_map = {}

    title_map = {}

    blockers = []

    warnings = []


    for number in sorted(
        int(key)
        for key in scenes
        if str(key).isdigit()
    ):
        entry = scenes[
            str(number)
        ]

        group = derive_source_group(
            number,
            entry
        )

        counts[
            group
        ] += 1

        digest = entry.get(
            "expected_sha256"
        )

        title = entry.get(
            "source_title"
        ) or entry.get(
            "title"
        )


        if digest:
            hash_map.setdefault(
                digest,
                []
            ).append(
                number
            )


        if title:
            title_map.setdefault(
                str(title),
                []
            ).append(
                number
            )


        sequence.append({
            "scene":
                number,

            "source_group":
                group,

            "title":
                title,

            "override_active":
                bool(
                    entry.get(
                        "override_active"
                    )
                ),

            "illustration_label":
                bool(
                    entry.get(
                        "illustration_label"
                    )
                ),

            "epistemic_usage":
                entry.get(
                    "epistemic_usage"
                ),
        })


    groups = [
        item[
            "source_group"
        ]
        for item in sequence
    ]


    unique_count = len(
        set(groups)
    )

    total = len(
        groups
    )

    ratio = (
        unique_count
        / total
        if total
        else 0
    )


    diversity = policy[
        "diversity_policy"
    ]


    if (
        ratio
        <
        diversity[
            "minimum_unique_source_ratio"
        ]
    ):
        blockers.append(
            "unique_source_ratio_too_low"
        )


    if (
        unique_count
        <
        diversity[
            "minimum_unique_source_groups"
        ]
        and
        total >= 12
    ):
        blockers.append(
            "unique_source_group_count_too_low"
        )


    max_run = maximum_run(
        groups
    )


    if (
        max_run
        >
        diversity[
            "maximum_consecutive_same_source_group"
        ]
    ):
        blockers.append(
            "consecutive_source_repetition"
        )


    windows = []

    for start in range(
        0,
        max(
            0,
            total - 5
        )
    ):
        part = sequence[
            start:
            start + 6
        ]

        if len(part) < 6:
            continue

        unique = len({
            item[
                "source_group"
            ]
            for item in part
        })

        windows.append({
            "start":
                part[0][
                    "scene"
                ],

            "end":
                part[-1][
                    "scene"
                ],

            "unique":
                unique,
        })

        if (
            unique
            <
            diversity[
                "minimum_unique_sources_per_6_scene_window"
            ]
        ):
            blockers.append(
                "low_6_scene_window_diversity:"
                f"{part[0]['scene']}-"
                f"{part[-1]['scene']}"
            )


    duplicate_hashes = {
        digest:
            scenes

        for digest, scenes
        in hash_map.items()

        if len(
            scenes
        ) > 1
    }


    return {
        "scene_count":
            total,

        "unique_source_count":
            unique_count,

        "unique_source_ratio":
            round(
                ratio,
                3
            ),

        "source_counts":
            dict(
                counts
            ),

        "maximum_consecutive_same_source":
            max_run,

        "windows":
            windows,

        "duplicate_hashes":
            duplicate_hashes,

        "sequence":
            sequence,

        "blockers":
            sorted(
                set(
                    blockers
                )
            ),

        "warnings":
            warnings,
    }


def build_pipeline_steps():
    return [
        {
            "order": 1,
            "name":
                "SCRIPT_GENERATION",

            "status":
                "NOT_EXECUTED",
        },
        {
            "order": 2,
            "name":
                "SCENE_MAP",

            "status":
                "NOT_EXECUTED",
        },
        {
            "order": 3,
            "name":
                "SEMANTIC_CLASSIFICATION",

            "status":
                "PLANNED",
        },
        {
            "order": 4,
            "name":
                "ENTITY_TRUTH_ANALYSIS",

            "status":
                "PLANNED",
        },
        {
            "order": 5,
            "name":
                "MEDIA_SEARCH",

            "status":
                "DISABLED_IN_VI1000_BUILD",
        },
        {
            "order": 6,
            "name":
                "CANDIDATE_HARDENING",

            "status":
                "PLANNED",
        },
        {
            "order": 7,
            "name":
                "GLOBAL_VISUAL_DIRECTOR",

            "status":
                "PLANNED",
        },
        {
            "order": 8,
            "name":
                "TRUTH_GATE",

            "status":
                "PLANNED",
        },
        {
            "order": 9,
            "name":
                "DIVERSITY_GATE",

            "status":
                "PLANNED",
        },
        {
            "order": 10,
            "name":
                "RENDER_CANARY",

            "status":
                "DISABLED",
        },
        {
            "order": 11,
            "name":
                "AUDIO_SUBTITLES",

            "status":
                "DISABLED",
        },
        {
            "order": 12,
            "name":
                "FINAL_QC",

            "status":
                "PLANNED",
        },
        {
            "order": 13,
            "name":
                "PUBLISH_PACKAGE",

            "status":
                "DISABLED",
        },
    ]


def build_batch_blueprint():
    slots = []

    for number in range(
        1,
        4
    ):
        slots.append({
            "slot":
                number,

            "status":
                "PLANNED_NOT_GENERATED",

            "topic":
                None,

            "short_id":
                None,

            "video_generated":
                False,

            "network_executed":
                False,

            "renderer_enabled":
                False,

            "required_gates": [
                "SCRIPT",
                "SCENE_MAP",
                "TRUTH",
                "IDENTITY",
                "MEDIA",
                "DIVERSITY",
                "TECHNICAL",
                "VISUAL_REVIEW",
            ],
        })

    return {
        "version":
            VERSION,

        "batch_size":
            3,

        "status":
            "PLANNED_ONLY",

        "slots":
            slots,

        "automatic_publish":
            False,

        "video_generation":
            False,
    }


def static_core_audit():
    targets = [
        BASE /
        "video.py",

        BASE /
        "v6.py",

        BASE /
        "gerar_short.sh",

        BASE /
        "vi6_95_scene_executor.py",
    ]

    report = {}

    for path in targets:
        if not path.exists():
            report[
                path.name
            ] = {
                "exists":
                    False,
            }

            continue

        text = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        report[
            path.name
        ] = {
            "exists":
                True,

            "sha256":
                sha256(
                    path
                ),

            "has_vi700_hook":
                (
                    "VI700_CANARY_MODE"
                    in text
                ),

            "has_vi730_delegate":
                (
                    "VI730_CANARY_MODE"
                    in text
                ),

            "has_ffmpeg":
                (
                    "ffmpeg"
                    in text.lower()
                ),
        }

    return report


def evaluate(
    requested_short_id=None
):
    policy = load_json(
        CONFIG
    )

    short_id = resolve_short_id(
        requested_short_id
    )

    blockers = []

    warnings = []


    if not short_id:
        blockers.append(
            "short_id_not_resolved"
        )


    scene_path = (
        scene_map_path(
            short_id
        )
        if short_id
        else None
    )

    motion_path = (
        motion_plan_path(
            short_id
        )
        if short_id
        else None
    )


    if not scene_path:
        blockers.append(
            "scene_map_missing"
        )

        scenes = []

    else:
        scenes = extract_scenes(
            load_json(
                scene_path
            )
        )


    if not scenes:
        blockers.append(
            "no_scenes_extracted"
        )


    classified = [
        classify_scene(
            scene,
            len(scenes)
        )
        for scene in scenes
    ]


    anchors = (
        extract_anchor_terms(
            scenes
        )
    )


    search_specs = (
        build_search_specs(
            classified,
            anchors
        )
    )


    preferred = (
        policy[
            "scene_policy"
        ][
            "preferred_scene_count"
        ]
    )


    if (
        scenes
        and len(
            scenes
        )
        != preferred
    ):
        warnings.append(
            "scene_count_not_preferred"
        )


    if (
        scenes
        and len(
            scenes
        )
        <
        policy[
            "scene_policy"
        ][
            "minimum_scene_count"
        ]
    ):
        blockers.append(
            "scene_count_below_minimum"
        )


    if (
        scenes
        and len(
            scenes
        )
        >
        policy[
            "scene_policy"
        ][
            "maximum_scene_count"
        ]
    ):
        blockers.append(
            "scene_count_above_maximum"
        )


    benchmark = None


    if VI900_MANIFEST.exists():
        benchmark_manifest = (
            load_json(
                VI900_MANIFEST
            )
        )

        benchmark = (
            audit_manifest(
                benchmark_manifest,
                policy
            )
        )


        if benchmark[
            "blockers"
        ]:
            warnings.append(
                "vi900_benchmark_has_diversity_findings"
            )


        ACTIVE_MANIFEST.write_text(
            json.dumps(
                benchmark_manifest,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )


    blueprint = {
        "version":
            VERSION,

        "short_id":
            short_id,

        "scene_map":
            (
                str(
                    scene_path
                )
                if scene_path
                else None
            ),

        "motion_plan":
            (
                str(
                    motion_path
                )
                if motion_path
                else None
            ),

        "anchors":
            anchors,

        "scenes":
            classified,

        "search_specs":
            search_specs,

        "fallback_policy":
            policy[
                "fallback_policy"
            ],

        "pipeline":
            build_pipeline_steps(),

        "renderer_activation":
            False,

        "video_generation":
            False,

        "network_execution":
            False,

        "automatic_publish":
            False,
    }


    LAUNCH_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    BLUEPRINT.write_text(
        json.dumps(
            blueprint,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    batch = (
        build_batch_blueprint()
    )


    BATCH.write_text(
        json.dumps(
            batch,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    core = static_core_audit()


    status = (
        "VI1000_LAUNCH_PRODUCTION_ENGINE_CERTIFIED"
        if not blockers
        else
        "HOLD"
    )


    report = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            short_id,

        "scene_count":
            len(
                scenes
            ),

        "anchor_terms":
            anchors,

        "classified_scenes":
            classified,

        "search_specs":
            search_specs,

        "benchmark_vi900":
            benchmark,

        "core_static_audit":
            core,

        "blueprint": {
            "path":
                str(
                    BLUEPRINT
                ),

            "sha256":
                sha256(
                    BLUEPRINT
                ),
        },

        "batch_blueprint": {
            "path":
                str(
                    BATCH
                ),

            "sha256":
                sha256(
                    BATCH
                ),
        },

        "active_manifest": (
            {
                "path":
                    str(
                        ACTIVE_MANIFEST
                    ),

                "sha256":
                    sha256(
                        ACTIVE_MANIFEST
                    ),
            }
            if ACTIVE_MANIFEST.exists()
            else None
        ),

        "blockers":
            blockers,

        "warnings":
            warnings,

        "source_recovery":
            "SHADOW_ONLY",

        "network_executed":
            False,

        "downloads_executed":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "renderer_activation":
            False,

        "automatic_publish":
            False,

        "production_media_mutated":
            False,

        "production_plan_mutated":
            False,

        "core_source_mutated":
            False,
    }


    LOG.mkdir(
        parents=True,
        exist_ok=True
    )


    OUT.write_text(
        json.dumps(
            {
                "gate":
                    report
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    return report


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--short-id",
        default=None
    )

    args = parser.parse_args()

    r = evaluate(
        args.short_id
    )

    print()
    print(
        "=============================================="
    )
    print(
        " VI1000 LAUNCH PRODUCTION ENGINE"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r[
            "status"
        ]
    )

    print(
        "SHORT ID:",
        r[
            "short_id"
        ]
    )

    print(
        "SCENES:",
        r[
            "scene_count"
        ]
    )

    print(
        "ANCHORS:",
        r[
            "anchor_terms"
        ]
    )

    print()
    print(
        "===== SCENE INTELLIGENCE ====="
    )

    for scene in (
        r[
            "classified_scenes"
        ]
    ):
        print(
            "SCENE",
            scene[
                "scene"
            ],
            "|",
            scene[
                "role"
            ],
            "|",
            scene[
                "epistemic_mode"
            ],
            "| factual=",
            scene[
                "factual_claim"
            ],
            "| identity=",
            scene[
                "identity_risk"
            ],
        )

    print()
    print(
        "===== SEARCH BLUEPRINT ====="
    )

    for item in (
        r[
            "search_specs"
        ]
    ):
        print(
            "SCENE",
            item[
                "scene"
            ],
            "|",
            item[
                "query"
            ],
            "|",
            item[
                "providers"
            ],
        )

    benchmark = (
        r.get(
            "benchmark_vi900"
        )
    )

    if benchmark:
        print()
        print(
            "===== VI900 BENCHMARK ====="
        )

        print(
            "UNIQUE SOURCES:",
            benchmark[
                "unique_source_count"
            ]
        )

        print(
            "UNIQUE RATIO:",
            benchmark[
                "unique_source_ratio"
            ]
        )

        print(
            "MAX RUN:",
            benchmark[
                "maximum_consecutive_same_source"
            ]
        )

        print(
            "BLOCKERS:",
            benchmark[
                "blockers"
            ]
        )

    print()
    print(
        "BLUEPRINT:",
        r[
            "blueprint"
        ]
    )

    print(
        "BATCH:",
        r[
            "batch_blueprint"
        ]
    )

    print(
        "ACTIVE MANIFEST:",
        r[
            "active_manifest"
        ]
    )

    print()
    print(
        "BLOCKERS:",
        r[
            "blockers"
        ]
    )

    print(
        "WARNINGS:",
        r[
            "warnings"
        ]
    )

    print()
    print(
        "NETWORK EXECUTED:",
        r[
            "network_executed"
        ]
    )

    print(
        "DOWNLOADS EXECUTED:",
        r[
            "downloads_executed"
        ]
    )

    print(
        "FFMPEG EXECUTED:",
        r[
            "ffmpeg_executed"
        ]
    )

    print(
        "VIDEO GENERATED:",
        r[
            "video_generated"
        ]
    )

    print(
        "RENDERER ACTIVATION:",
        r[
            "renderer_activation"
        ]
    )


if __name__ == "__main__":
    main()
