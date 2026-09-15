#!/usr/bin/env python3

import json
from pathlib import Path
from collections import Counter

VERSION = "30.00"

BASE = Path.home() / "ShortAutoPro"

VI10 = (
    BASE / "logs/producao/"
    "vi10_00_visual_director_latest.json"
)

VI14 = (
    BASE / "logs/producao/"
    "vi14_00_consensus_candidate_gate_latest.json"
)

VI20 = (
    BASE / "logs/producao/"
    "vi20_00_real_media_ab_latest.json"
)

VI25 = (
    BASE / "manifests/"
    "vi25_1_shadow_override_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi30_00_cross_media_director_latest.json"
)


def load(path):
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


def family_from_path(path):
    ext = Path(
        str(path or "")
    ).suffix.lower()

    if ext in {
        ".mp4", ".mov",
        ".webm", ".mkv"
    }:
        return "VIDEO"

    if ext in {
        ".jpg", ".jpeg",
        ".png", ".webp"
    }:
        return "IMAGE"

    return "UNKNOWN"


def current_media(short_id, scene):
    folder = (
        BASE
        / "imagens"
        / f"short_{short_id}"
    )

    matches = list(
        folder.glob(
            f"scene_{scene:02d}.*"
        )
    )

    matches = [
        x
        for x in matches
        if x.is_file()
    ]

    if not matches:
        return None

    matches.sort(
        key=lambda p:
            p.stat().st_mtime,
        reverse=True
    )

    return matches[0]


def desired_family(
    category,
    motion,
    scene,
    narrative_priority
):
    category = str(
        category or ""
    ).upper()

    motion = str(
        motion or ""
    ).upper()

    if category in {
        "DOCUMENT",
        "EVIDENCE"
    }:
        return (
            "ARCHIVAL_IMAGE"
        )

    if (
        scene == 1
        and narrative_priority
        >= 8
    ):
        return "VIDEO"

    if category == "FACE":
        return "IMAGE"

    if category == "OBJECT":
        return "IMAGE"

    if category == "LOCATION":
        if motion in {
            "HORIZONTAL_DISCOVERY",
            "ARCHITECTURE_DRIFT",
            "SLOW_PUSH"
        }:
            return "VIDEO"

        return "IMAGE"

    return "IMAGE"


def compatibility(
    current_family,
    desired_family
):
    if desired_family == (
        "ARCHIVAL_IMAGE"
    ):
        return (
            current_family
            == "IMAGE"
        )

    return (
        current_family
        == desired_family
    )


def scene_score(
    plan,
    consensus,
    current_family,
    desired_family,
    vi20_scene=None
):
    current_score = float(
        plan.get(
            "current_score"
        )
        or 0
    )

    ideal_score = float(
        plan.get(
            "ideal_score"
        )
        or current_score
    )

    expected_gain = (
        ideal_score
        - current_score
    )

    cross_type = (
        not compatibility(
            current_family,
            desired_family
        )
    )

    score = 50.0

    if expected_gain >= 12:
        score += 20

    elif expected_gain >= 7:
        score += 12

    elif expected_gain <= 0:
        score -= 12

    if cross_type:
        score += 10

    if not plan.get(
        "shot_match",
        True
    ):
        score += 12

    if consensus.get(
        "consensus"
    ):
        score += 15

    if (
        plan.get(
            "identity"
        )
        == "CAUTION"
    ):
        score -= 15

    if vi20_scene:
        gain = float(
            vi20_scene.get(
                "final_gain"
            )
            or 0
        )

        if gain >= 20:
            score += 20

        elif gain >= 7:
            score += 10

    return max(
        0,
        min(
            100,
            round(score, 2)
        )
    )


def evaluate():
    vi10 = load(
        VI10
    )

    vi14 = load(
        VI14
    )

    vi20 = load(
        VI20
    )

    vi25 = load(
        VI25
    )

    if not vi10:
        raise RuntimeError(
            "vi10_missing"
        )

    short_id = str(
        vi10.get(
            "short_id"
        )
        or ""
    )

    plans = by_scene(
        vi10.get(
            "plans"
        )
        or []
    )

    consensus = by_scene(
        vi14.get(
            "decisions"
        )
        or []
    )

    vi20_results = by_scene(
        vi20.get(
            "results"
        )
        or []
    )

    decisions = []

    for scene in range(
        1,
        13
    ):
        plan = plans.get(
            scene,
            {}
        )

        current = current_media(
            short_id,
            scene
        )

        if current is None:
            current_family = (
                "UNKNOWN"
            )
        else:
            current_family = (
                family_from_path(
                    current
                )
            )

        desired = desired_family(
            plan.get(
                "category"
            ),
            plan.get(
                "motion"
            ),
            scene,
            float(
                plan.get(
                    "priority"
                )
                or 0
            )
        )

        same_family = (
            compatibility(
                current_family,
                desired
            )
        )

        score = scene_score(
            plan,
            consensus.get(
                scene,
                {}
            ),
            current_family,
            desired,
            vi20_results.get(
                scene
            )
        )

        reasons = []

        if same_family:
            reasons.append(
                "current_media_family_compatible"
            )

        else:
            reasons.append(
                "cross_media_opportunity"
            )

        if not plan.get(
            "shot_match",
            True
        ):
            reasons.append(
                "shot_mismatch"
            )

        if plan.get(
            "identity"
        ) == "CAUTION":
            reasons.append(
                "identity_guard"
            )

        if (
            scene
            in vi20_results
            and vi20_results[
                scene
            ].get(
                "decision"
            )
            == "READY_FOR_MANUAL_REPLACEMENT"
        ):
            reasons.append(
                "real_candidate_certified"
            )

        if (
            score >= 75
            and not same_family
        ):
            action = (
                "CROSS_MEDIA_CANDIDATE"
            )

        elif (
            score >= 70
            and same_family
        ):
            action = (
                "SAME_MEDIA_FAMILY_OPTIMIZE"
            )

        else:
            action = (
                "KEEP_CURRENT"
            )

        decisions.append({
            "scene":
                scene,

            "category":
                plan.get(
                    "category"
                ),

            "current_media":
                str(current)
                if current
                else None,

            "current_family":
                current_family,

            "desired_family":
                desired,

            "cross_type":
                not same_family,

            "action":
                action,

            "score":
                score,

            "identity":
                plan.get(
                    "identity"
                ),

            "shot_match":
                plan.get(
                    "shot_match"
                ),

            "reasons":
                reasons,
        })

    cross_candidates = [
        x
        for x in decisions
        if x[
            "action"
        ]
        == "CROSS_MEDIA_CANDIDATE"
    ]

    cross_candidates.sort(
        key=lambda x:
            x["score"],
        reverse=True
    )

    # Conservative global budget.
    selected = (
        cross_candidates[:3]
    )

    selected_scenes = {
        x["scene"]
        for x in selected
    }

    for item in decisions:
        if (
            item["action"]
            == "CROSS_MEDIA_CANDIDATE"
            and item[
                "scene"
            ]
            not in selected_scenes
        ):
            item[
                "action"
            ] = (
                "DEFER_CROSS_MEDIA_BUDGET"
            )

    counts = Counter(
        x["action"]
        for x in decisions
    )

    family_counts = Counter(
        x["desired_family"]
        for x in decisions
    )

    cross_scenes = [
        x["scene"]
        for x in decisions
        if x["cross_type"]
    ]

    identity_guard = [
        x["scene"]
        for x in decisions
        if x["identity"]
        == "CAUTION"
    ]

    blockers = []

    warnings = []

    if len(decisions) != 12:
        blockers.append(
            "scene_count_not_12"
        )

    if len(selected) > 3:
        blockers.append(
            "cross_media_budget_exceeded"
        )

    if identity_guard:
        warnings.append(
            "identity_guard_scenes_present"
        )

    if cross_scenes:
        warnings.append(
            "cross_media_opportunities_present"
        )

    status = (
        "HOLD"
        if blockers
        else
        "VI30_CROSS_MEDIA_DIRECTOR_CERTIFIED"
    )

    result = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            short_id,

        "scene_count":
            len(decisions),

        "desired_family_counts":
            dict(
                family_counts
            ),

        "action_counts":
            dict(
                counts
            ),

        "cross_type_scenes":
            cross_scenes,

        "selected_cross_media_scenes":
            sorted(
                selected_scenes
            ),

        "identity_guard_scenes":
            identity_guard,

        "vi25_shadow_cross_type":
            vi25.get(
                "cross_type"
            ),

        "decisions":
            decisions,

        "blockers":
            blockers,

        "warnings":
            warnings,

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
        " VI30.00 CROSS-MEDIA VISUAL DIRECTOR"
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
        "DESIRED FAMILIES:",
        r[
            "desired_family_counts"
        ]
    )

    print(
        "ACTIONS:",
        r[
            "action_counts"
        ]
    )

    print(
        "CROSS TYPE SCENES:",
        r[
            "cross_type_scenes"
        ]
    )

    print(
        "SELECTED CROSS MEDIA:",
        r[
            "selected_cross_media_scenes"
        ]
    )

    print(
        "IDENTITY GUARD:",
        r[
            "identity_guard_scenes"
        ]
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
        "===== CROSS-MEDIA PLAN ====="
    )

    for x in r[
        "decisions"
    ]:
        print(
            "SCENE",
            x["scene"],
            "|",
            x["category"],
            "| current=",
            x["current_family"],
            "| desired=",
            x["desired_family"],
            "| cross=",
            x["cross_type"],
            "| action=",
            x["action"],
            "| score=",
            x["score"],
            "| identity=",
            x["identity"],
        )

    print()
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
