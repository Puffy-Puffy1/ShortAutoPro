#!/usr/bin/env python3

import copy
import hashlib
import json
import re
from pathlib import Path
from collections import Counter


VERSION = "550.00"

BASE = Path.home() / "ShortAutoPro"
LOG = BASE / "logs/producao"

VI330 = LOG / "vi330_00_controlled_real_ab_latest.json"
VI420 = LOG / "vi420_00_batch_deep_ab_latest.json"
VI500 = LOG / "vi500_00_global_provenance_identity_latest.json"

OUT = (
    LOG /
    "vi550_00_role_provenance_repair_latest.json"
)

SHADOW = (
    BASE /
    "temp/vi550_shadow/"
    "motion_plan_2026-09-01_1433_vi550_shadow.json"
)


TEXT_EXTENSIONS = {
    ".json",
    ".txt",
    ".log",
    ".csv",
    ".md",
}

MAX_TRACE_FILE = 3_000_000
MAX_TRACE_FILES = 2500


HUMAN_TERMS = {
    "person",
    "woman",
    "man",
    "girl",
    "boy",
    "face",
    "portrait",
    "human",
    "silhouette",
}


ROLE_TERMS = {
    "ROOFTOP": {
        "rooftop",
        "roof",
        "water tower",
        "water towers",
        "water tank",
    },

    "HALLWAY": {
        "hallway",
        "corridor",
    },

    "ELEVATOR": {
        "elevator",
        "lift",
        "elevador",
    },

    "SURVEILLANCE": {
        "cctv",
        "security camera",
        "surveillance",
    },

    "DOCUMENT": {
        "document",
        "record",
        "report",
        "paper",
        "certificate",
        "file",
    },

    "MEDICINE": {
        "medicine",
        "medication",
        "prescription",
        "pill",
        "bottle",
    },

    "FACADE": {
        "facade",
        "façade",
        "street",
        "exterior",
        "building",
    },
}


def load_gate(path, required=False):
    if not path.exists():
        if required:
            raise RuntimeError(
                f"missing:{path.name}"
            )
        return {}

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return data.get(
        "gate",
        data
    )


def normalize(value):
    text = str(value or "")

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"^\s*File\s*:\s*",
        "",
        text,
        flags=re.I
    )

    text = (
        text
        .replace("_", " ")
        .replace("-", " ")
        .lower()
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


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


def by_scene(items):
    result = {}

    for item in items or []:
        try:
            scene = int(
                item.get("scene")
            )

        except Exception:
            continue

        result[scene] = item

    return result


def load_scene_map(short_id):
    path = (
        BASE /
        "roteiros" /
        f"scene_map_{short_id}.json"
    )

    if not path.exists():
        raise RuntimeError(
            "scene_map_missing"
        )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return by_scene(
        data.get("scenes")
        or []
    )


def visual_text(scene):
    parts = []

    query = scene.get("query")

    if query:
        parts.append(
            str(query)
        )

    must = scene.get(
        "must_have"
    )

    if isinstance(
        must,
        list
    ):
        parts.extend(
            str(x)
            for x in must
        )

    elif must:
        parts.append(
            str(must)
        )

    return " ".join(parts)


def narration_text(scene):
    return str(
        scene.get("segment")
        or ""
    )


def term_hits(
    text,
    terms
):
    low = normalize(text)

    return sorted({
        term
        for term in terms
        if term in low
    })


def derive_role(
    category,
    visual
):
    category = str(
        category or "GENERAL"
    ).upper()

    scores = {}

    for role, terms in (
        ROLE_TERMS.items()
    ):
        hits = term_hits(
            visual,
            terms
        )

        if hits:
            scores[role] = {
                "hits":
                    hits,

                "count":
                    len(hits),
            }

    preferred_order = [
        "ROOFTOP",
        "ELEVATOR",
        "HALLWAY",
        "SURVEILLANCE",
        "MEDICINE",
        "FACADE",
        "DOCUMENT",
    ]

    for role in preferred_order:
        if role in scores:
            return role, scores

    if category == "FACE":
        return "GENERIC_HUMAN", scores

    if category == "DOCUMENT":
        return "DOCUMENT", scores

    if category == "EVIDENCE":
        return "SURVEILLANCE", scores

    if category == "OBJECT":
        return "OBJECT", scores

    if category == "LOCATION":
        return "LOCATION", scores

    return "GENERAL", scores


def repair_scene_role(
    scene_num,
    old_category,
    scene,
    known_entities
):
    visual = visual_text(
        scene
    )

    narration = narration_text(
        scene
    )

    low_visual = normalize(
        visual
    )

    old_category = str(
        old_category
        or "GENERAL"
    ).upper()

    human_hits = term_hits(
        visual,
        HUMAN_TERMS
    )

    role, role_scores = (
        derive_role(
            old_category,
            visual
        )
    )

    visual_entities = [
        entity
        for entity in known_entities
        if (
            normalize(entity)
            and normalize(entity)
            in low_visual
        )
    ]

    narration_entities = [
        entity
        for entity in known_entities
        if (
            normalize(entity)
            and normalize(entity)
            in normalize(
                narration
            )
        )
    ]

    repaired_category = (
        old_category
    )

    repair_applied = False

    repair_reason = None

    if (
        old_category == "FACE"
        and not human_hits
        and role
        in {
            "ROOFTOP",
            "HALLWAY",
            "ELEVATOR",
            "FACADE",
        }
    ):
        repaired_category = (
            "LOCATION"
        )

        repair_applied = True

        repair_reason = (
            "face_category_without_human_visual"
        )

    elif (
        old_category == "FACE"
        and not human_hits
        and role
        in {
            "MEDICINE",
            "OBJECT",
        }
    ):
        repaired_category = (
            "OBJECT"
        )

        repair_applied = True

        repair_reason = (
            "face_category_contains_object_visual"
        )

    if (
        old_category == "FACE"
        and human_hits
        and not visual_entities
    ):
        identity_mode = (
            "ANONYMOUS_ILLUSTRATIVE_HUMAN"
        )

        identity_search_allowed = True

        identity_attribution_allowed = False

    elif visual_entities:
        identity_mode = (
            "EXPLICIT_VISUAL_ENTITY"
        )

        identity_search_allowed = True

        identity_attribution_allowed = True

    else:
        identity_mode = (
            "IDENTITY_NOT_REQUIRED"
        )

        identity_search_allowed = (
            repaired_category
            != "FACE"
        )

        identity_attribution_allowed = False

    return {
        "scene":
            scene_num,

        "old_category":
            old_category,

        "repaired_category":
            repaired_category,

        "role":
            (
                "GENERIC_HUMAN"
                if (
                    repaired_category
                    == "FACE"
                    and human_hits
                )
                else role
            ),

        "repair_applied":
            repair_applied,

        "repair_reason":
            repair_reason,

        "visual_text":
            visual,

        "human_hits":
            human_hits,

        "role_evidence":
            role_scores,

        "visual_entities":
            visual_entities,

        "narration_entities":
            narration_entities,

        "identity_mode":
            identity_mode,

        "identity_search_allowed":
            identity_search_allowed,

        "identity_attribution_allowed":
            identity_attribution_allowed,
    }


def epistemic_mode(
    scene_num,
    repair
):
    category = repair[
        "repaired_category"
    ]

    visual_entities = repair[
        "visual_entities"
    ]

    if scene_num == 1:
        return (
            "AUTHENTIC_ARCHIVAL_CASE_INSERT"
        )

    if scene_num == 2:
        return (
            "CASE_SPECIFIC_LOCATION"
        )

    if category in {
        "EVIDENCE",
        "DOCUMENT",
    }:
        return (
            "FACTUAL_EVIDENCE"
        )

    if visual_entities:
        return (
            "CASE_SPECIFIC_VISUAL"
        )

    if (
        category == "FACE"
        and repair[
            "identity_mode"
        ]
        == "ANONYMOUS_ILLUSTRATIVE_HUMAN"
    ):
        return (
            "ILLUSTRATIVE_REENACTMENT"
        )

    return (
        "ILLUSTRATIVE_BROLL"
    )


def trace_context(
    text,
    term,
    radius=600
):
    index = text.find(
        term
    )

    if index < 0:
        return ""

    start = max(
        0,
        index - radius
    )

    end = min(
        len(text),
        index
        + len(term)
        + radius
    )

    return text[
        start:end
    ]


def classify_trace(
    path,
    context
):
    low = normalize(
        context
    )

    url_present = (
        "http://" in context.lower()
        or "https://" in context.lower()
    )

    source_markers = any(
        marker in low
        for marker in {
            "license",
            "licence",
            "attribution",
            "credit",
            "source url",
            "source_url",
            "provider",
            "author",
            "creator",
        }
    )

    shadow_like = any(
        marker in path.name.lower()
        for marker in {
            "shadow",
            "override",
            "vi500",
            "vi550",
        }
    )

    if (
        url_present
        and source_markers
        and not shadow_like
    ):
        return (
            "SOURCE_METADATA_TRACE"
        )

    return "TRACE_ONLY"


def scan_local_traces(
    current_media
):
    targets = {}

    for item in current_media:
        digest = str(
            item.get("sha256")
            or ""
        )

        path_value = item.get(
            "path"
        )

        if not digest:
            continue

        basename = (
            Path(
                path_value
            ).name
            if path_value
            else ""
        )

        targets[
            item["scene"]
        ] = {
            "sha256":
                digest,

            "basename":
                basename,
        }

    results = {
        scene: []
        for scene in targets
    }

    roots = [
        BASE / "credits",
        BASE / "manifests",
        BASE / "logs/producao",
        BASE / "temp",
    ]

    scanned = 0

    for root in roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if scanned >= MAX_TRACE_FILES:
                break

            if not path.is_file():
                continue

            if (
                path.suffix.lower()
                not in TEXT_EXTENSIONS
            ):
                continue

            try:
                size = (
                    path.stat()
                    .st_size
                )

            except Exception:
                continue

            if (
                size <= 0
                or size
                > MAX_TRACE_FILE
            ):
                continue

            scanned += 1

            try:
                text = path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )

            except Exception:
                continue

            for scene, target in (
                targets.items()
            ):
                matched_term = None

                digest = target[
                    "sha256"
                ]

                basename = target[
                    "basename"
                ]

                if (
                    digest
                    and digest in text
                ):
                    matched_term = digest

                elif (
                    basename
                    and basename in text
                ):
                    matched_term = basename

                if not matched_term:
                    continue

                context = trace_context(
                    text,
                    matched_term
                )

                trace_class = (
                    classify_trace(
                        path,
                        context
                    )
                )

                results[
                    scene
                ].append({
                    "file":
                        str(path),

                    "match":
                        (
                            "SHA256"
                            if matched_term
                            == digest
                            else "BASENAME"
                        ),

                    "class":
                        trace_class,

                    "url_present":
                        (
                            "http://"
                            in context.lower()
                            or
                            "https://"
                            in context.lower()
                        ),

                    "context_preview":
                        re.sub(
                            r"\s+",
                            " ",
                            context
                        )[:500],
                })

    for scene in results:
        unique = {}

        for item in results[
            scene
        ]:
            key = (
                item["file"],
                item["match"],
            )

            unique[key] = item

        results[scene] = list(
            unique.values()
        )[:15]

    return results, scanned


def trace_status(
    old_status,
    traces
):
    if (
        old_status
        == "EXACT_EXTERNAL_PROVENANCE"
    ):
        return old_status

    source_candidates = [
        item
        for item in traces
        if item[
            "class"
        ]
        == "SOURCE_METADATA_TRACE"
    ]

    if source_candidates:
        return (
            "SOURCE_TRACE_CANDIDATE"
        )

    if traces:
        return (
            "TRACE_ONLY"
        )

    return (
        "UNVERIFIED_PROVENANCE"
    )


def duplicate_hashes(
    current_media
):
    groups = {}

    for item in current_media:
        digest = item.get(
            "sha256"
        )

        if not digest:
            continue

        groups.setdefault(
            digest,
            []
        ).append(
            item["scene"]
        )

    return {
        digest:
            scenes
        for digest, scenes
        in groups.items()
        if len(scenes) > 1
    }


def build_priority(
    scene,
    epistemic,
    provenance,
    repair,
    vi420
):
    # Scene 2 has proven provenance.
    if scene == 2:
        return (
            0,
            "KEEP_CURRENT_VERIFIED"
        )

    # Scene 9 already has a verified,
    # downloaded, licensed shadow candidate.
    if (
        scene == 9
        and vi420.get(
            "scene9",
            {}
        ).get(
            "decision"
        )
        == "READY_FOR_SHADOW_OBJECT_AB"
    ):
        return (
            0,
            "VERIFIED_SHADOW_REPLACEMENT_READY"
        )

    # Search exhaustion concerns relevance,
    # not licensing/provenance.
    if scene == 7:
        return (
            80,
            "KEEP_VISUAL_PROVENANCE_REQUIRED"
        )

    # Scene 1 has verified archival insert,
    # but its base image remains unverified.
    if scene == 1:
        if provenance == (
            "EXACT_EXTERNAL_PROVENANCE"
        ):
            return (
                0,
                "HYBRID_INSERT_BASE_VERIFIED"
            )

        return (
            70,
            "HYBRID_INSERT_BASE_PROVENANCE_PENDING"
        )

    if epistemic == (
        "FACTUAL_EVIDENCE"
    ):
        if provenance == (
            "EXACT_EXTERNAL_PROVENANCE"
        ):
            return (
                0,
                "FACTUAL_MEDIA_VERIFIED"
            )

        return (
            95,
            "FACTUAL_PROVENANCE_OR_REPLACEMENT_REQUIRED"
        )

    if repair[
        "identity_mode"
    ] == (
        "ANONYMOUS_ILLUSTRATIVE_HUMAN"
    ):
        if provenance == (
            "EXACT_EXTERNAL_PROVENANCE"
        ):
            return (
                0,
                "ANONYMOUS_HUMAN_VERIFIED"
            )

        return (
            55,
            "LICENSED_ANONYMOUS_HUMAN_REQUIRED"
        )

    if repair[
        "repair_applied"
    ]:
        if provenance == (
            "EXACT_EXTERNAL_PROVENANCE"
        ):
            return (
                0,
                "ROLE_REPAIRED_MEDIA_VERIFIED"
            )

        return (
            60,
            "ROLE_REPAIRED_PROVENANCE_REQUIRED"
        )

    if provenance == (
        "EXACT_EXTERNAL_PROVENANCE"
    ):
        return (
            0,
            "KEEP_CURRENT_VERIFIED"
        )

    if provenance == (
        "SOURCE_TRACE_CANDIDATE"
    ):
        return (
            30,
            "VERIFY_LOCAL_SOURCE_TRACE"
        )

    if provenance == (
        "TRACE_ONLY"
    ):
        return (
            40,
            "PROVENANCE_TRACE_RECONSTRUCTION"
        )

    return (
        45,
        "LICENSED_ILLUSTRATIVE_REPLACEMENT_OR_PROVENANCE"
    )


def find_vi500_shadow(
    vi500
):
    value = (
        vi500.get(
            "shadow_plan",
            {}
        ).get(
            "path"
        )
    )

    if not value:
        return None

    path = Path(
        value
    )

    return (
        path
        if path.exists()
        else None
    )


def build_shadow(
    vi500,
    payload
):
    source = find_vi500_shadow(
        vi500
    )

    if not source:
        return {
            "written":
                False,

            "reason":
                "vi500_shadow_missing",
        }

    before = sha256(
        source
    )

    data = json.loads(
        source.read_text(
            encoding="utf-8"
        )
    )

    if isinstance(
        data,
        dict
    ):
        shadow = copy.deepcopy(
            data
        )

    else:
        shadow = {
            "source_plan":
                data
        }

    shadow[
        "vi550_shadow"
    ] = payload

    SHADOW.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    SHADOW.write_text(
        json.dumps(
            shadow,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return {
        "written":
            True,

        "source":
            str(source),

        "source_sha256":
            before,

        "source_preserved":
            sha256(source)
            == before,

        "path":
            str(SHADOW),
    }


def evaluate():
    vi330 = load_gate(
        VI330
    )

    vi420 = load_gate(
        VI420,
        required=True
    )

    vi500 = load_gate(
        VI500,
        required=True
    )

    short_id = str(
        vi500.get(
            "short_id"
        )
        or "2026-09-01_1433"
    )

    scenes = load_scene_map(
        short_id
    )

    current500 = by_scene(
        vi500.get(
            "current_media"
        )
        or []
    )

    known_entities = (
        vi500.get(
            "known_entities"
        )
        or []
    )

    repairs = {}

    for scene in range(
        1,
        13
    ):
        old = current500.get(
            scene,
            {}
        )

        repairs[
            scene
        ] = repair_scene_role(
            scene,
            old.get(
                "category"
            ),
            scenes.get(
                scene,
                {}
            ),
            known_entities
        )

    current_media = []

    for scene in range(
        1,
        13
    ):
        old = current500.get(
            scene,
            {}
        )

        current_media.append({
            "scene":
                scene,

            "path":
                old.get(
                    "path"
                ),

            "sha256":
                old.get(
                    "sha256"
                ),

            "category":
                old.get(
                    "category"
                ),

            "old_provenance":
                old.get(
                    "provenance_status"
                )
                or
                "UNVERIFIED_PROVENANCE",
        })

    traces, trace_files_scanned = (
        scan_local_traces(
            current_media
        )
    )

    duplicates = (
        duplicate_hashes(
            current_media
        )
    )

    decisions = []

    next_queue = []

    role_repairs = []

    for scene in range(
        1,
        13
    ):
        repair = repairs[
            scene
        ]

        old = current500.get(
            scene,
            {}
        )

        old_provenance = (
            old.get(
                "provenance_status"
            )
            or
            "UNVERIFIED_PROVENANCE"
        )

        provenance = trace_status(
            old_provenance,
            traces.get(
                scene,
                []
            )
        )

        epistemic = epistemic_mode(
            scene,
            repair
        )

        priority, action = (
            build_priority(
                scene,
                epistemic,
                provenance,
                repair,
                vi420
            )
        )

        if repair[
            "repair_applied"
        ]:
            role_repairs.append(
                scene
            )

        item = {
            "scene":
                scene,

            "old_category":
                repair[
                    "old_category"
                ],

            "repaired_category":
                repair[
                    "repaired_category"
                ],

            "role":
                repair[
                    "role"
                ],

            "role_repaired":
                repair[
                    "repair_applied"
                ],

            "repair_reason":
                repair[
                    "repair_reason"
                ],

            "epistemic_mode":
                epistemic,

            "identity_mode":
                repair[
                    "identity_mode"
                ],

            "identity_search_allowed":
                repair[
                    "identity_search_allowed"
                ],

            "identity_attribution_allowed":
                repair[
                    "identity_attribution_allowed"
                ],

            "provenance":
                provenance,

            "trace_count":
                len(
                    traces.get(
                        scene,
                        []
                    )
                ),

            "priority":
                priority,

            "action":
                action,
        }

        decisions.append(
            item
        )

        if priority > 0:
            next_queue.append({
                **item,

                "traces":
                    traces.get(
                        scene,
                        []
                    )[:5],
            })

    next_queue.sort(
        key=lambda x: (
            x["priority"],
            -x["scene"],
        ),
        reverse=True
    )

    scene1_candidate = (
        vi330.get(
            "candidate"
        )
        or {}
    )

    scene9_candidate = (
        vi420.get(
            "scene9",
            {}
        ).get(
            "candidate"
        )
        or {}
    )

    payload = {
        "version":
            VERSION,

        "role_repairs":
            {
                str(scene):
                    repairs[scene]
                for scene in role_repairs
            },

        "epistemic_plan":
            decisions,

        "scene_1": {
            "strategy":
                "HYBRID_ARCHIVAL_INSERT_ONLY",

            "candidate":
                scene1_candidate,

            "base_provenance_pending":
                (
                    next(
                        x
                        for x in decisions
                        if x[
                            "scene"
                        ] == 1
                    )[
                        "priority"
                    ]
                    > 0
                ),

            "renderer_activation":
                False,
        },

        "scene_9": {
            "strategy":
                "VERIFIED_SHADOW_REPLACEMENT_CANDIDATE",

            "candidate":
                scene9_candidate,

            "renderer_activation":
                False,
        },

        "production_media_mutated":
            False,

        "production_plan_mutated":
            False,

        "automatic_replace":
            False,

        "ffmpeg":
            False,

        "video_generated":
            False,
    }

    shadow = build_shadow(
        vi500,
        payload
    )


    action_counts = Counter(
        x["action"]
        for x in decisions
    )

    epistemic_counts = Counter(
        x["epistemic_mode"]
        for x in decisions
    )

    provenance_counts = Counter(
        x["provenance"]
        for x in decisions
    )

    anonymous_human = [
        x["scene"]
        for x in decisions
        if x[
            "identity_mode"
        ]
        == "ANONYMOUS_ILLUSTRATIVE_HUMAN"
    ]

    factual_pending = [
        x["scene"]
        for x in decisions
        if (
            x[
                "epistemic_mode"
            ]
            == "FACTUAL_EVIDENCE"
            and x["priority"] > 0
        )
    ]

    blockers = []

    if not shadow.get(
        "written"
    ):
        blockers.append(
            "vi550_shadow_not_written"
        )

    warnings = []

    if role_repairs:
        warnings.append(
            "category_role_repairs_applied_shadow_only"
        )

    if anonymous_human:
        warnings.append(
            "anonymous_human_scenes_require_no_identity_attribution"
        )

    if factual_pending:
        warnings.append(
            "factual_media_provenance_pending"
        )

    if duplicates:
        warnings.append(
            "duplicate_production_media_detected"
        )

    report = {
        "version":
            VERSION,

        "status":
            (
                "VI550_ROLE_PROVENANCE_REPAIR_CERTIFIED"
                if not blockers
                else "HOLD"
            ),

        "short_id":
            short_id,

        "role_repaired_scenes":
            role_repairs,

        "anonymous_human_scenes":
            anonymous_human,

        "factual_provenance_pending_scenes":
            factual_pending,

        "trace_files_scanned":
            trace_files_scanned,

        "duplicate_production_hashes":
            duplicates,

        "provenance_counts":
            dict(
                provenance_counts
            ),

        "epistemic_counts":
            dict(
                epistemic_counts
            ),

        "action_counts":
            dict(
                action_counts
            ),

        "decisions":
            decisions,

        "local_traces":
            {
                str(scene):
                    traces[
                        scene
                    ]
                for scene in sorted(
                    traces
                )
                if traces[
                    scene
                ]
            },

        "next_queue":
            next_queue,

        "shadow_plan":
            shadow,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "network_executed":
            False,

        "download_executed":
            False,

        "production_media_mutated":
            False,

        "production_plan_mutated":
            False,

        "automatic_replace":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "source_recovery":
            "SHADOW_ONLY",
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUT.write_text(
        json.dumps(
            {"gate": report},
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return report


if __name__ == "__main__":
    r = evaluate()

    print()
    print(
        "=============================================="
    )
    print(
        " VI550 ROLE + PROVENANCE REPAIR"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "ROLE REPAIRS:",
        r[
            "role_repaired_scenes"
        ]
    )

    print(
        "ANONYMOUS HUMAN:",
        r[
            "anonymous_human_scenes"
        ]
    )

    print(
        "FACTUAL PENDING:",
        r[
            "factual_provenance_pending_scenes"
        ]
    )

    print(
        "TRACE FILES SCANNED:",
        r[
            "trace_files_scanned"
        ]
    )

    print(
        "PROVENANCE:",
        r[
            "provenance_counts"
        ]
    )

    print(
        "EPISTEMIC:",
        r[
            "epistemic_counts"
        ]
    )

    print(
        "ACTIONS:",
        r[
            "action_counts"
        ]
    )

    print(
        "DUPLICATES:",
        r[
            "duplicate_production_hashes"
        ]
    )

    print()
    print(
        "===== ROLE / IDENTITY REPAIR ====="
    )

    for x in r[
        "decisions"
    ]:
        print(
            "SCENE",
            x["scene"],
            "|",
            x[
                "old_category"
            ],
            "->",
            x[
                "repaired_category"
            ],
            "| role=",
            x["role"],
            "| epistemic=",
            x[
                "epistemic_mode"
            ],
            "| identity=",
            x[
                "identity_mode"
            ],
        )

        if x[
            "role_repaired"
        ]:
            print(
                "   REPAIR:",
                x[
                    "repair_reason"
                ]
            )

    print()
    print(
        "===== PROVENANCE + ACTION ====="
    )

    for x in r[
        "decisions"
    ]:
        print(
            "SCENE",
            x["scene"],
            "| provenance=",
            x[
                "provenance"
            ],
            "| traces=",
            x[
                "trace_count"
            ],
            "| priority=",
            x[
                "priority"
            ],
            "|",
            x["action"],
        )

    print()
    print(
        "===== NEXT QUEUE ====="
    )

    for x in r[
        "next_queue"
    ]:
        print(
            "SCENE",
            x["scene"],
            "| priority=",
            x[
                "priority"
            ],
            "| role=",
            x["role"],
            "| epistemic=",
            x[
                "epistemic_mode"
            ],
            "|",
            x["action"],
        )

    print()
    print(
        "SHADOW PLAN:",
        r["shadow_plan"]
    )

    print(
        "BLOCKERS:",
        r["blockers"]
    )

    print(
        "WARNINGS:",
        r["warnings"]
    )

    print()
    print(
        "NETWORK EXECUTED:",
        r["network_executed"]
    )

    print(
        "DOWNLOAD EXECUTED:",
        r["download_executed"]
    )

    print(
        "PRODUCTION MEDIA MUTATED:",
        r[
            "production_media_mutated"
        ]
    )

    print(
        "PRODUCTION PLAN MUTATED:",
        r[
            "production_plan_mutated"
        ]
    )

    print(
        "AUTOMATIC REPLACE:",
        r[
            "automatic_replace"
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
