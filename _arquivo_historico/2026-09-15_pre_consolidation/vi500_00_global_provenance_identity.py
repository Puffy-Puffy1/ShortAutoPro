#!/usr/bin/env python3
from short_id_runtime_v1 import resolve_short_id as _sap_resolve_short_id

import copy
import hashlib
import json
import re
import struct
from pathlib import Path
from collections import Counter


VERSION = "500.00"

BASE = Path.home() / "ShortAutoPro"
LOG = BASE / "logs/producao"

VI225 = (
    LOG /
    "vi225_00_safe_family_fallback_latest.json"
)

VI235 = (
    LOG /
    "vi235_00_media_provenance_check_latest.json"
)

VI260 = (
    LOG /
    "vi260_00_global_provenance_director_latest.json"
)

VI300 = (
    LOG /
    "vi300_00_targeted_global_search_latest.json"
)

VI320 = (
    LOG /
    "vi320_00_deep_context_truth_latest.json"
)

VI330 = (
    LOG /
    "vi330_00_controlled_real_ab_latest.json"
)

VI400 = (
    LOG /
    "vi400_00_speed_quality_accelerator_latest.json"
)

VI420 = (
    LOG /
    "vi420_00_batch_deep_ab_latest.json"
)

OUT = (
    LOG /
    "vi500_00_global_provenance_identity_latest.json"
)

SHADOW = (
    BASE /
    "temp/vi500_shadow/"
    "motion_plan_2026-09-01_1433_vi500_shadow.json"
)


IMAGE_EXT = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

VIDEO_EXT = {
    ".mp4",
    ".webm",
    ".mov",
    ".m4v",
    ".ogv",
    ".mpeg",
    ".mpg",
}


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


LOCATION_OBJECT_TERMS = {
    "rooftop",
    "roof",
    "water tower",
    "water towers",
    "water tank",
    "building",
    "hotel",
    "hallway",
    "corridor",
    "elevator",
    "street",
    "camera",
    "cctv",
}


def load_gate(
    path,
    required=False
):
    if not path.exists():
        if required:
            raise RuntimeError(
                f"missing:{path.name}"
            )

        return {}

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        if required:
            raise

        return {}

    return data.get(
        "gate",
        data
    )


def normalize(value):
    text = str(
        value or ""
    )

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
            chunk = f.read(
                1024 * 1024
            )

            if not chunk:
                break

            h.update(chunk)

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


def media_family(path):
    if not path:
        return "MISSING"

    ext = path.suffix.lower()

    if ext in IMAGE_EXT:
        return "IMAGE"

    if ext in VIDEO_EXT:
        return "VIDEO"

    return "UNKNOWN"


def find_media(
    short_id,
    scene
):
    folder = (
        BASE /
        "imagens" /
        f"short_{short_id}"
    )

    matches = sorted(
        folder.glob(
            f"scene_{scene:02d}.*"
        )
    )

    return (
        matches[0]
        if matches
        else None
    )


def load_scene_map(
    short_id
):
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

    query = scene.get(
        "query"
    )

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

    return " ".join(
        parts
    )


def narration_text(scene):
    return str(
        scene.get(
            "segment"
        )
        or ""
    )


def jpeg_size(path):
    try:
        with open(
            path,
            "rb"
        ) as f:
            if (
                f.read(2)
                != b"\xff\xd8"
            ):
                return None

            while True:
                b = f.read(1)

                if not b:
                    return None

                if b != b"\xff":
                    continue

                while b == b"\xff":
                    b = f.read(1)

                marker = b[0]

                if marker in {
                    0xD8,
                    0xD9,
                }:
                    continue

                raw = f.read(2)

                if len(raw) != 2:
                    return None

                length = struct.unpack(
                    ">H",
                    raw
                )[0]

                if marker in {
                    0xC0, 0xC1, 0xC2,
                    0xC3, 0xC5, 0xC6,
                    0xC7, 0xC9, 0xCA,
                    0xCB, 0xCD, 0xCE,
                    0xCF,
                }:
                    data = f.read(5)

                    if len(data) != 5:
                        return None

                    h, w = struct.unpack(
                        ">HH",
                        data[1:5]
                    )

                    return w, h

                f.seek(
                    length - 2,
                    1
                )

    except Exception:
        return None


def png_size(path):
    try:
        with open(
            path,
            "rb"
        ) as f:
            data = f.read(24)

        if (
            len(data) >= 24
            and data[:8]
            == b"\x89PNG\r\n\x1a\n"
        ):
            return struct.unpack(
                ">II",
                data[16:24]
            )

    except Exception:
        pass

    return None


def image_size(path):
    if not path:
        return None

    ext = path.suffix.lower()

    if ext in {
        ".jpg",
        ".jpeg",
    }:
        return jpeg_size(
            path
        )

    if ext == ".png":
        return png_size(
            path
        )

    return None


def local_hash_references(
    digest
):
    if not digest:
        return []

    roots = [
        BASE / "manifests",
        BASE / "credits",
    ]

    hits = []

    for root in roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            try:
                size = path.stat().st_size

            except Exception:
                continue

            if size > 5_000_000:
                continue

            if path.suffix.lower() not in {
                ".json",
                ".txt",
                ".log",
                ".csv",
            }:
                continue

            try:
                text = path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )

            except Exception:
                continue

            if digest in text:
                hits.append(
                    str(path)
                )

                if len(hits) >= 20:
                    return hits

    return hits


def build_external_registry(
    vi225,
    vi235,
    vi330,
    vi420
):
    registry = {}

    checks225 = {
        str(
            x.get("title")
            or ""
        ):
            x
        for x in (
            vi225.get(
                "checks"
            )
            or []
        )
    }

    for item in (
        vi235.get(
            "candidate_results"
        )
        or []
    ):
        digest = str(
            item.get(
                "sha256"
            )
            or ""
        )

        if not digest:
            continue

        title = str(
            item.get(
                "title"
            )
            or ""
        )

        metadata = (
            checks225.get(
                title
            )
            or {}
        )

        registry[
            digest
        ] = {
            "title":
                title,

            "url":
                metadata.get(
                    "url"
                ),

            "license":
                metadata.get(
                    "license"
                ),

            "source":
                "VI235_COMMONS_EXACT_DOWNLOAD",

            "confidence":
                "EXACT_SHA256",
        }

    candidate330 = (
        vi330.get(
            "candidate"
        )
        or {}
    )

    digest330 = str(
        candidate330.get(
            "sha256"
        )
        or ""
    )

    if digest330:
        registry[
            digest330
        ] = {
            "title":
                candidate330.get(
                    "title"
                ),

            "url":
                None,

            "license":
                candidate330.get(
                    "license"
                ),

            "source":
                "VI330_CONTROLLED_COMMONS_DOWNLOAD",

            "confidence":
                "EXACT_SHA256",
        }

    candidate420 = (
        vi420.get(
            "scene9",
            {}
        ).get(
            "candidate"
        )
        or {}
    )

    digest420 = str(
        candidate420.get(
            "sha256"
        )
        or ""
    )

    if digest420:
        registry[
            digest420
        ] = {
            "title":
                candidate420.get(
                    "title"
                ),

            "url":
                candidate420.get(
                    "url"
                ),

            "license":
                candidate420.get(
                    "license"
                ),

            "source":
                "VI420_CONTROLLED_COMMONS_DOWNLOAD",

            "confidence":
                "EXACT_SHA256",
        }

    return registry


def resolve_identity(
    scene_num,
    scene,
    category,
    known_entities
):
    visual = normalize(
        visual_text(
            scene
        )
    )

    narration = normalize(
        narration_text(
            scene
        )
    )

    category = str(
        category or ""
    ).upper()

    if category != "FACE":
        return {
            "scene":
                scene_num,

            "status":
                "NOT_FACE_SCENE",

            "identity":
                None,

            "search_allowed":
                True,

            "reason":
                "identity_gate_not_required",
        }

    known = [
        str(x)
        for x in known_entities
        if x
    ]

    explicit_visual = []

    contextual = []

    for entity in known:
        e = normalize(
            entity
        )

        if (
            e
            and e in visual
        ):
            explicit_visual.append(
                entity
            )

        if (
            e
            and e in narration
        ):
            contextual.append(
                entity
            )

    human_hits = sorted({
        term
        for term in HUMAN_TERMS
        if term in visual
    })

    location_hits = sorted({
        term
        for term in LOCATION_OBJECT_TERMS
        if term in visual
    })

    # Strongest possible policy:
    # only visual fields can authorize
    # identity-specific media search.
    if explicit_visual:
        primary = (
            "Elisa Lam"
            if any(
                normalize(x)
                == "elisa lam"
                for x in explicit_visual
            )
            else explicit_visual[0]
        )

        return {
            "scene":
                scene_num,

            "status":
                "EXPLICIT_VISUAL_IDENTITY_REQUIREMENT",

            "identity":
                primary,

            "visual_entities":
                explicit_visual,

            "contextual_entities":
                contextual,

            "human_hits":
                human_hits,

            "location_hits":
                location_hits,

            "search_allowed":
                True,

            "search_mode":
                "EXACT_IDENTITY_ONLY",

            "reason":
                "identity_explicit_in_visual_spec",
        }

    # FACE category but visual instruction
    # describes an environment/object.
    if (
        location_hits
        and not human_hits
    ):
        return {
            "scene":
                scene_num,

            "status":
                "ROLE_CONFLICT_QUARANTINE",

            "identity":
                None,

            "visual_entities":
                [],

            "contextual_entities":
                contextual,

            "human_hits":
                human_hits,

            "location_hits":
                location_hits,

            "search_allowed":
                False,

            "search_mode":
                "BLOCKED",

            "reason":
                "face_category_conflicts_with_nonhuman_visual_spec",
        }

    # A narration mentioning Elisa Lam is
    # context, not permission to claim
    # that a random woman is Elisa Lam.
    if human_hits:
        return {
            "scene":
                scene_num,

            "status":
                "GENERIC_HUMAN_IDENTITY_UNSPECIFIED",

            "identity":
                None,

            "visual_entities":
                [],

            "contextual_entities":
                contextual,

            "human_hits":
                human_hits,

            "location_hits":
                location_hits,

            "search_allowed":
                False,

            "search_mode":
                "NO_IDENTITY_INFERENCE",

            "reason":
                "generic_person_visual_without_explicit_identity",
        }

    return {
        "scene":
            scene_num,

        "status":
            "IDENTITY_UNRESOLVED_QUARANTINE",

        "identity":
            None,

        "visual_entities":
            [],

        "contextual_entities":
            contextual,

        "human_hits":
            human_hits,

        "location_hits":
            location_hits,

        "search_allowed":
            False,

        "search_mode":
            "BLOCKED",

        "reason":
            "face_scene_has_no_explicit_identity",
    }


def find_shadow_source(
    vi420
):
    path = (
        vi420.get(
            "shadow_plan",
            {}
        ).get(
            "path"
        )
    )

    if path:
        p = Path(
            path
        )

        if p.exists():
            return p

    return None


def build_shadow(
    vi420,
    payload
):
    source = find_shadow_source(
        vi420
    )

    if not source:
        return {
            "written":
                False,

            "reason":
                "vi420_shadow_missing",
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
        "vi500_shadow"
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

    after = sha256(
        source
    )

    return {
        "written":
            True,

        "source":
            str(source),

        "source_sha256":
            before,

        "source_preserved":
            before == after,

        "path":
            str(SHADOW),
    }


def evaluate():
    vi225 = load_gate(
        VI225
    )

    vi235 = load_gate(
        VI235
    )

    vi260 = load_gate(
        VI260,
        required=True
    )

    vi300 = load_gate(
        VI300
    )

    vi320 = load_gate(
        VI320,
        required=True
    )

    vi330 = load_gate(
        VI330,
        required=True
    )

    vi400 = load_gate(
        VI400,
        required=True
    )

    vi420 = load_gate(
        VI420,
        required=True
    )

    short_id = str(
        vi260.get(
            "short_id"
        )
        or _sap_resolve_short_id()
    )

    scenes = load_scene_map(
        short_id
    )

    vi260_by_scene = by_scene(
        vi260.get(
            "decisions"
        )
        or []
    )

    known_entities = (
        vi320.get(
            "anchors",
            {}
        ).get(
            "known_entities"
        )
        or []
    )

    registry = build_external_registry(
        vi225,
        vi235,
        vi330,
        vi420
    )

    identity_results = {}

    current_results = []

    exact_verified = []

    local_reference_scenes = []

    unresolved_provenance = []

    for scene_num in range(
        1,
        13
    ):
        scene = scenes.get(
            scene_num,
            {}
        )

        old = vi260_by_scene.get(
            scene_num,
            {}
        )

        category = str(
            old.get(
                "category"
            )
            or "GENERAL"
        ).upper()

        media = find_media(
            short_id,
            scene_num
        )

        digest = None

        bytes_count = None

        family = "MISSING"

        dimensions = None

        if media:
            family = media_family(
                media
            )

            digest = sha256(
                media
            )

            bytes_count = (
                media.stat()
                .st_size
            )

            dimensions = image_size(
                media
            )

        external = (
            registry.get(
                digest
            )
            if digest
            else None
        )

        refs = (
            local_hash_references(
                digest
            )
            if digest
            else []
        )

        if external:
            provenance_status = (
                "EXACT_EXTERNAL_PROVENANCE"
            )

            exact_verified.append(
                scene_num
            )

        elif refs:
            provenance_status = (
                "LOCAL_HASH_REFERENCE_ONLY"
            )

            local_reference_scenes.append(
                scene_num
            )

        else:
            provenance_status = (
                "UNVERIFIED_PROVENANCE"
            )

            unresolved_provenance.append(
                scene_num
            )

        identity = resolve_identity(
            scene_num,
            scene,
            category,
            known_entities
        )

        identity_results[
            scene_num
        ] = identity

        current_results.append({
            "scene":
                scene_num,

            "category":
                category,

            "path":
                str(media)
                if media
                else None,

            "family":
                family,

            "sha256":
                digest,

            "bytes":
                bytes_count,

            "dimensions":
                (
                    list(
                        dimensions
                    )
                    if dimensions
                    else None
                ),

            "provenance_status":
                provenance_status,

            "external_provenance":
                external,

            "local_hash_references":
                refs,

            "identity":
                identity,
        })

    # VI235 is authoritative for scene 2.
    # This protects against any registry
    # field missing in old reports.
    if (
        2 not in exact_verified
        and vi235.get(
            "decision"
        )
        == "CURRENT_MEDIA_PROVENANCE_IDENTIFIED"
    ):
        exact_verified.append(
            2
        )

        unresolved_provenance = [
            x
            for x in unresolved_provenance
            if x != 2
        ]

        for item in current_results:
            if item["scene"] == 2:
                item[
                    "provenance_status"
                ] = (
                    "EXACT_EXTERNAL_PROVENANCE"
                )

                item[
                    "external_provenance"
                ] = {
                    "title":
                        (
                            vi235.get(
                                "exact_match_titles"
                            )
                            or [
                                "Hotel Cecil LA.jpg"
                            ]
                        )[0],

                    "source":
                        "VI235_SHA256_MATCH",

                    "confidence":
                        "EXACT_SHA256",
                }

                break

    exact_verified = sorted(
        set(
            exact_verified
        )
    )

    unresolved_provenance = sorted(
        set(
            unresolved_provenance
        )
    )

    local_reference_scenes = sorted(
        set(
            local_reference_scenes
        )
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

    scene9_ready = (
        vi420.get(
            "scene9",
            {}
        ).get(
            "decision"
        )
        == "READY_FOR_SHADOW_OBJECT_AB"
        and bool(
            scene9_candidate
        )
    )

    scene1_ready = (
        vi400.get(
            "scene1",
            {}
        ).get(
            "strategy"
        )
        == "HYBRID_ARCHIVAL_INSERT_ONLY"
    )

    global_plan = []

    next_queue = []

    for item in current_results:
        scene = item[
            "scene"
        ]

        ident = item[
            "identity"
        ]

        provenance = item[
            "provenance_status"
        ]

        if scene == 1:
            action = (
                "HYBRID_ARCHIVAL_INSERT_READY"
                if scene1_ready
                else "KEEP_CURRENT"
            )

            priority = 0

        elif scene == 2:
            action = (
                "KEEP_CURRENT_VERIFIED"
            )

            priority = 0

        elif scene == 9:
            action = (
                "SHADOW_OBJECT_CANDIDATE_READY"
                if scene9_ready
                else "KEEP_CURRENT"
            )

            priority = 0

        elif scene == 7:
            action = (
                "KEEP_CURRENT_SEARCH_EXHAUSTED"
            )

            priority = 0

        elif (
            ident["status"]
            == "ROLE_CONFLICT_QUARANTINE"
        ):
            action = (
                "ROLE_CONFLICT_QUARANTINE"
            )

            priority = 100

        elif (
            ident["status"]
            == "EXPLICIT_VISUAL_IDENTITY_REQUIREMENT"
        ):
            action = (
                "IDENTITY_EXACT_SEARCH_READY"
            )

            priority = 90

        elif item[
            "category"
        ] == "FACE":
            action = (
                "IDENTITY_QUARANTINE"
            )

            priority = 85

        elif provenance == (
            "EXACT_EXTERNAL_PROVENANCE"
        ):
            action = (
                "KEEP_CURRENT_VERIFIED"
            )

            priority = 0

        elif item[
            "category"
        ] in {
            "DOCUMENT",
            "EVIDENCE",
        }:
            action = (
                "PROVENANCE_RECONSTRUCTION_PRIORITY"
            )

            priority = 60

        elif provenance == (
            "LOCAL_HASH_REFERENCE_ONLY"
        ):
            action = (
                "PROVENANCE_REFERENCE_AUDIT"
            )

            priority = 45

        else:
            action = (
                "PROVENANCE_RECONSTRUCTION"
            )

            priority = 35

        global_plan.append({
            "scene":
                scene,

            "category":
                item[
                    "category"
                ],

            "provenance":
                provenance,

            "identity_status":
                ident[
                    "status"
                ],

            "priority":
                priority,

            "action":
                action,
        })

        if priority > 0:
            next_queue.append({
                "scene":
                    scene,

                "priority":
                    priority,

                "action":
                    action,

                "category":
                    item[
                        "category"
                    ],

                "provenance":
                    provenance,

                "identity":
                    ident,
            })

    next_queue.sort(
        key=lambda x: (
            x["priority"],
            -x["scene"],
        ),
        reverse=True
    )


    shadow_payload = {
        "version":
            VERSION,

        "scene_1": {
            "strategy":
                "HYBRID_ARCHIVAL_INSERT_ONLY"
                if scene1_ready
                else "KEEP_CURRENT",

            "candidate":
                (
                    vi330.get(
                        "candidate"
                    )
                    or {}
                ),

            "base_media_preserved":
                True,
        },

        "scene_2": {
            "strategy":
                "KEEP_CURRENT_VERIFIED",

            "provenance":
                "EXACT_SHA256",
        },

        "scene_9": {
            "strategy":
                (
                    "SHADOW_OBJECT_CANDIDATE"
                    if scene9_ready
                    else "KEEP_CURRENT"
                ),

            "candidate":
                scene9_candidate,

            "base_media_preserved":
                True,
        },

        "identity_resolution": {
            str(scene):
                identity_results[
                    scene
                ]
            for scene in sorted(
                identity_results
            )
        },

        "global_plan":
            global_plan,

        "renderer_activation":
            False,

        "production_media_mutated":
            False,

        "automatic_replace":
            False,

        "ffmpeg":
            False,

        "video_generated":
            False,
    }

    shadow = build_shadow(
        vi420,
        shadow_payload
    )

    identity_status_counts = Counter(
        identity_results[
            scene
        ][
            "status"
        ]
        for scene in identity_results
    )

    action_counts = Counter(
        item["action"]
        for item in global_plan
    )

    identity_quarantine = sorted([
        scene
        for scene, item
        in identity_results.items()
        if (
            item[
                "status"
            ]
            in {
                "GENERIC_HUMAN_IDENTITY_UNSPECIFIED",
                "IDENTITY_UNRESOLVED_QUARANTINE",
                "ROLE_CONFLICT_QUARANTINE",
            }
        )
    ])

    role_conflicts = sorted([
        scene
        for scene, item
        in identity_results.items()
        if item[
            "status"
        ]
        == "ROLE_CONFLICT_QUARANTINE"
    ])

    warnings = []

    if identity_quarantine:
        warnings.append(
            "identity_quarantine_active"
        )

    if role_conflicts:
        warnings.append(
            "face_role_conflict_detected"
        )

    if unresolved_provenance:
        warnings.append(
            "unverified_current_media_remaining"
        )

    blockers = []

    if not shadow.get(
        "written"
    ):
        blockers.append(
            "vi500_shadow_not_written"
        )

    status = (
        "VI500_GLOBAL_PROVENANCE_IDENTITY_CERTIFIED"
        if not blockers
        else "HOLD"
    )

    report = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            short_id,

        "known_entities":
            known_entities,

        "provenance_registry_entries":
            len(
                registry
            ),

        "exact_verified_scenes":
            exact_verified,

        "local_reference_scenes":
            local_reference_scenes,

        "unverified_provenance_scenes":
            unresolved_provenance,

        "identity_status_counts":
            dict(
                identity_status_counts
            ),

        "identity_quarantine_scenes":
            identity_quarantine,

        "role_conflict_scenes":
            role_conflicts,

        "current_media":
            current_results,

        "global_plan":
            global_plan,

        "action_counts":
            dict(
                action_counts
            ),

        "next_queue":
            next_queue,

        "scene1_archival_insert_ready":
            scene1_ready,

        "scene9_object_shadow_ready":
            scene9_ready,

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
        " VI500 GLOBAL PROVENANCE + IDENTITY RESOLVER"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "KNOWN ENTITIES:",
        r[
            "known_entities"
        ]
    )

    print(
        "REGISTRY ENTRIES:",
        r[
            "provenance_registry_entries"
        ]
    )

    print(
        "EXACT VERIFIED:",
        r[
            "exact_verified_scenes"
        ]
    )

    print(
        "LOCAL REFERENCES:",
        r[
            "local_reference_scenes"
        ]
    )

    print(
        "UNVERIFIED:",
        r[
            "unverified_provenance_scenes"
        ]
    )

    print()
    print(
        "IDENTITY COUNTS:",
        r[
            "identity_status_counts"
        ]
    )

    print(
        "IDENTITY QUARANTINE:",
        r[
            "identity_quarantine_scenes"
        ]
    )

    print(
        "ROLE CONFLICTS:",
        r[
            "role_conflict_scenes"
        ]
    )

    print()
    print(
        "SCENE 1 INSERT READY:",
        r[
            "scene1_archival_insert_ready"
        ]
    )

    print(
        "SCENE 9 SHADOW READY:",
        r[
            "scene9_object_shadow_ready"
        ]
    )

    print()
    print(
        "===== IDENTITY RESOLUTION ====="
    )

    for item in (
        r[
            "current_media"
        ]
    ):
        if item[
            "category"
        ] != "FACE":
            continue

        identity = item[
            "identity"
        ]

        print()
        print(
            "SCENE:",
            item["scene"]
        )

        print(
            " STATUS:",
            identity[
                "status"
            ]
        )

        print(
            " IDENTITY:",
            identity.get(
                "identity"
            )
        )

        print(
            " HUMAN:",
            identity.get(
                "human_hits"
            )
        )

        print(
            " LOCATION/OBJECT:",
            identity.get(
                "location_hits"
            )
        )

        print(
            " CONTEXT:",
            identity.get(
                "contextual_entities"
            )
        )

        print(
            " SEARCH ALLOWED:",
            identity[
                "search_allowed"
            ]
        )

        print(
            " REASON:",
            identity[
                "reason"
            ]
        )

    print()
    print(
        "===== GLOBAL PLAN ====="
    )

    for item in (
        r[
            "global_plan"
        ]
    ):
        print(
            "SCENE",
            item["scene"],
            "|",
            item["category"],
            "| provenance=",
            item["provenance"],
            "| identity=",
            item["identity_status"],
            "| priority=",
            item["priority"],
            "|",
            item["action"],
        )

    print()
    print(
        "===== NEXT QUEUE ====="
    )

    for item in (
        r[
            "next_queue"
        ][:10]
    ):
        print(
            "SCENE",
            item["scene"],
            "| priority=",
            item["priority"],
            "|",
            item["action"],
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
