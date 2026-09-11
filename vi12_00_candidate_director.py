#!/usr/bin/env python3

import json
import re
from pathlib import Path
from collections import Counter

VERSION = "12.00"

BASE = Path.home() / "ShortAutoPro"

VI10 = (
    BASE
    / "logs/producao/"
      "vi10_00_visual_director_latest.json"
)

VI920 = (
    BASE
    / "logs/producao/"
      "vi9_20_provider_router_master_latest.json"
)

OUT = (
    BASE
    / "logs/producao/"
      "vi12_00_candidate_director_latest.json"
)


MIN_GAIN = 7.0
STRONG_GAIN = 12.0
MAX_REPLACEMENTS = 4


def load_gate(path):
    if not path.exists():
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


def by_scene(items):
    out = {}

    for item in items or []:
        try:
            scene = int(
                item.get("scene")
            )
        except Exception:
            continue

        out[scene] = item

    return out


def clean_query(text):
    bad = {
        "portrait", "medium",
        "wide", "close",
        "close_up", "shot",
        "cinematic", "clear",
        "photo", "image",
        "photograph",
    }

    tokens = re.findall(
        r"[A-Za-zÀ-ÿ0-9'-]+",
        str(text or "")
    )

    result = []

    seen = set()

    for token in tokens:
        low = token.lower()

        if low in bad:
            continue

        if low in seen:
            continue

        seen.add(low)
        result.append(token)

    return " ".join(
        result
    ).strip()


def provider_query(
    provider,
    route
):
    raw = str(
        route.get(
            "original_query"
        )
        or ""
    )

    query = clean_query(
        raw
    )

    category = str(
        route.get(
            "category"
        )
        or "GENERAL"
    ).upper()

    if provider == "WIKIPEDIA":
        return query

    if provider == (
        "DOCUMENTARY_ARCHIVE_SHADOW"
    ):
        suffix = {
            "DOCUMENT":
                "historical document archive",
            "EVIDENCE":
                "historical evidence archive",
        }.get(
            category,
            "historical archive"
        )

        return (
            query + " " + suffix
        ).strip()

    suffix = {
        "FACE":
            "editorial documentary person",
        "LOCATION":
            "documentary location",
        "OBJECT":
            "documentary object detail",
        "DOCUMENT":
            "document archival detail",
        "EVIDENCE":
            "evidence archival detail",
    }.get(
        category,
        "documentary visual"
    )

    return (
        query + " " + suffix
    ).strip()


def identity_policy(
    category,
    identity
):
    if (
        str(category).upper()
        == "FACE"
        and identity == "CAUTION"
    ):
        return {
            "mode":
                "NO_IDENTITY_INFERENCE",

            "require_exact_identity":
                True,

            "generic_face_allowed":
                False,

            "penalty":
                15,
        }

    return {
        "mode":
            "NORMAL",

        "require_exact_identity":
            False,

        "generic_face_allowed":
            True,

        "penalty":
            0,
    }


def minimum_gain_gate(plan):
    current = float(
        plan.get(
            "current_score"
        )
        or 0
    )

    ideal = float(
        plan.get(
            "ideal_score"
        )
        or 0
    )

    gain = (
        ideal - current
    )

    if gain < 0:
        return {
            "status":
                "REJECT",

            "reason":
                "projected_candidate_worse_than_current",

            "gain":
                round(gain, 2),
        }

    if gain < MIN_GAIN:
        return {
            "status":
                "REJECT",

            "reason":
                "gain_below_minimum",

            "gain":
                round(gain, 2),
        }

    if gain >= STRONG_GAIN:
        strength = "STRONG"
    else:
        strength = "VALID"

    return {
        "status":
            "PASS",

        "reason":
            "minimum_gain_met",

        "strength":
            strength,

        "gain":
            round(gain, 2),
    }


def candidate_score(plan, route):
    current = float(
        plan.get(
            "current_score"
        )
        or 0
    )

    ideal = float(
        plan.get(
            "ideal_score"
        )
        or 0
    )

    provider = str(
        plan.get(
            "provider"
        )
        or ""
    )

    provider_quality = {
        "WIKIPEDIA": 92,
        "DOCUMENTARY_ARCHIVE_SHADOW": 91,
        "VISUAL_SEARCH_SHADOW": 86,
    }.get(
        provider,
        75
    )

    shot = (
        100
        if plan.get(
            "shot_match",
            True
        )
        else 72
    )

    identity = identity_policy(
        plan.get(
            "category"
        ),
        plan.get(
            "identity"
        )
    )

    route_confidence = float(
        route.get(
            "confidence"
        )
        or 0
    ) * 100

    projected = (
        ideal * .40
        + provider_quality * .20
        + shot * .15
        + route_confidence * .15
        + 100 * .10
        - identity["penalty"]
    )

    projected = max(
        0,
        min(
            100,
            projected
        )
    )

    return {
        "current":
            round(current, 2),

        "ideal":
            round(ideal, 2),

        "projected_candidate":
            round(projected, 2),

        "projected_vs_current":
            round(
                projected - current,
                2
            ),
    }


def scene_decision(
    plan,
    route
):
    provider = (
        plan.get(
            "provider"
        )
        or route.get(
            "final_provider"
        )
        or "VISUAL_SEARCH_SHADOW"
    )

    gain_gate = minimum_gain_gate(
        plan
    )

    identity = identity_policy(
        plan.get(
            "category"
        ),
        plan.get(
            "identity"
        )
    )

    candidate = candidate_score(
        plan,
        route
    )

    query = provider_query(
        provider,
        route
    )

    reasons = []

    if gain_gate[
        "status"
    ] != "PASS":

        action = "KEEP_CURRENT"

        reasons.append(
            gain_gate[
                "reason"
            ]
        )

    elif (
        identity[
            "require_exact_identity"
        ]
    ):

        action = (
            "CANDIDATE_SEARCH_IDENTITY_LOCKED"
        )

        reasons.append(
            "exact_identity_required"
        )

    else:

        action = (
            "CANDIDATE_SEARCH_READY"
        )

        reasons.append(
            "minimum_gain_certified"
        )


    if not query:
        action = "KEEP_CURRENT"

        reasons.append(
            "query_missing"
        )


    priority = float(
        plan.get(
            "priority"
        )
        or 0
    )


    if gain_gate[
        "status"
    ] == "PASS":

        priority += (
            gain_gate[
                "gain"
            ] * 2
        )


    if gain_gate.get(
        "strength"
    ) == "STRONG":

        priority += 15


    if identity[
        "require_exact_identity"
    ]:

        priority -= 8


    return {
        "scene":
            plan.get(
                "scene"
            ),

        "category":
            plan.get(
                "category"
            ),

        "provider":
            provider,

        "query":
            query,

        "ideal_shot":
            plan.get(
                "ideal_shot"
            ),

        "current_score":
            plan.get(
                "current_score"
            ),

        "ideal_score":
            plan.get(
                "ideal_score"
            ),

        "gain_gate":
            gain_gate,

        "candidate_projection":
            candidate,

        "identity_policy":
            identity,

        "action":
            action,

        "priority":
            round(
                priority,
                2
            ),

        "reasons":
            reasons,

        "network_allowed":
            False,

        "download_allowed":
            False,

        "replace_allowed":
            False,
    }


def dedupe_queries(items):
    seen = {}

    for item in items:
        query = (
            item.get(
                "query"
            )
            or ""
        ).lower().strip()

        if not query:
            continue

        if query in seen:
            item[
                "duplicate_query_with_scene"
            ] = seen[query]

            item[
                "priority"
            ] = round(
                item[
                    "priority"
                ] - 10,
                2
            )

        else:
            seen[query] = (
                item["scene"]
            )

    return items


def evaluate():
    vi10 = load_gate(
        VI10
    )

    vi920 = load_gate(
        VI920
    )

    if not vi10:
        raise RuntimeError(
            "vi10_report_missing"
        )

    if not vi920:
        raise RuntimeError(
            "vi9_20_report_missing"
        )

    plans = by_scene(
        vi10.get(
            "plans"
        )
        or []
    )

    routes = by_scene(
        vi920.get(
            "routes"
        )
        or []
    )

    decisions = []

    for scene in range(
        1,
        13
    ):
        if scene not in plans:
            continue

        decisions.append(
            scene_decision(
                plans[scene],
                routes.get(
                    scene,
                    {}
                )
            )
        )

    decisions = dedupe_queries(
        decisions
    )

    candidates = [
        x
        for x in decisions
        if x["action"] in {
            "CANDIDATE_SEARCH_READY",
            "CANDIDATE_SEARCH_IDENTITY_LOCKED",
        }
    ]

    candidates.sort(
        key=lambda x: (
            x["priority"],
            x[
                "candidate_projection"
            ][
                "projected_vs_current"
            ]
        ),
        reverse=True
    )

    selected = (
        candidates[
            :MAX_REPLACEMENTS
        ]
    )

    selected_scenes = {
        x["scene"]
        for x in selected
    }

    for item in decisions:
        if (
            item["action"]
            in {
                "CANDIDATE_SEARCH_READY",
                "CANDIDATE_SEARCH_IDENTITY_LOCKED",
            }
            and item[
                "scene"
            ]
            not in selected_scenes
        ):
            item[
                "action"
            ] = (
                "DEFER_CANDIDATE_BUDGET"
            )

            item[
                "reasons"
            ].append(
                "global_replacement_budget"
            )


    action_counts = Counter(
        x["action"]
        for x in decisions
    )

    provider_counts = Counter(
        x["provider"]
        for x in decisions
    )

    rejected_gain = [
        x["scene"]
        for x in decisions
        if x[
            "gain_gate"
        ][
            "status"
        ] == "REJECT"
    ]

    identity_locked = [
        x["scene"]
        for x in decisions
        if x[
            "identity_policy"
        ][
            "require_exact_identity"
        ]
    ]

    negative_projection = [
        x["scene"]
        for x in decisions
        if x[
            "candidate_projection"
        ][
            "projected_vs_current"
        ] < 0
    ]

    blockers = []

    warnings = []

    if len(decisions) != 12:
        blockers.append(
            "scene_count_not_12"
        )

    if len(selected) > MAX_REPLACEMENTS:
        blockers.append(
            "replacement_budget_exceeded"
        )

    if any(
        x["replace_allowed"]
        for x in decisions
    ):
        blockers.append(
            "replacement_activation_detected"
        )

    if any(
        x["download_allowed"]
        for x in decisions
    ):
        blockers.append(
            "download_activation_detected"
        )

    if rejected_gain:
        warnings.append(
            "minimum_gain_rejections_active"
        )

    if identity_locked:
        warnings.append(
            "identity_locked_candidates_present"
        )

    if negative_projection:
        warnings.append(
            "negative_candidate_projection_detected"
        )

    status = (
        "HOLD"
        if blockers
        else "VI12_CANDIDATE_DIRECTOR_SHADOW_CERTIFIED"
    )

    result = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            vi10.get(
                "short_id"
            ),

        "scene_count":
            len(decisions),

        "minimum_gain":
            MIN_GAIN,

        "strong_gain":
            STRONG_GAIN,

        "max_replacements":
            MAX_REPLACEMENTS,

        "selected_candidate_scenes":
            sorted(
                selected_scenes
            ),

        "selected_candidate_count":
            len(
                selected_scenes
            ),

        "gain_rejected_scenes":
            rejected_gain,

        "identity_locked_scenes":
            identity_locked,

        "negative_projection_scenes":
            negative_projection,

        "action_counts":
            dict(
                action_counts
            ),

        "provider_counts":
            dict(
                provider_counts
            ),

        "decisions":
            decisions,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "network_executed":
            False,

        "automatic_search":
            False,

        "automatic_download":
            False,

        "automatic_replace":
            False,

        "media_mutated":
            False,

        "renderer_activation":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "source_recovery":
            "SHADOW_ONLY",

        "full_active":
            False,
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUT.write_text(
        json.dumps(
            {
                "gate":
                    result
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return result


if __name__ == "__main__":
    r = evaluate()

    print()
    print(
        "=============================================="
    )
    print(
        " VI12.00 VISUAL CANDIDATE DIRECTOR"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "SHORT ID:",
        r["short_id"]
    )

    print(
        "SCENES:",
        r["scene_count"]
    )

    print(
        "MINIMUM GAIN:",
        r["minimum_gain"]
    )

    print(
        "MAX REPLACEMENTS:",
        r["max_replacements"]
    )

    print(
        "SELECTED:",
        r[
            "selected_candidate_scenes"
        ]
    )

    print(
        "GAIN REJECTED:",
        r[
            "gain_rejected_scenes"
        ]
    )

    print(
        "IDENTITY LOCKED:",
        r[
            "identity_locked_scenes"
        ]
    )

    print(
        "ACTION COUNTS:",
        r["action_counts"]
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
        "===== CANDIDATE PLAN ====="
    )

    for x in r["decisions"]:
        print(
            "SCENE",
            x["scene"],
            "|",
            x["category"],
            "| provider=",
            x["provider"],
            "| action=",
            x["action"],
            "| gain=",
            x[
                "gain_gate"
            ].get(
                "gain"
            ),
            "| projected_gain=",
            x[
                "candidate_projection"
            ][
                "projected_vs_current"
            ],
            "| priority=",
            x["priority"],
            "| identity=",
            x[
                "identity_policy"
            ][
                "mode"
            ],
        )

    print()
    print(
        "NETWORK EXECUTED:",
        r["network_executed"]
    )

    print(
        "AUTOMATIC DOWNLOAD:",
        r["automatic_download"]
    )

    print(
        "AUTOMATIC REPLACE:",
        r["automatic_replace"]
    )

    print(
        "MEDIA MUTATED:",
        r["media_mutated"]
    )

    print(
        "FFMPEG EXECUTED:",
        r["ffmpeg_executed"]
    )

    print(
        "VIDEO GENERATED:",
        r["video_generated"]
    )

    print(
        "SOURCE RECOVERY:",
        r["source_recovery"]
    )

    print(
        "FULL ACTIVE:",
        r["full_active"]
    )
