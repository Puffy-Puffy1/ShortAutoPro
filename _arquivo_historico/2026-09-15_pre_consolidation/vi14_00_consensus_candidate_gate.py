#!/usr/bin/env python3

import json
from pathlib import Path
from collections import Counter

VERSION = "14.00"

BASE = Path.home() / "ShortAutoPro"

VI12 = (
    BASE
    / "logs/producao/"
      "vi12_00_candidate_director_latest.json"
)

OUT = (
    BASE
    / "logs/producao/"
      "vi14_00_consensus_candidate_gate_latest.json"
)

MIN_GAIN = 7.0
MIN_PROJECTED_GAIN = 3.0
STRONG_GAIN = 12.0
MAX_REAL_SEARCH = 3


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


def consensus_scene(item):
    gain = float(
        item.get(
            "gain_gate",
            {}
        ).get(
            "gain"
        )
        or 0
    )

    projected = float(
        item.get(
            "candidate_projection",
            {}
        ).get(
            "projected_vs_current"
        )
        or 0
    )

    identity = (
        item.get(
            "identity_policy",
            {}
        ).get(
            "mode"
        )
        or "NORMAL"
    )

    provider = (
        item.get(
            "provider"
        )
        or "UNKNOWN"
    )

    query = (
        item.get(
            "query"
        )
        or ""
    ).strip()

    reasons = []

    gate_gain = (
        gain >= MIN_GAIN
    )

    gate_projection = (
        projected
        >= MIN_PROJECTED_GAIN
    )

    gate_query = bool(
        query
    )

    gate_provider = (
        provider
        not in {
            "",
            "UNKNOWN",
        }
    )

    if not gate_gain:
        reasons.append(
            "insufficient_expected_gain"
        )

    if not gate_projection:
        reasons.append(
            "projection_not_better_than_current"
        )

    if not gate_query:
        reasons.append(
            "query_missing"
        )

    if not gate_provider:
        reasons.append(
            "provider_missing"
        )

    consensus = (
        gate_gain
        and gate_projection
        and gate_query
        and gate_provider
    )

    if not consensus:
        action = "KEEP_CURRENT"

    elif identity == (
        "NO_IDENTITY_INFERENCE"
    ):
        action = (
            "REAL_SEARCH_IDENTITY_LOCKED"
        )
        reasons.append(
            "identity_verification_required"
        )

    else:
        action = (
            "REAL_SEARCH_READY"
        )
        reasons.append(
            "consensus_gain_certified"
        )

    if (
        gain >= STRONG_GAIN
        and projected >= 10
    ):
        strength = "STRONG"

    elif consensus:
        strength = "VALID"

    else:
        strength = "REJECTED"

    confidence = (
        min(
            100,
            max(
                0,
                50 + gain * 2.5
            )
        ) * .45
        +
        min(
            100,
            max(
                0,
                50 + projected * 2
            )
        ) * .40
        +
        (
            100
            if identity == "NORMAL"
            else 70
        ) * .15
    )

    return {
        "scene":
            item.get(
                "scene"
            ),

        "category":
            item.get(
                "category"
            ),

        "provider":
            provider,

        "query":
            query,

        "ideal_shot":
            item.get(
                "ideal_shot"
            ),

        "current_score":
            item.get(
                "current_score"
            ),

        "ideal_score":
            item.get(
                "ideal_score"
            ),

        "gain":
            round(
                gain,
                2
            ),

        "projected_gain":
            round(
                projected,
                2
            ),

        "gain_gate":
            gate_gain,

        "projection_gate":
            gate_projection,

        "query_gate":
            gate_query,

        "provider_gate":
            gate_provider,

        "consensus":
            consensus,

        "strength":
            strength,

        "identity_mode":
            identity,

        "action":
            action,

        "confidence":
            round(
                confidence,
                2
            ),

        "priority":
            float(
                item.get(
                    "priority"
                )
                or 0
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


def evaluate():
    vi12 = load_gate(
        VI12
    )

    if not vi12:
        raise RuntimeError(
            "vi12_report_missing"
        )

    source = (
        vi12.get(
            "decisions"
        )
        or []
    )

    decisions = [
        consensus_scene(
            item
        )
        for item in source
    ]

    ready = [
        x
        for x in decisions
        if x[
            "action"
        ] in {
            "REAL_SEARCH_READY",
            "REAL_SEARCH_IDENTITY_LOCKED",
        }
    ]

    ready.sort(
        key=lambda x: (
            x["strength"] == "STRONG",
            x["confidence"],
            x["priority"],
            x["projected_gain"],
            x["gain"],
        ),
        reverse=True
    )

    selected = (
        ready[
            :MAX_REAL_SEARCH
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
                "REAL_SEARCH_READY",
                "REAL_SEARCH_IDENTITY_LOCKED",
            }
            and item["scene"]
            not in selected_scenes
        ):
            item[
                "action"
            ] = (
                "DEFER_REAL_SEARCH_BUDGET"
            )

            item[
                "reasons"
            ].append(
                "real_search_budget"
            )

    rejected_projection = [
        x["scene"]
        for x in decisions
        if (
            x["gain_gate"]
            and not x[
                "projection_gate"
            ]
        )
    ]

    rejected_gain = [
        x["scene"]
        for x in decisions
        if not x[
            "gain_gate"
        ]
    ]

    identity_locked_ready = [
        x["scene"]
        for x in decisions
        if (
            x["action"]
            == "REAL_SEARCH_IDENTITY_LOCKED"
        )
    ]

    actions = Counter(
        x["action"]
        for x in decisions
    )

    blockers = []

    warnings = []

    if len(decisions) != 12:
        blockers.append(
            "scene_count_not_12"
        )

    if len(selected) > MAX_REAL_SEARCH:
        blockers.append(
            "real_search_budget_exceeded"
        )

    if any(
        x["network_allowed"]
        or x["download_allowed"]
        or x["replace_allowed"]
        for x in decisions
    ):
        blockers.append(
            "unsafe_activation_detected"
        )

    if rejected_projection:
        warnings.append(
            "projection_disagreement_detected"
        )

    if identity_locked_ready:
        warnings.append(
            "identity_locked_search_present"
        )

    status = (
        "HOLD"
        if blockers
        else
        "VI14_CONSENSUS_CANDIDATE_GATE_CERTIFIED"
    )

    result = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            vi12.get(
                "short_id"
            ),

        "scene_count":
            len(decisions),

        "min_gain":
            MIN_GAIN,

        "min_projected_gain":
            MIN_PROJECTED_GAIN,

        "max_real_search":
            MAX_REAL_SEARCH,

        "selected_real_search_scenes":
            sorted(
                selected_scenes
            ),

        "rejected_gain_scenes":
            rejected_gain,

        "projection_disagreement_scenes":
            rejected_projection,

        "identity_locked_ready_scenes":
            identity_locked_ready,

        "action_counts":
            dict(
                actions
            ),

        "decisions":
            decisions,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "network_executed":
            False,

        "automatic_download":
            False,

        "automatic_replace":
            False,

        "media_mutated":
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
        " VI14.00 CONSENSUS CANDIDATE GATE"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "SELECTED REAL SEARCH:",
        r[
            "selected_real_search_scenes"
        ]
    )

    print(
        "GAIN REJECTED:",
        r[
            "rejected_gain_scenes"
        ]
    )

    print(
        "PROJECTION DISAGREEMENT:",
        r[
            "projection_disagreement_scenes"
        ]
    )

    print(
        "IDENTITY LOCKED READY:",
        r[
            "identity_locked_ready_scenes"
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
        "===== CONSENSUS PLAN ====="
    )

    for x in r["decisions"]:
        print(
            "SCENE",
            x["scene"],
            "| action=",
            x["action"],
            "| gain=",
            x["gain"],
            "| projected=",
            x["projected_gain"],
            "| consensus=",
            x["consensus"],
            "| strength=",
            x["strength"],
            "| confidence=",
            x["confidence"],
            "| identity=",
            x["identity_mode"],
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


def evaluate():
    vi12 = load_gate(
        VI12
    )

    if not vi12:
        raise RuntimeError(
            "vi12_report_missing"
        )

    source = (
        vi12.get(
            "decisions"
        )
        or []
    )

    decisions = [
        consensus_scene(
            item
        )
        for item in source
    ]

    ready = [
        x
        for x in decisions
        if x[
            "action"
        ] in {
            "REAL_SEARCH_READY",
            "REAL_SEARCH_IDENTITY_LOCKED",
        }
    ]

    ready.sort(
        key=lambda x: (
            x["strength"] == "STRONG",
            x["confidence"],
            x["priority"],
            x["projected_gain"],
            x["gain"],
        ),
        reverse=True
    )

    selected = (
        ready[
            :MAX_REAL_SEARCH
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
                "REAL_SEARCH_READY",
                "REAL_SEARCH_IDENTITY_LOCKED",
            }
            and item["scene"]
            not in selected_scenes
        ):
            item[
                "action"
            ] = (
                "DEFER_REAL_SEARCH_BUDGET"
            )

            item[
                "reasons"
            ].append(
                "real_search_budget"
            )

    rejected_projection = [
        x["scene"]
        for x in decisions
        if (
            x["gain_gate"]
            and not x[
                "projection_gate"
            ]
        )
    ]

    rejected_gain = [
        x["scene"]
        for x in decisions
        if not x[
            "gain_gate"
        ]
    ]

    identity_locked_ready = [
        x["scene"]
        for x in decisions
        if (
            x["action"]
            == "REAL_SEARCH_IDENTITY_LOCKED"
        )
    ]

    actions = Counter(
        x["action"]
        for x in decisions
    )

    blockers = []

    warnings = []

    if len(decisions) != 12:
        blockers.append(
            "scene_count_not_12"
        )

    if len(selected) > MAX_REAL_SEARCH:
        blockers.append(
            "real_search_budget_exceeded"
        )

    if any(
        x["network_allowed"]
        or x["download_allowed"]
        or x["replace_allowed"]
        for x in decisions
    ):
        blockers.append(
            "unsafe_activation_detected"
        )

    if rejected_projection:
        warnings.append(
            "projection_disagreement_detected"
        )

    if identity_locked_ready:
        warnings.append(
            "identity_locked_search_present"
        )

    status = (
        "HOLD"
        if blockers
        else
        "VI14_CONSENSUS_CANDIDATE_GATE_CERTIFIED"
    )

    result = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            vi12.get(
                "short_id"
            ),

        "scene_count":
            len(decisions),

        "min_gain":
            MIN_GAIN,

        "min_projected_gain":
            MIN_PROJECTED_GAIN,

        "max_real_search":
            MAX_REAL_SEARCH,

        "selected_real_search_scenes":
            sorted(
                selected_scenes
            ),

        "rejected_gain_scenes":
            rejected_gain,

        "projection_disagreement_scenes":
            rejected_projection,

        "identity_locked_ready_scenes":
            identity_locked_ready,

        "action_counts":
            dict(
                actions
            ),

        "decisions":
            decisions,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "network_executed":
            False,

        "automatic_download":
            False,

        "automatic_replace":
            False,

        "media_mutated":
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
        " VI14.00 CONSENSUS CANDIDATE GATE"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "SELECTED REAL SEARCH:",
        r[
            "selected_real_search_scenes"
        ]
    )

    print(
        "GAIN REJECTED:",
        r[
            "rejected_gain_scenes"
        ]
    )

    print(
        "PROJECTION DISAGREEMENT:",
        r[
            "projection_disagreement_scenes"
        ]
    )

    print(
        "IDENTITY LOCKED READY:",
        r[
            "identity_locked_ready_scenes"
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
        "===== CONSENSUS PLAN ====="
    )

    for x in r["decisions"]:
        print(
            "SCENE",
            x["scene"],
            "| action=",
            x["action"],
            "| gain=",
            x["gain"],
            "| projected=",
            x["projected_gain"],
            "| consensus=",
            x["consensus"],
            "| strength=",
            x["strength"],
            "| confidence=",
            x["confidence"],
            "| identity=",
            x["identity_mode"],
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
