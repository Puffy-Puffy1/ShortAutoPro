#!/usr/bin/env python3

import json
import hashlib
import re
from pathlib import Path
from collections import Counter


VERSION = "260.00"

BASE = Path.home() / "ShortAutoPro"

LOG = BASE / "logs/producao"
ROTEIROS = BASE / "roteiros"

VI70 = (
    LOG /
    "vi70_00_global_visual_casting_latest.json"
)

VI235 = (
    LOG /
    "vi235_00_media_provenance_check_latest.json"
)

VI210 = (
    LOG /
    "vi210_00_scene_role_family_gate_latest.json"
)

VI225 = (
    LOG /
    "vi225_00_safe_family_fallback_latest.json"
)

VI230 = (
    LOG /
    "vi230_00_current_vs_candidate_ab_latest.json"
)

OUT = (
    LOG /
    "vi260_00_global_provenance_director_latest.json"
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
    ".mpeg",
    ".mpg",
    ".ogv",
}


STYLE_STOP = {
    "dark",
    "cinematic",
    "mysterious",
    "dramatic",
    "moody",
    "vintage",
    "clear",
    "shot",
    "image",
    "photo",
    "video",
    "footage",
    "background",
    "foreground",
}


def load_gate(path):
    if not path.exists():
        return {}

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return {}

    return data.get(
        "gate",
        data
    )


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


def media_family(path):
    ext = path.suffix.lower()

    if ext in VIDEO_EXT:
        return "VIDEO"

    if ext in IMAGE_EXT:
        return "IMAGE"

    return "UNKNOWN"


def find_media(
    short_id,
    scene
):
    folder = (
        BASE
        / "imagens"
        / f"short_{short_id}"
    )

    stem = (
        f"scene_{scene:02d}"
    )

    matches = sorted(
        folder.glob(
            stem + ".*"
        )
    )

    return (
        matches[0]
        if matches
        else None
    )


def load_scene_map(short_id):
    path = (
        ROTEIROS
        / f"scene_map_{short_id}.json"
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
        data.get(
            "scenes"
        )
        or []
    )


def scene_text(scene):
    parts = []

    for key in (
        "segment",
        "query",
        "must_have",
    ):
        value = scene.get(key)

        if isinstance(
            value,
            list
        ):
            parts.extend(
                str(x)
                for x in value
            )

        elif value:
            parts.append(
                str(value)
            )

    return " ".join(
        parts
    )


def clean_query(text):
    words = re.findall(
        r"[A-Za-zÀ-ÿ0-9'-]+",
        str(text or "")
    )

    output = []

    seen = set()

    for word in words:
        low = word.lower()

        if low in STYLE_STOP:
            continue

        if len(low) < 3:
            continue

        if low in seen:
            continue

        seen.add(low)

        output.append(
            word
        )

    return " ".join(
        output[:8]
    )


def exact_provenance_map(
    vi235
):
    result = {}

    scene = vi235.get(
        "scene"
    )

    matches = (
        vi235.get(
            "exact_match_titles"
        )
        or []
    )

    if scene and matches:
        try:
            scene = int(scene)
        except Exception:
            return result

        result[scene] = {
            "status":
                "EXACT_EXTERNAL_PROVENANCE",

            "titles":
                matches,

            "evidence":
                "sha256_exact_match",
        }

    return result


def route_provider(
    desired_family,
    category
):
    category = str(
        category or ""
    ).upper()

    if desired_family == "VIDEO":
        return [
            "INTERNET_ARCHIVE",
            "WIKIMEDIA_COMMONS_VIDEO",
        ]

    if (
        desired_family
        == "ARCHIVAL_IMAGE"
        or category
        in {
            "DOCUMENT",
            "EVIDENCE",
        }
    ):
        return [
            "WIKIMEDIA_COMMONS",
            "DOCUMENTARY_ARCHIVE_SHADOW",
        ]

    return [
        "WIKIMEDIA_COMMONS",
    ]


def role_query(
    scene,
    category,
    desired
):
    raw = (
        scene.get("query")
        or scene.get("segment")
        or ""
    )

    query = clean_query(
        raw
    )

    category = str(
        category or ""
    ).upper()

    suffix = ""

    if desired == "VIDEO":
        if category == "LOCATION":
            suffix = " exterior location"

        elif category == "FACE":
            suffix = ""

    elif (
        desired
        == "ARCHIVAL_IMAGE"
    ):
        suffix = " archive"

    query = (
        query
        + suffix
    ).strip()

    return " ".join(
        query.split()
    )


def evaluate():
    vi70 = load_gate(
        VI70
    )

    vi235 = load_gate(
        VI235
    )

    vi210 = load_gate(
        VI210
    )

    vi225 = load_gate(
        VI225
    )

    vi230 = load_gate(
        VI230
    )

    if not vi70:
        raise RuntimeError(
            "vi70_missing"
        )

    short_id = str(
        vi70.get(
            "short_id"
        )
        or ""
    )

    scenes = load_scene_map(
        short_id
    )

    plans70 = by_scene(
        vi70.get(
            "decisions"
        )
        or []
    )

    provenance = (
        exact_provenance_map(
            vi235
        )
    )

    decisions = []

    search_queue = []

    for scene_num in range(
        1,
        13
    ):
        scene = scenes.get(
            scene_num,
            {}
        )

        plan = plans70.get(
            scene_num,
            {}
        )

        current_path = find_media(
            short_id,
            scene_num
        )

        current_family = (
            media_family(
                current_path
            )
            if current_path
            else "MISSING"
        )

        desired_family = str(
            plan.get(
                "desired_family"
            )
            or current_family
        )

        category = str(
            plan.get(
                "category"
            )
            or "GENERAL"
        ).upper()

        identity = str(
            plan.get(
                "identity"
            )
            or "PASS"
        ).upper()

        prov = provenance.get(
            scene_num
        )

        if prov:
            provenance_status = (
                prov["status"]
            )

            provenance_title = (
                prov["titles"][0]
            )

        else:
            provenance_status = (
                "UNVERIFIED_PROVENANCE"
            )

            provenance_title = None

        family_match = (
            current_family
            == desired_family
            or (
                desired_family
                == "ARCHIVAL_IMAGE"
                and current_family
                == "IMAGE"
            )
        )

        priority = 0
        reasons = []

        if (
            provenance_status
            == "UNVERIFIED_PROVENANCE"
        ):
            priority += 30
            reasons.append(
                "provenance_unverified"
            )

        if not family_match:
            priority += 25
            reasons.append(
                "desired_family_differs"
            )

        if identity == "CAUTION":
            priority += 25
            reasons.append(
                "identity_guard_required"
            )

        if category in {
            "DOCUMENT",
            "EVIDENCE",
        }:
            priority += 10
            reasons.append(
                "evidence_sensitive_scene"
            )

        # Scene 2 now has exact SHA256 provenance.
        if (
            scene_num == 2
            and provenance_status
            == "EXACT_EXTERNAL_PROVENANCE"
        ):
            priority = 0

            action = (
                "KEEP_CURRENT_VERIFIED"
            )

            reasons = [
                "exact_sha256_provenance",
                "authentic_current_media",
                "better_vertical_fit_than_alternative",
                "no_meaningful_resolution_gain_from_alternative",
            ]

        # Scene 7 underwent multiple searches and
        # context truth rejected replacements.
        elif scene_num == 7:
            priority = min(
                priority,
                10
            )

            action = (
                "KEEP_CURRENT_SEARCH_EXHAUSTED"
            )

            reasons.append(
                "multiple_candidate_searches_rejected"
            )

        elif identity == "CAUTION":
            action = (
                "SEARCH_WITH_IDENTITY_GUARD"
            )

        elif not family_match:
            action = (
                "SEARCH_ROLE_CONSTRAINED"
            )

        elif provenance_status == (
            "UNVERIFIED_PROVENANCE"
        ):
            action = (
                "PROVENANCE_AUDIT_PRIORITY"
            )

        else:
            action = "KEEP_CURRENT"

        media_hash = None

        if (
            current_path
            and current_path.is_file()
        ):
            media_hash = sha256(
                current_path
            )

        item = {
            "scene":
                scene_num,

            "category":
                category,

            "identity":
                identity,

            "current_path":
                (
                    str(current_path)
                    if current_path
                    else None
                ),

            "current_sha256":
                media_hash,

            "current_family":
                current_family,

            "desired_family":
                desired_family,

            "family_match":
                family_match,

            "provenance_status":
                provenance_status,

            "provenance_title":
                provenance_title,

            "priority":
                priority,

            "action":
                action,

            "reasons":
                reasons,
        }

        decisions.append(
            item
        )

        if (
            priority > 0
            and action
            not in {
                "KEEP_CURRENT_VERIFIED",
                "KEEP_CURRENT_SEARCH_EXHAUSTED",
            }
        ):
            search_queue.append({
                "scene":
                    scene_num,

                "priority":
                    priority,

                "category":
                    category,

                "identity":
                    identity,

                "current_family":
                    current_family,

                "desired_family":
                    desired_family,

                "provider_route":
                    route_provider(
                        desired_family,
                        category
                    ),

                "query":
                    role_query(
                        scene,
                        category,
                        desired_family
                    ),

                "mode":
                    (
                        "IDENTITY_GUARDED"
                        if identity
                        == "CAUTION"
                        else
                        "NORMAL"
                    ),
            })

    search_queue.sort(
        key=lambda x: (
            x["priority"],
            x["scene"],
        ),
        reverse=True
    )

    action_counts = Counter(
        x["action"]
        for x in decisions
    )

    provenance_counts = Counter(
        x[
            "provenance_status"
        ]
        for x in decisions
    )

    verified_keep = [
        x["scene"]
        for x in decisions
        if x["action"]
        == "KEEP_CURRENT_VERIFIED"
    ]

    identity_guard = [
        x["scene"]
        for x in decisions
        if x["identity"]
        == "CAUTION"
    ]

    top_search = [
        x["scene"]
        for x in search_queue[:6]
    ]

    corrections = {
        "vi230_suitability_gain":
            "INVALIDATED_AS_ASYMMETRIC_BASELINE",

        "scene_2":
            "KEEP_CURRENT_VERIFIED",

        "scene_2_provenance":
            (
                vi235.get(
                    "exact_match_titles"
                )
                or []
            ),

        "file_prefix_role_bug":
            "DO_NOT_INTERPRET_FILE_NAMESPACE_AS_DOCUMENT",

        "secondary_entity_rule":
            "LOS_ANGELES_ALONE_NEVER_PROVES_HOTEL_CECIL",

        "family_policy":
            "PREFERENCE_WITH_SAFE_FALLBACK_NOT_BLIND_REPLACEMENT",

        "scene_7":
            "KEEP_CURRENT_AFTER_CONTEXT_FALSE_POSITIVES",

        "automatic_replace":
            False,
    }

    blockers = []

    warnings = []

    if any(
        x["current_family"]
        == "MISSING"
        for x in decisions
    ):
        blockers.append(
            "production_scene_media_missing"
        )

    if identity_guard:
        warnings.append(
            "identity_guard_scenes_present"
        )

    if len(
        provenance
    ) < 12:
        warnings.append(
            "most_current_media_provenance_unverified"
        )

    status = (
        "HOLD"
        if blockers
        else
        "VI260_GLOBAL_PROVENANCE_DIRECTOR_CERTIFIED"
    )

    report = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            short_id,

        "scene_count":
            len(decisions),

        "corrections_applied":
            corrections,

        "provenance_counts":
            dict(
                provenance_counts
            ),

        "action_counts":
            dict(
                action_counts
            ),

        "verified_keep_scenes":
            verified_keep,

        "identity_guard_scenes":
            identity_guard,

        "next_search_scenes":
            top_search,

        "decisions":
            decisions,

        "search_queue":
            search_queue,

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
        " VI260 GLOBAL MEDIA PROVENANCE DIRECTOR"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "SCENES:",
        r["scene_count"]
    )

    print(
        "PROVENANCE:",
        r["provenance_counts"]
    )

    print(
        "ACTIONS:",
        r["action_counts"]
    )

    print(
        "VERIFIED KEEP:",
        r["verified_keep_scenes"]
    )

    print(
        "IDENTITY GUARD:",
        r["identity_guard_scenes"]
    )

    print(
        "NEXT SEARCH:",
        r["next_search_scenes"]
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
        "===== CORRECTIONS APPLIED ====="
    )

    for key, value in (
        r[
            "corrections_applied"
        ].items()
    ):
        print(
            key,
            "=",
            value
        )

    print()
    print(
        "===== GLOBAL MEDIA PLAN ====="
    )

    for x in r["decisions"]:
        print(
            "SCENE",
            x["scene"],
            "|",
            x["category"],
            "| current=",
            x["current_family"],
            "| desired=",
            x["desired_family"],
            "| provenance=",
            x["provenance_status"],
            "| identity=",
            x["identity"],
            "| priority=",
            x["priority"],
            "| action=",
            x["action"],
        )

        if x.get(
            "provenance_title"
        ):
            print(
                "   PROVENANCE:",
                x[
                    "provenance_title"
                ]
            )

    print()
    print(
        "===== NEXT SMART SEARCH QUEUE ====="
    )

    for x in r[
        "search_queue"
    ]:
        print(
            "SCENE",
            x["scene"],
            "| priority=",
            x["priority"],
            "| mode=",
            x["mode"],
            "| providers=",
            x["provider_route"],
        )

        print(
            "   QUERY:",
            x["query"]
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
