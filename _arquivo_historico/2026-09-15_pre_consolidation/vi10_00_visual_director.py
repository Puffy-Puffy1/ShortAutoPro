#!/usr/bin/env python3

import json
from collections import Counter
from pathlib import Path

VERSION = "10.00"

BASE = Path.home() / "ShortAutoPro"

R920 = BASE / "logs/producao/vi9_20_provider_router_master_latest.json"
R850 = BASE / "logs/producao/vi8_50_real_media_master_latest.json"
R800 = BASE / "logs/producao/vi8_00_master_cinematic_gate_latest.json"

OUT = BASE / "logs/producao/vi10_00_visual_director_latest.json"


def load_gate(path):
    if not path.exists():
        return {}

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return data.get("gate", data)


def map_by_scene(items):
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


def ideal_shot(category):
    table = {
        "FACE": "medium",
        "DOCUMENT": "close_up",
        "EVIDENCE": "close_up",
        "LOCATION": "wide",
        "OBJECT": "close_up",
        "GENERAL": "medium",
        "ABSTRACT": "medium",
    }

    return table.get(
        str(category or "GENERAL").upper(),
        "medium"
    )


def provider_score(provider):
    table = {
        "WIKIPEDIA": 92,
        "DOCUMENTARY_ARCHIVE_SHADOW": 90,
        "VISUAL_SEARCH_SHADOW": 85,
        "KEEP_CURRENT": 80,
    }

    return table.get(
        provider,
        70
    )


def identity_risk(category, route):
    if category != "FACE":
        return {
            "status": "PASS",
            "penalty": 0,
        }

    reasons = (
        route.get("reasons")
        or []
    )

    if (
        "face_without_confirmed_entity"
        in reasons
    ):
        return {
            "status": "CAUTION",
            "penalty": 12,
        }

    return {
        "status": "PASS",
        "penalty": 0,
    }


def current_media_score(real_scene):
    ranking = (
        real_scene.get("ranking")
        or {}
    )

    best_real = (
        ranking.get("best_real")
        or {}
    )

    try:
        return float(
            best_real.get("score")
            or 0
        )
    except Exception:
        return 0.0


def build_scene_plan(scene, route, real_scene, cinematic):
    category = (
        route.get("category")
        or real_scene.get("category")
        or "GENERAL"
    )

    provider = (
        route.get("final_provider")
        or "VISUAL_SEARCH_SHADOW"
    )

    desired_shot = ideal_shot(
        category
    )

    current_score = current_media_score(
        real_scene
    )

    ranking = (
        real_scene.get("ranking")
        or {}
    )

    virtual = (
        ranking.get("best_virtual")
        or {}
    )

    ideal_score = float(
        virtual.get("score")
        or 0
    )

    gap = max(
        0.0,
        ideal_score - current_score
    )

    identity = identity_risk(
        category,
        route
    )

    shot_match = cinematic.get(
        "shot_match",
        True
    )

    priority = gap

    reasons = []

    if gap >= 15:
        priority += 25
        reasons.append(
            "large_real_media_gap"
        )

    elif gap >= 7:
        priority += 14
        reasons.append(
            "meaningful_real_media_gap"
        )

    if not shot_match:
        priority += 15
        reasons.append(
            "shot_mismatch"
        )

    if category == "FACE":
        priority += 10
        reasons.append(
            "face_preservation"
        )

    if category in {
        "DOCUMENT",
        "EVIDENCE",
    }:
        priority += 8
        reasons.append(
            "documentary_value"
        )

    if scene in {
        1, 9, 10, 11
    }:
        priority += 8
        reasons.append(
            "high_narrative_impact"
        )

    priority -= identity[
        "penalty"
    ]

    if (
        current_score >= 85
        and gap < 7
        and shot_match
    ):
        action = "KEEP_CURRENT"

        reasons.append(
            "current_media_competitive"
        )

    elif identity[
        "status"
    ] == "CAUTION":
        action = (
            "SEARCH_BETTER_MEDIA_WITH_IDENTITY_GUARD"
        )

    else:
        action = "SEARCH_BETTER_MEDIA"

    confidence = (
        provider_score(provider) * .35
        + min(100, current_score + gap) * .30
        + (
            100 if shot_match else 65
        ) * .20
        + (
            100
            if identity["status"] == "PASS"
            else 70
        ) * .15
    )

    confidence = max(
        0,
        min(100, confidence)
    )

    return {
        "scene": scene,
        "category": category,
        "provider": provider,
        "action": action,
        "ideal_shot": desired_shot,
        "current_score":
            round(current_score, 2),
        "ideal_score":
            round(ideal_score, 2),
        "gap":
            round(gap, 2),
        "priority":
            round(priority, 2),
        "confidence":
            round(confidence, 2),
        "identity":
            identity["status"],
        "shot_match":
            bool(shot_match),
        "motion":
            cinematic.get("motion"),
        "reasons":
            reasons,
    }


def repetition_penalties(plans):
    penalties = {}

    for i in range(
        len(plans) - 2
    ):
        trio = plans[i:i+3]

        cats = [
            x["category"]
            for x in trio
        ]

        providers = [
            x["provider"]
            for x in trio
        ]

        shots = [
            x["ideal_shot"]
            for x in trio
        ]

        if len(set(cats)) == 1:
            penalties[
                trio[1]["scene"]
            ] = penalties.get(
                trio[1]["scene"],
                0
            ) + 8

        if (
            len(set(shots)) == 1
            and len(set(providers)) == 1
        ):
            penalties[
                trio[1]["scene"]
            ] = penalties.get(
                trio[1]["scene"],
                0
            ) + 6

    return penalties


def optimize_global(plans):
    penalties = repetition_penalties(
        plans
    )

    for item in plans:
        penalty = penalties.get(
            item["scene"],
            0
        )

        if penalty:
            item["priority"] = round(
                item["priority"]
                + penalty,
                2
            )

            item["reasons"].append(
                "global_repetition_break"
            )

    return plans


def evaluate():
    r920 = load_gate(R920)
    r850 = load_gate(R850)
    r800 = load_gate(R800)

    if not r920:
        raise RuntimeError(
            "vi9_20_report_missing"
        )

    if not r850:
        raise RuntimeError(
            "vi8_50_report_missing"
        )

    decisions = map_by_scene(
        r920.get("decisions")
        or []
    )

    real_plan = (
        r850.get("plan")
        or {}
    )

    real_scenes = map_by_scene(
        real_plan.get("scenes")
        or []
    )

    cinematic_plans = map_by_scene(
        r800.get("plans")
        or []
    )

    plans = []

    for scene in range(1, 13):
        plans.append(
            build_scene_plan(
                scene,
                decisions.get(scene, {}),
                real_scenes.get(scene, {}),
                cinematic_plans.get(scene, {})
            )
        )

    plans = optimize_global(
        plans
    )

    search_candidates = [
        x
        for x in plans
        if x["action"] != "KEEP_CURRENT"
    ]

    search_candidates.sort(
        key=lambda x: (
            x["priority"],
            x["confidence"]
        ),
        reverse=True
    )

    # Global change budget.
    selected = (
        search_candidates[:6]
    )

    selected_scenes = [
        x["scene"]
        for x in selected
    ]

    for item in plans:
        if (
            item["action"] != "KEEP_CURRENT"
            and item["scene"]
            not in selected_scenes
        ):
            item["action"] = (
                "DEFER_CHANGE_BUDGET"
            )

    provider_counts = Counter(
        x["provider"]
        for x in plans
    )

    action_counts = Counter(
        x["action"]
        for x in plans
    )

    identity_cautions = [
        x["scene"]
        for x in plans
        if x["identity"] == "CAUTION"
    ]

    shot_mismatches = [
        x["scene"]
        for x in plans
        if not x["shot_match"]
    ]

    avg_confidence = round(
        sum(
            x["confidence"]
            for x in plans
        ) / len(plans),
        2
    )

    blockers = []

    warnings = []

    if len(plans) != 12:
        blockers.append(
            "scene_count_not_12"
        )

    if len(selected) > 6:
        blockers.append(
            "change_budget_exceeded"
        )

    if identity_cautions:
        warnings.append(
            "identity_guard_required"
        )

    if shot_mismatches:
        warnings.append(
            "shot_corrections_available"
        )

    if blockers:
        status = "HOLD"

    else:
        status = (
            "VI10_VISUAL_DIRECTOR_SHADOW_CERTIFIED"
        )

    result = {
        "version": VERSION,
        "status": status,
        "short_id":
            r920.get("short_id"),
        "scene_count":
            len(plans),
        "provider_counts":
            dict(provider_counts),
        "action_counts":
            dict(action_counts),
        "selected_change_scenes":
            selected_scenes,
        "selected_change_count":
            len(selected),
        "identity_caution_scenes":
            identity_cautions,
        "shot_mismatch_scenes":
            shot_mismatches,
        "average_confidence":
            avg_confidence,
        "plans":
            plans,
        "blockers":
            blockers,
        "warnings":
            warnings,
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
            {"gate": result},
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
        "============================================"
    )
    print(
        " VI10.00 VISUAL DIRECTOR ENGINE"
    )
    print(
        "============================================"
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
        "AVERAGE CONFIDENCE:",
        r["average_confidence"]
    )

    print(
        "PROVIDER COUNTS:",
        r["provider_counts"]
    )

    print(
        "ACTION COUNTS:",
        r["action_counts"]
    )

    print(
        "SELECTED CHANGES:",
        r["selected_change_scenes"]
    )

    print(
        "IDENTITY CAUTION:",
        r["identity_caution_scenes"]
    )

    print(
        "SHOT MISMATCH:",
        r["shot_mismatch_scenes"]
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
        "===== FINAL VISUAL PLAN ====="
    )

    for x in r["plans"]:
        print(
            "SCENE",
            x["scene"],
            "|",
            x["category"],
            "| provider=",
            x["provider"],
            "| action=",
            x["action"],
            "| shot=",
            x["ideal_shot"],
            "| current=",
            x["current_score"],
            "| ideal=",
            x["ideal_score"],
            "| gap=",
            x["gap"],
            "| priority=",
            x["priority"],
            "| confidence=",
            x["confidence"],
            "| identity=",
            x["identity"],
        )

    print()
    print(
        "AUTOMATIC SEARCH:",
        r["automatic_search"]
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
