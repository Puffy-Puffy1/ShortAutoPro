#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$HOME/ShortAutoPro" || exit 1

echo
echo "======================================"
echo " VI8.21 -> VI8.30"
echo " CINEMATIC MEDIA MASTER SYSTEM"
echo " SHADOW ONLY"
echo "======================================"
echo
echo "VIDEO GENERATION=OFF"
echo "FFMPEG=OFF"
echo "DOWNLOAD=OFF"
echo "MEDIA REPLACEMENT=OFF"
echo

VIDEO_BEFORE="$(sha256sum video.py | awk '{print $1}')"
GERAR_BEFORE="$(sha256sum gerar_short.sh | awk '{print $1}')"


# =====================================================
# VI8.21 — IMPROVEMENT PRIORITY
# =====================================================

cat > vi8_21_improvement_priority.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.21"


def priority(
    selection,
    cinematic_plan=None
):
    comparison = (
        selection.get("comparison")
        or {}
    )

    delta = float(
        comparison.get(
            "delta",
            0
        )
        or 0
    )

    category = str(
        selection.get(
            "category"
        )
        or "GENERAL"
    ).upper()

    scene = int(
        selection.get(
            "scene"
        )
        or 0
    )

    score = delta

    reasons = []

    if delta >= 15:
        score += 20
        reasons.append(
            "large_media_gain"
        )

    elif delta >= 7:
        score += 10
        reasons.append(
            "meaningful_media_gain"
        )

    if category == "FACE":
        score += 10
        reasons.append(
            "subject_preservation_priority"
        )

    if category in {
        "DOCUMENT",
        "EVIDENCE",
    }:
        score += 8
        reasons.append(
            "documentary_priority"
        )

    if scene in {
        1,
        9,
        10,
        11,
    }:
        score += 8
        reasons.append(
            "high_narrative_impact"
        )

    if cinematic_plan:
        if not cinematic_plan.get(
            "shot_match",
            True
        ):
            score += 15
            reasons.append(
                "shot_mismatch"
            )

        if cinematic_plan.get(
            "status"
        ) == "HOLD":
            score += 25
            reasons.append(
                "cinematic_hold"
            )

    return {
        "version":
            VERSION,

        "scene":
            scene,

        "priority_score":
            round(
                score,
                2
            ),

        "reasons":
            reasons,
    }


def self_test():
    result = priority({
        "scene": 6,
        "category": "FACE",
        "comparison": {
            "delta": 18
        },
    })

    assert (
        result["priority_score"]
        > 18
    )

    print(
        "VI8.21 IMPROVEMENT PRIORITY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.22 — CONFIDENCE ENGINE
# =====================================================

cat > vi8_22_selection_confidence.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.22"


def evaluate(selection):
    winner = (
        selection.get("winner")
        or {}
    )

    ranking = (
        selection.get("ranking")
        or []
    )

    winner_score = float(
        winner.get(
            "score",
            0
        )
        or 0
    )

    eligible = [
        item
        for item in ranking
        if item.get(
            "eligible"
        )
    ]

    eligible.sort(
        key=lambda x:
            float(
                x.get(
                    "score",
                    0
                )
            ),
        reverse=True
    )

    second_score = (
        float(
            eligible[1].get(
                "score",
                0
            )
        )
        if len(eligible) >= 2
        else 0
    )

    margin = (
        winner_score
        - second_score
    )

    comparison = (
        selection.get("comparison")
        or {}
    )

    improvement = float(
        comparison.get(
            "delta",
            0
        )
        or 0
    )

    confidence = (
        45
        + min(
            30,
            max(
                0,
                margin * 2
            )
        )
        + min(
            25,
            max(
                0,
                improvement
            )
        )
    )

    confidence = max(
        0,
        min(
            100,
            confidence
        )
    )

    if confidence >= 80:
        level = "HIGH"

    elif confidence >= 65:
        level = "MEDIUM"

    else:
        level = "LOW"

    return {
        "version":
            VERSION,

        "scene":
            selection.get(
                "scene"
            ),

        "confidence":
            round(
                confidence,
                2
            ),

        "level":
            level,

        "winner_margin":
            round(
                margin,
                2
            ),

        "improvement":
            round(
                improvement,
                2
            ),
    }


def self_test():
    result = evaluate({
        "scene": 4,

        "winner": {
            "score": 90
        },

        "ranking": [
            {
                "score": 90,
                "eligible": True,
            },
            {
                "score": 70,
                "eligible": True,
            },
        ],

        "comparison": {
            "delta": 15
        },
    })

    assert (
        result["confidence"]
        >= 80
    )

    print(
        "VI8.22 SELECTION CONFIDENCE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.23 — REPLACEMENT BUDGET
# =====================================================

cat > vi8_23_replacement_budget.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.23"

MAX_REPLACEMENTS = 6
MAX_STRONG_CHANGES = 4


def allocate(items):
    ranked = sorted(
        items,
        key=lambda item:
            item.get(
                "priority_score",
                0
            ),
        reverse=True
    )

    selected = []

    strong_count = 0

    for item in ranked:
        if (
            len(selected)
            >= MAX_REPLACEMENTS
        ):
            break

        recommendation = (
            item.get(
                "recommendation"
            )
            or ""
        )

        confidence = float(
            item.get(
                "confidence",
                0
            )
        )

        if confidence < 65:
            continue

        if recommendation == (
            "KEEP_CURRENT"
        ):
            continue

        if recommendation == (
            "STRONG_REPLACEMENT_CANDIDATE"
        ):
            if (
                strong_count
                >= MAX_STRONG_CHANGES
            ):
                continue

            strong_count += 1

        selected.append(
            item
        )

    return {
        "version":
            VERSION,

        "max_replacements":
            MAX_REPLACEMENTS,

        "max_strong_changes":
            MAX_STRONG_CHANGES,

        "selected":
            selected,

        "selected_scenes":
            [
                item.get(
                    "scene"
                )
                for item
                in selected
            ],

        "selected_count":
            len(selected),
    }


def self_test():
    sample = [
        {
            "scene": 1,
            "priority_score": 100,
            "recommendation":
                "STRONG_REPLACEMENT_CANDIDATE",
            "confidence": 90,
        }
        for _ in range(10)
    ]

    result = allocate(
        sample
    )

    assert (
        result["selected_count"]
        <= MAX_REPLACEMENTS
    )

    print(
        "VI8.23 REPLACEMENT BUDGET=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.24 — GLOBAL REGRESSION GUARD
# =====================================================

cat > vi8_24_global_regression_guard.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.24"


def evaluate(
    vi8_cinematic,
    selection_plan,
    budget
):
    blockers = []
    warnings = []

    old_forecast = float(
        vi8_cinematic.get(
            "forecast_score",
            0
        )
        or 0
    )

    selected_count = int(
        budget.get(
            "selected_count",
            0
        )
        or 0
    )

    continuity = (
        selection_plan.get(
            "continuity"
        )
        or {}
    )

    continuity_warnings = int(
        continuity.get(
            "count",
            0
        )
        or 0
    )

    if old_forecast < 75:
        blockers.append(
            "cinematic_baseline_too_low"
        )

    if selected_count > 6:
        blockers.append(
            "replacement_budget_exceeded"
        )

    if continuity_warnings >= 4:
        warnings.append(
            "media_continuity_risk"
        )

    if (
        vi8_cinematic.get(
            "blockers"
        )
        or []
    ):
        blockers.append(
            "existing_cinematic_blocker"
        )

    return {
        "version":
            VERSION,

        "status":
            (
                "HOLD"
                if blockers
                else (
                    "PASS_WITH_WARNINGS"
                    if warnings
                    else "PASS"
                )
            ),

        "baseline_forecast":
            old_forecast,

        "planned_changes":
            selected_count,

        "blockers":
            blockers,

        "warnings":
            warnings,
    }


def self_test():
    result = evaluate(
        {
            "forecast_score": 94,
            "blockers": [],
        },
        {
            "continuity": {
                "count": 0
            }
        },
        {
            "selected_count": 4
        }
    )

    assert result["status"] == "PASS"

    print(
        "VI8.24 GLOBAL REGRESSION GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.25 — CINEMATIC MEDIA MERGER
# =====================================================

cat > vi8_25_cinematic_media_merger.py <<'PY'
#!/usr/bin/env python3

from vi8_21_improvement_priority import (
    priority
)

from vi8_22_selection_confidence import (
    evaluate as confidence
)

VERSION = "8.25"


def merge(
    media_plan,
    cinematic_plans
):
    cinematic_by_scene = {
        item.get("scene"):
            item

        for item
        in cinematic_plans
    }

    merged = []

    selections = (
        media_plan.get(
            "selections"
        )
        or []
    )

    for selection in selections:
        scene = selection.get(
            "scene"
        )

        cinematic = (
            cinematic_by_scene.get(
                scene
            )
            or {}
        )

        p = priority(
            selection,
            cinematic
        )

        c = confidence(
            selection
        )

        comparison = (
            selection.get(
                "comparison"
            )
            or {}
        )

        winner = (
            selection.get(
                "winner"
            )
            or {}
        )

        winner_candidate = (
            winner.get(
                "candidate"
            )
            or {}
        )

        merged.append({
            "scene":
                scene,

            "category":
                selection.get(
                    "category"
                ),

            "current_score":
                (
                    selection.get(
                        "current"
                    )
                    or {}
                ).get(
                    "score"
                ),

            "winner_score":
                winner.get(
                    "score"
                ),

            "winner_shot":
                winner_candidate.get(
                    "shot"
                ),

            "winner_source":
                winner_candidate.get(
                    "source"
                ),

            "delta":
                comparison.get(
                    "delta"
                ),

            "recommendation":
                comparison.get(
                    "recommendation"
                ),

            "priority_score":
                p.get(
                    "priority_score"
                ),

            "priority_reasons":
                p.get(
                    "reasons"
                ),

            "confidence":
                c.get(
                    "confidence"
                ),

            "confidence_level":
                c.get(
                    "level"
                ),

            "cinematic_shot_match":
                cinematic.get(
                    "shot_match"
                ),

            "cinematic_motion":
                cinematic.get(
                    "motion"
                ),

            "cinematic_status":
                cinematic.get(
                    "status"
                ),
        })

    return {
        "version":
            VERSION,

        "items":
            merged,
    }


def self_test():
    assert VERSION == "8.25"

    print(
        "VI8.25 CINEMATIC MEDIA MERGER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.26 — CHANGE PLAN BUILDER
# =====================================================

cat > vi8_26_change_plan_builder.py <<'PY'
#!/usr/bin/env python3

from vi8_23_replacement_budget import (
    allocate
)

VERSION = "8.26"


def build(merged):
    items = (
        merged.get("items")
        or []
    )

    budget_input = []

    for item in items:
        budget_input.append({
            "scene":
                item.get(
                    "scene"
                ),

            "priority_score":
                item.get(
                    "priority_score"
                ),

            "recommendation":
                item.get(
                    "recommendation"
                ),

            "confidence":
                item.get(
                    "confidence"
                ),

            "category":
                item.get(
                    "category"
                ),

            "winner_shot":
                item.get(
                    "winner_shot"
                ),

            "winner_source":
                item.get(
                    "winner_source"
                ),

            "delta":
                item.get(
                    "delta"
                ),
        })

    budget = allocate(
        budget_input
    )

    return {
        "version":
            VERSION,

        "budget":
            budget,

        "planned_changes":
            budget.get(
                "selected"
            )
            or [],

        "planned_change_count":
            budget.get(
                "selected_count"
            ),
    }


def self_test():
    result = build({
        "items": []
    })

    assert (
        result[
            "planned_change_count"
        ]
        == 0
    )

    print(
        "VI8.26 CHANGE PLAN BUILDER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.27 — ACTIVATION SAFETY CONTRACT
# =====================================================

cat > vi8_27_activation_safety_contract.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.27"


def evaluate():
    return {
        "version":
            VERSION,

        "mode":
            "SHADOW_ONLY",

        "automatic_download":
            False,

        "automatic_media_replace":
            False,

        "filesystem_media_mutation":
            False,

        "renderer_activation":
            False,

        "ffmpeg_allowed":
            False,

        "source_recovery":
            "SHADOW_ONLY",

        "full_active":
            False,

        "status":
            "LOCKED_SAFE",
    }


def self_test():
    result = evaluate()

    assert (
        result[
            "ffmpeg_allowed"
        ]
        is False
    )

    assert (
        result[
            "automatic_media_replace"
        ]
        is False
    )

    print(
        "VI8.27 ACTIVATION SAFETY CONTRACT=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.28 — INTEGRATION READINESS
# =====================================================

cat > vi8_28_integration_readiness.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.28"


def evaluate(
    cinematic,
    selection_audit,
    regression,
    change_plan
):
    blockers = []
    warnings = []

    blockers.extend(
        cinematic.get(
            "blockers"
        )
        or []
    )

    blockers.extend(
        selection_audit.get(
            "blockers"
        )
        or []
    )

    blockers.extend(
        regression.get(
            "blockers"
        )
        or []
    )

    warnings.extend(
        cinematic.get(
            "warnings"
        )
        or []
    )

    warnings.extend(
        selection_audit.get(
            "warnings"
        )
        or []
    )

    warnings.extend(
        regression.get(
            "warnings"
        )
        or []
    )

    planned = int(
        change_plan.get(
            "planned_change_count",
            0
        )
        or 0
    )

    if planned == 0:
        warnings.append(
            "no_media_changes_selected"
        )

    blockers = sorted(
        set(blockers)
    )

    warnings = sorted(
        set(warnings)
    )

    if blockers:
        status = "HOLD"

    elif planned > 0:
        status = (
            "READY_FOR_MEDIA_INTEGRATION_PREVIEW"
        )

    else:
        status = (
            "SAFE_NO_CHANGE_REQUIRED"
        )

    return {
        "version":
            VERSION,

        "status":
            status,

        "planned_changes":
            planned,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "real_media_mutation":
            False,

        "renderer_activation":
            False,
    }


def self_test():
    result = evaluate(
        {
            "blockers": [],
            "warnings": [],
        },
        {
            "blockers": [],
            "warnings": [],
        },
        {
            "blockers": [],
            "warnings": [],
        },
        {
            "planned_change_count": 2
        }
    )

    assert (
        result["status"]
        == "READY_FOR_MEDIA_INTEGRATION_PREVIEW"
    )

    print(
        "VI8.28 INTEGRATION READINESS=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.29 — MASTER CERTIFICATION
# =====================================================

cat > vi8_29_master_certification.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.29"


def evaluate(
    readiness,
    safety,
    cinematic_score
):
    blockers = (
        readiness.get(
            "blockers"
        )
        or []
    )

    warnings = (
        readiness.get(
            "warnings"
        )
        or []
    )

    safety_ok = (
        safety.get(
            "status"
        )
        == "LOCKED_SAFE"
    )

    if not safety_ok:
        blockers = list(
            blockers
        ) + [
            "activation_safety_not_locked"
        ]

    blockers = sorted(
        set(blockers)
    )

    if blockers:
        status = "HOLD"

    elif (
        readiness.get(
            "status"
        )
        == "READY_FOR_MEDIA_INTEGRATION_PREVIEW"
        and float(
            cinematic_score
            or 0
        ) >= 85
    ):
        status = (
            "CINEMATIC_MEDIA_SHADOW_CERTIFIED"
        )

    else:
        status = (
            "CINEMATIC_MEDIA_SHADOW_SAFE"
        )

    return {
        "version":
            VERSION,

        "status":
            status,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "shadow_certified":
            (
                status
                == "CINEMATIC_MEDIA_SHADOW_CERTIFIED"
            ),

        "real_media_activation":
            False,

        "full_active_authorized":
            False,
    }


def self_test():
    result = evaluate(
        {
            "status":
                "READY_FOR_MEDIA_INTEGRATION_PREVIEW",
            "blockers": [],
            "warnings": [],
        },
        {
            "status":
                "LOCKED_SAFE"
        },
        94
    )

    assert (
        result[
            "shadow_certified"
        ]
        is True
    )

    print(
        "VI8.29 MASTER CERTIFICATION=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.30 — MASTER MEDIA CINEMATIC GATE
# =====================================================

cat > vi8_30_master_media_cinematic_gate.py <<'PY'
#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path

from vi8_00_master_cinematic_gate import (
    evaluate as cinematic_gate
)

from vi8_20_media_selection_shadow_gate import (
    evaluate as media_gate
)

from vi8_25_cinematic_media_merger import (
    merge
)

from vi8_26_change_plan_builder import (
    build as build_change_plan
)

from vi8_24_global_regression_guard import (
    evaluate as regression_guard
)

from vi8_27_activation_safety_contract import (
    evaluate as safety_contract
)

from vi8_28_integration_readiness import (
    evaluate as readiness_gate
)

from vi8_29_master_certification import (
    evaluate as certification_gate
)


VERSION = "8.30"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    cinematic = cinematic_gate()

    media = media_gate()

    media_plan = (
        media.get("plan")
        or {}
    )

    cinematic_plans = (
        cinematic.get("plans")
        or []
    )

    merged = merge(
        media_plan,
        cinematic_plans
    )

    change_plan = (
        build_change_plan(
            merged
        )
    )

    regression = (
        regression_guard(
            cinematic,
            media_plan,
            change_plan.get(
                "budget"
            )
            or {}
        )
    )

    safety = (
        safety_contract()
    )

    readiness = (
        readiness_gate(
            cinematic,
            media.get(
                "audit"
            )
            or {},
            regression,
            change_plan
        )
    )

    certification = (
        certification_gate(
            readiness,
            safety,
            cinematic.get(
                "forecast_score"
            )
        )
    )

    result = {
        "version":
            VERSION,

        "status":
            certification.get(
                "status"
            ),

        "short_id":
            cinematic.get(
                "short_id"
            ),

        "cinematic_score":
            cinematic.get(
                "forecast_score"
            ),

        "cinematic_level":
            cinematic.get(
                "forecast_level"
            ),

        "cinematic_status":
            cinematic.get(
                "status"
            ),

        "media_status":
            media.get(
                "status"
            ),

        "merged":
            merged,

        "change_plan":
            change_plan,

        "regression_guard":
            regression,

        "readiness":
            readiness,

        "safety":
            safety,

        "blockers":
            certification.get(
                "blockers"
            ),

        "warnings":
            certification.get(
                "warnings"
            ),

        "shadow_certified":
            certification.get(
                "shadow_certified"
            ),

        "automatic_download":
            False,

        "automatic_media_replace":
            False,

        "renderer_activation":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "source_recovery":
            "SHADOW_ONLY",

        "full_active_authorized":
            False,
    }

    output = (
        BASE
        / "logs"
        / "producao"
        / "vi8_30_master_media_cinematic_gate_latest.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.write_text(
        json.dumps(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "gate":
                    result,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return result


def self_test():
    assert VERSION == "8.30"

    print(
        "VI8.30 MASTER MEDIA CINEMATIC GATE=PASS"
    )


if __name__ == "__main__":
    result = evaluate()

    print()
    print(
        "======================================"
    )
    print(
        " VI8.30 MASTER MEDIA CINEMATIC GATE"
    )
    print(
        "======================================"
    )

    print(
        "STATUS:",
        result.get("status")
    )

    print(
        "SHORT ID:",
        result.get("short_id")
    )

    print(
        "CINEMATIC SCORE:",
        result.get(
            "cinematic_score"
        )
    )

    print(
        "CINEMATIC LEVEL:",
        result.get(
            "cinematic_level"
        )
    )

    print(
        "CINEMATIC STATUS:",
        result.get(
            "cinematic_status"
        )
    )

    print(
        "MEDIA STATUS:",
        result.get(
            "media_status"
        )
    )

    change_plan = (
        result.get(
            "change_plan"
        )
        or {}
    )

    print(
        "PLANNED CHANGES:",
        change_plan.get(
            "planned_change_count"
        )
    )

    print(
        "PLANNED SCENES:",
        (
            change_plan.get(
                "budget"
            )
            or {}
        ).get(
            "selected_scenes"
        )
    )

    regression = (
        result.get(
            "regression_guard"
        )
        or {}
    )

    print(
        "REGRESSION GUARD:",
        regression.get(
            "status"
        )
    )

    print(
        "BLOCKERS:",
        result.get(
            "blockers"
        )
    )

    print(
        "WARNINGS:",
        result.get(
            "warnings"
        )
    )

    print(
        "SHADOW CERTIFIED:",
        result.get(
            "shadow_certified"
        )
    )

    print()
    print(
        "===== PRIORITIZED MEDIA CHANGES ====="
    )

    merged = (
        result.get(
            "merged"
        )
        or {}
    )

    items = sorted(
        merged.get(
            "items"
        )
        or [],
        key=lambda item:
            item.get(
                "priority_score",
                0
            ),
        reverse=True
    )

    for item in items:
        print(
            "SCENE",
            item.get(
                "scene"
            ),
            "| category=",
            item.get(
                "category"
            ),
            "| current=",
            item.get(
                "current_score"
            ),
            "| winner=",
            item.get(
                "winner_score"
            ),
            "| delta=",
            item.get(
                "delta"
            ),
            "| shot=",
            item.get(
                "winner_shot"
            ),
            "| priority=",
            item.get(
                "priority_score"
            ),
            "| confidence=",
            item.get(
                "confidence"
            ),
            item.get(
                "confidence_level"
            ),
            "| recommendation=",
            item.get(
                "recommendation"
            ),
        )

    print()
    print(
        "AUTOMATIC DOWNLOAD:",
        result.get(
            "automatic_download"
        )
    )

    print(
        "AUTOMATIC MEDIA REPLACE:",
        result.get(
            "automatic_media_replace"
        )
    )

    print(
        "RENDERER ACTIVATION:",
        result.get(
            "renderer_activation"
        )
    )

    print(
        "FFMPEG EXECUTED:",
        result.get(
            "ffmpeg_executed"
        )
    )

    print(
        "VIDEO GENERATED:",
        result.get(
            "video_generated"
        )
    )

    print(
        "SOURCE RECOVERY:",
        result.get(
            "source_recovery"
        )
    )

    print(
        "FULL ACTIVE AUTHORIZED:",
        result.get(
            "full_active_authorized"
        )
    )
PY


# =====================================================
# COMPILE
# =====================================================

echo
echo "===== COMPILE ====="

python -m py_compile \
  vi8_21_improvement_priority.py \
  vi8_22_selection_confidence.py \
  vi8_23_replacement_budget.py \
  vi8_24_global_regression_guard.py \
  vi8_25_cinematic_media_merger.py \
  vi8_26_change_plan_builder.py \
  vi8_27_activation_safety_contract.py \
  vi8_28_integration_readiness.py \
  vi8_29_master_certification.py \
  vi8_30_master_media_cinematic_gate.py \
  || exit 10

echo "COMPILE=PASS"


# =====================================================
# SELF TESTS
# =====================================================

echo
echo "===== SELF TESTS ====="

python vi8_21_improvement_priority.py || exit 11
python vi8_22_selection_confidence.py || exit 12
python vi8_23_replacement_budget.py || exit 13
python vi8_24_global_regression_guard.py || exit 14
python vi8_25_cinematic_media_merger.py || exit 15
python vi8_26_change_plan_builder.py || exit 16
python vi8_27_activation_safety_contract.py || exit 17
python vi8_28_integration_readiness.py || exit 18
python vi8_29_master_certification.py || exit 19

echo "SELF TESTS=PASS"


# =====================================================
# CORE SAFETY BEFORE ANALYSIS
# =====================================================

VIDEO_MID="$(sha256sum video.py | awk '{print $1}')"
GERAR_MID="$(sha256sum gerar_short.sh | awk '{print $1}')"

if [ "$VIDEO_BEFORE" != "$VIDEO_MID" ]; then
    echo "CRITICAL: video.py changed"
    exit 30
fi

if [ "$GERAR_BEFORE" != "$GERAR_MID" ]; then
    echo "CRITICAL: gerar_short.sh changed"
    exit 31
fi

echo
echo "CORE FILES UNCHANGED=YES"


# =====================================================
# VI8.30 REAL SHADOW MASTER ANALYSIS
# =====================================================

echo
echo "======================================"
echo " VI8.30 REAL SHADOW ANALYSIS"
echo "======================================"
echo
echo "NO VIDEO WILL BE GENERATED."
echo

python vi8_30_master_media_cinematic_gate.py || exit 40


# =====================================================
# FINAL CORE SAFETY
# =====================================================

VIDEO_FINAL="$(sha256sum video.py | awk '{print $1}')"
GERAR_FINAL="$(sha256sum gerar_short.sh | awk '{print $1}')"

echo
echo "===== FINAL CORE INTEGRITY ====="

echo "VIDEO BEFORE=$VIDEO_BEFORE"
echo "VIDEO FINAL =$VIDEO_FINAL"

echo
echo "GERAR BEFORE=$GERAR_BEFORE"
echo "GERAR FINAL =$GERAR_FINAL"

if [ "$VIDEO_BEFORE" != "$VIDEO_FINAL" ]; then
    echo "CRITICAL: video.py changed"
    exit 50
fi

if [ "$GERAR_BEFORE" != "$GERAR_FINAL" ]; then
    echo "CRITICAL: gerar_short.sh changed"
    exit 51
fi

echo
echo "VIDEO.PY UNCHANGED=YES"
echo "GERAR_SHORT.SH UNCHANGED=YES"
echo "VIDEO GENERATED=NO"
echo "FFMPEG EXECUTED=NO"
echo "DOWNLOAD EXECUTED=NO"
echo "MEDIA REPLACEMENT=NO"
echo "RENDERER MODIFIED=NO"
echo "SOURCE RECOVERY=SHADOW_ONLY"
echo "FULL ACTIVE=LOCKED"

echo
echo "======================================"
echo " VI8.01 -> VI8.30 COMPLETE"
echo "======================================"
echo
echo "INTELLIGENT MEDIA SELECTION=READY"
echo "CINEMATIC + MEDIA MERGER=READY"
echo "PRIORITY ENGINE=READY"
echo "CONFIDENCE ENGINE=READY"
echo "REPLACEMENT BUDGET=READY"
echo "GLOBAL REGRESSION GUARD=READY"
echo "ACTIVATION SAFETY=LOCKED"
echo
echo "REPORT:"
echo "logs/producao/vi8_30_master_media_cinematic_gate_latest.json"
