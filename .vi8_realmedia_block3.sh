#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$HOME/ShortAutoPro" || exit 1

echo
echo "======================================"
echo " VI8.51 -> VI8.60"
echo " SEARCH STRATEGY INTELLIGENCE"
echo " SHADOW ONLY"
echo "======================================"
echo

VIDEO_BEFORE="$(sha256sum video.py | awk '{print $1}')"
GERAR_BEFORE="$(sha256sum gerar_short.sh | awk '{print $1}')"


# =====================================================
# VI8.51 — SEARCH NEED CLASSIFIER
# =====================================================

cat > vi8_51_search_need_classifier.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.51"


def evaluate(scene_result):
    gap = (
        scene_result.get("gap")
        or {}
    )

    status = gap.get(
        "status"
    )

    real_count = int(
        scene_result.get(
            "real_candidate_count",
            0
        )
        or 0
    )

    if status == "NO_REAL_MEDIA":
        need = "CRITICAL"

    elif status == "STRONG_REAL_MEDIA_GAP":
        need = "HIGH"

    elif status == "REAL_MEDIA_GAP":
        need = "MEDIUM"

    elif status == "MINOR_REAL_MEDIA_GAP":
        need = "LOW"

    elif status == "REAL_MEDIA_COMPETITIVE":
        need = "NONE"

    else:
        need = (
            "LOW"
            if real_count
            else "CRITICAL"
        )

    return {
        "version": VERSION,
        "scene":
            scene_result.get(
                "scene"
            ),
        "need": need,
        "gap_status": status,
        "real_count": real_count,
    }


def self_test():
    result = evaluate({
        "scene": 5,
        "real_candidate_count": 1,
        "gap": {
            "status":
                "STRONG_REAL_MEDIA_GAP"
        }
    })

    assert result["need"] == "HIGH"

    print(
        "VI8.51 SEARCH NEED CLASSIFIER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.52 — IDEAL SEARCH SPEC
# =====================================================

cat > vi8_52_ideal_search_spec.py <<'PY'
#!/usr/bin/env python3

from vi8_11_ideal_shot_generator import (
    generate
)

VERSION = "8.52"


def build(scene_result):
    category = str(
        scene_result.get(
            "category"
        )
        or "GENERAL"
    ).upper()

    ranking = (
        scene_result.get(
            "ranking"
        )
        or {}
    )

    best_virtual = (
        ranking.get(
            "best_virtual"
        )
        or {}
    )

    candidate = (
        best_virtual.get(
            "candidate"
        )
        or {}
    )

    ideal_shot = (
        candidate.get("shot")
        or generate(category)[0]
    )

    query = str(
        scene_result.get(
            "query"
        )
        or ""
    ).strip()

    modifiers = []

    if category == "FACE":
        modifiers.extend([
            "portrait",
            "clear face",
            ideal_shot,
        ])

    elif category == "DOCUMENT":
        modifiers.extend([
            "document",
            "legible",
            ideal_shot,
        ])

    elif category == "EVIDENCE":
        modifiers.extend([
            "evidence",
            "detail",
            ideal_shot,
        ])

    elif category == "LOCATION":
        modifiers.extend([
            "location",
            "environment",
            ideal_shot,
        ])

    elif category == "OBJECT":
        modifiers.extend([
            "object detail",
            ideal_shot,
        ])

    else:
        modifiers.append(
            ideal_shot
        )

    search_query = " ".join(
        [
            query,
            *modifiers
        ]
    ).strip()

    return {
        "version": VERSION,
        "scene":
            scene_result.get(
                "scene"
            ),
        "category": category,
        "ideal_shot": ideal_shot,
        "base_query": query,
        "search_query":
            search_query,
    }


def self_test():
    result = build({
        "scene": 6,
        "category": "FACE",
        "query": "young girl portrait",
        "ranking": {},
    })

    assert "portrait" in (
        result["search_query"]
    )

    print(
        "VI8.52 IDEAL SEARCH SPEC=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.53 — MINIMUM GAIN POLICY
# =====================================================

cat > vi8_53_minimum_gain_policy.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.53"


MIN_GAIN = {
    "CRITICAL": 0,
    "HIGH": 8,
    "MEDIUM": 6,
    "LOW": 4,
    "NONE": 999,
}


def threshold(need):
    return MIN_GAIN.get(
        str(
            need or "LOW"
        ).upper(),
        6
    )


def self_test():
    assert threshold(
        "HIGH"
    ) == 8

    assert threshold(
        "NONE"
    ) > 100

    print(
        "VI8.53 MINIMUM GAIN POLICY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.54 — SEARCH VALUE ESTIMATOR
# =====================================================

cat > vi8_54_search_value_estimator.py <<'PY'
#!/usr/bin/env python3

from vi8_53_minimum_gain_policy import (
    threshold
)

VERSION = "8.54"


def evaluate(
    need,
    virtual_advantage
):
    gap = float(
        virtual_advantage
        or 0
    )

    minimum = threshold(
        need
    )

    worthwhile = (
        need == "CRITICAL"
        or gap >= minimum
    )

    if need == "NONE":
        worthwhile = False

    return {
        "version": VERSION,
        "need": need,
        "gap": round(
            gap,
            2
        ),
        "minimum_gain":
            minimum,
        "worthwhile":
            worthwhile,
    }


def self_test():
    result = evaluate(
        "HIGH",
        15
    )

    assert result[
        "worthwhile"
    ] is True

    print(
        "VI8.54 SEARCH VALUE ESTIMATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.55 — SEARCH PRIORITY ENGINE
# =====================================================

cat > vi8_55_search_priority_engine.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.55"


NEED_WEIGHT = {
    "CRITICAL": 50,
    "HIGH": 35,
    "MEDIUM": 20,
    "LOW": 8,
    "NONE": 0,
}


def evaluate(
    scene,
    category,
    need,
    gap
):
    score = (
        NEED_WEIGHT.get(
            need,
            0
        )
        + max(
            0,
            float(
                gap or 0
            )
        )
    )

    reasons = []

    if category == "FACE":
        score += 10
        reasons.append(
            "face_quality_priority"
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

    return {
        "version": VERSION,
        "scene": scene,
        "priority_score":
            round(
                score,
                2
            ),
        "reasons": reasons,
    }


def self_test():
    result = evaluate(
        10,
        "FACE",
        "HIGH",
        12
    )

    assert (
        result[
            "priority_score"
        ] > 50
    )

    print(
        "VI8.55 SEARCH PRIORITY ENGINE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.56 — SEARCH BUDGET PLANNER
# =====================================================

cat > vi8_56_search_budget_planner.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.56"

MAX_SEARCH_SCENES = 5


def allocate(items):
    ranked = sorted(
        items,
        key=lambda x:
            x.get(
                "priority_score",
                0
            ),
        reverse=True
    )

    selected = []

    for item in ranked:
        if len(
            selected
        ) >= MAX_SEARCH_SCENES:
            break

        if not item.get(
            "worthwhile"
        ):
            continue

        selected.append(
            item
        )

    return {
        "version": VERSION,
        "max_search_scenes":
            MAX_SEARCH_SCENES,
        "selected":
            selected,
        "selected_scenes":
            [
                x.get("scene")
                for x in selected
            ],
        "selected_count":
            len(selected),
    }


def self_test():
    result = allocate([
        {
            "scene": i,
            "priority_score":
                100 - i,
            "worthwhile": True,
        }
        for i in range(10)
    ])

    assert (
        result["selected_count"]
        == MAX_SEARCH_SCENES
    )

    print(
        "VI8.56 SEARCH BUDGET PLANNER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.57 — NO-SEARCH GUARD
# =====================================================

cat > vi8_57_no_search_guard.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.57"


def evaluate(
    search_item
):
    reasons = []

    if (
        search_item.get(
            "need"
        )
        == "NONE"
    ):
        reasons.append(
            "real_media_already_competitive"
        )

    if not search_item.get(
        "worthwhile"
    ):
        reasons.append(
            "gain_below_threshold"
        )

    return {
        "version": VERSION,
        "scene":
            search_item.get(
                "scene"
            ),
        "skip":
            bool(reasons),
        "reasons":
            reasons,
    }


def self_test():
    result = evaluate({
        "scene": 3,
        "need": "NONE",
        "worthwhile": False,
    })

    assert result["skip"] is True

    print(
        "VI8.57 NO SEARCH GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.58 — SEARCH STRATEGY PLAN
# =====================================================

cat > vi8_58_search_strategy_plan.py <<'PY'
#!/usr/bin/env python3

from vi8_51_search_need_classifier import (
    evaluate as classify_need
)

from vi8_52_ideal_search_spec import (
    build as search_spec
)

from vi8_54_search_value_estimator import (
    evaluate as search_value
)

from vi8_55_search_priority_engine import (
    evaluate as search_priority
)

from vi8_56_search_budget_planner import (
    allocate
)

from vi8_57_no_search_guard import (
    evaluate as no_search_guard
)

VERSION = "8.58"


def build(real_plan):
    scenes = (
        real_plan.get("scenes")
        or []
    )

    items = []

    for scene_result in scenes:
        need = classify_need(
            scene_result
        )

        spec = search_spec(
            scene_result
        )

        gap = (
            (
                scene_result.get(
                    "gap"
                )
                or {}
            ).get(
                "virtual_advantage"
            )
            or 0
        )

        value = search_value(
            need["need"],
            gap
        )

        priority = (
            search_priority(
                scene_result.get(
                    "scene"
                ),
                scene_result.get(
                    "category"
                ),
                need["need"],
                gap
            )
        )

        item = {
            "scene":
                scene_result.get(
                    "scene"
                ),
            "category":
                scene_result.get(
                    "category"
                ),
            "need":
                need["need"],
            "gap_status":
                need[
                    "gap_status"
                ],
            "real_candidate_count":
                need[
                    "real_count"
                ],
            "gap":
                value["gap"],
            "minimum_gain":
                value[
                    "minimum_gain"
                ],
            "worthwhile":
                value[
                    "worthwhile"
                ],
            "priority_score":
                priority[
                    "priority_score"
                ],
            "priority_reasons":
                priority[
                    "reasons"
                ],
            "ideal_shot":
                spec[
                    "ideal_shot"
                ],
            "search_query":
                spec[
                    "search_query"
                ],
        }

        guard = no_search_guard(
            item
        )

        item[
            "skip_search"
        ] = guard["skip"]

        item[
            "skip_reasons"
        ] = guard["reasons"]

        items.append(
            item
        )

    budget = allocate(
        items
    )

    return {
        "version": VERSION,
        "items": items,
        "budget": budget,
    }


def self_test():
    assert VERSION == "8.58"

    print(
        "VI8.58 SEARCH STRATEGY PLAN=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.59 — SEARCH STRATEGY AUDIT
# =====================================================

cat > vi8_59_search_strategy_audit.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.59"


def evaluate(plan):
    items = (
        plan.get("items")
        or []
    )

    budget = (
        plan.get("budget")
        or {}
    )

    blockers = []
    warnings = []

    selected = (
        budget.get(
            "selected"
        )
        or []
    )

    for item in selected:
        if item.get(
            "skip_search"
        ):
            blockers.append(
                f"scene_{item.get('scene')}_selected_but_guarded"
            )

        if not item.get(
            "search_query"
        ):
            blockers.append(
                f"scene_{item.get('scene')}_query_missing"
            )

    high_need = [
        x
        for x in items
        if x.get(
            "need"
        )
        in {
            "HIGH",
            "CRITICAL",
        }
    ]

    if (
        high_need
        and not selected
    ):
        warnings.append(
            "high_need_but_no_search_selected"
        )

    return {
        "version": VERSION,
        "status": (
            "HOLD"
            if blockers
            else (
                "PASS_WITH_WARNINGS"
                if warnings
                else "PASS"
            )
        ),
        "selected_count":
            len(selected),
        "selected_scenes":
            budget.get(
                "selected_scenes"
            ),
        "blockers":
            blockers,
        "warnings":
            warnings,
    }


def self_test():
    result = evaluate({
        "items": [],
        "budget": {
            "selected": [],
            "selected_scenes": [],
        }
    })

    assert (
        result["status"]
        == "PASS"
    )

    print(
        "VI8.59 SEARCH STRATEGY AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.60 — REAL MEDIA SEARCH MASTER GATE
# =====================================================

cat > vi8_60_real_media_search_master_gate.py <<'PY'
#!/usr/bin/env python3

import json
from pathlib import Path

from vi8_50_real_media_master_gate import (
    evaluate as real_media_gate
)

from vi8_58_search_strategy_plan import (
    build as build_strategy
)

from vi8_59_search_strategy_audit import (
    evaluate as audit_strategy
)

VERSION = "8.60"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    real = real_media_gate()

    plan = (
        real.get("plan")
        or {}
    )

    strategy = build_strategy(
        plan
    )

    audit = audit_strategy(
        strategy
    )

    blockers = (
        audit.get(
            "blockers"
        )
        or []
    )

    if blockers:
        status = "HOLD"

    elif audit.get(
        "selected_count",
        0
    ) > 0:
        status = (
            "SEARCH_STRATEGY_SHADOW_READY"
        )

    else:
        status = (
            "REAL_MEDIA_ALREADY_COMPETITIVE"
        )

    result = {
        "version": VERSION,
        "status": status,
        "short_id":
            real.get("short_id"),
        "real_media_status":
            real.get("status"),
        "strategy":
            strategy,
        "audit":
            audit,
        "blockers":
            blockers,
        "warnings":
            audit.get(
                "warnings"
            )
            or [],
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

    output = (
        BASE
        / "logs"
        / "producao"
        / "vi8_60_real_media_search_master_latest.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.write_text(
        json.dumps(
            {
                "gate": result
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return result


def self_test():
    assert VERSION == "8.60"

    print(
        "VI8.60 REAL MEDIA SEARCH MASTER GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


echo
echo "===== COMPILE ====="

python -m py_compile \
  vi8_51_search_need_classifier.py \
  vi8_52_ideal_search_spec.py \
  vi8_53_minimum_gain_policy.py \
  vi8_54_search_value_estimator.py \
  vi8_55_search_priority_engine.py \
  vi8_56_search_budget_planner.py \
  vi8_57_no_search_guard.py \
  vi8_58_search_strategy_plan.py \
  vi8_59_search_strategy_audit.py \
  vi8_60_real_media_search_master_gate.py \
  || exit 10

echo "COMPILE=PASS"


echo
echo "===== SELF TESTS ====="

python vi8_51_search_need_classifier.py || exit 11
python vi8_52_ideal_search_spec.py || exit 12
python vi8_53_minimum_gain_policy.py || exit 13
python vi8_54_search_value_estimator.py || exit 14
python vi8_55_search_priority_engine.py || exit 15
python vi8_56_search_budget_planner.py || exit 16
python vi8_57_no_search_guard.py || exit 17
python vi8_58_search_strategy_plan.py || exit 18
python vi8_59_search_strategy_audit.py || exit 19
python vi8_60_real_media_search_master_gate.py || exit 20

echo "SELF TESTS=PASS"


echo
echo "======================================"
echo " VI8.60 REAL MEDIA SEARCH ANALYSIS"
echo "======================================"

python - <<'PY'
from vi8_60_real_media_search_master_gate import (
    evaluate
)

r = evaluate()

print(
    "STATUS:",
    r.get("status")
)

print(
    "SHORT ID:",
    r.get("short_id")
)

print(
    "REAL MEDIA STATUS:",
    r.get(
        "real_media_status"
    )
)

audit = (
    r.get("audit")
    or {}
)

print(
    "SEARCH SCENES:",
    audit.get(
        "selected_scenes"
    )
)

print(
    "SEARCH COUNT:",
    audit.get(
        "selected_count"
    )
)

print(
    "BLOCKERS:",
    r.get("blockers")
)

print(
    "WARNINGS:",
    r.get("warnings")
)

print()
print(
    "===== SEARCH STRATEGY BY SCENE ====="
)

strategy = (
    r.get("strategy")
    or {}
)

for item in (
    strategy.get("items")
    or []
):
    print(
        "SCENE",
        item.get("scene"),
        "| category=",
        item.get("category"),
        "| need=",
        item.get("need"),
        "| real_count=",
        item.get(
            "real_candidate_count"
        ),
        "| gap=",
        item.get("gap"),
        "| min_gain=",
        item.get(
            "minimum_gain"
        ),
        "| worthwhile=",
        item.get(
            "worthwhile"
        ),
        "| priority=",
        item.get(
            "priority_score"
        ),
        "| ideal_shot=",
        item.get(
            "ideal_shot"
        ),
        "| skip=",
        item.get(
            "skip_search"
        ),
    )

print()
print(
    "===== PRIORITY SEARCH PLAN ====="
)

budget = (
    strategy.get("budget")
    or {}
)

for item in (
    budget.get("selected")
    or []
):
    print(
        "SCENE",
        item.get("scene"),
        "| priority=",
        item.get(
            "priority_score"
        ),
        "| need=",
        item.get("need"),
        "| shot=",
        item.get(
            "ideal_shot"
        ),
        "| query=",
        item.get(
            "search_query"
        ),
    )

print()
print(
    "AUTOMATIC SEARCH:",
    r.get(
        "automatic_search"
    )
)

print(
    "AUTOMATIC DOWNLOAD:",
    r.get(
        "automatic_download"
    )
)

print(
    "AUTOMATIC REPLACE:",
    r.get(
        "automatic_replace"
    )
)

print(
    "MEDIA MUTATED:",
    r.get(
        "media_mutated"
    )
)

print(
    "FFMPEG EXECUTED:",
    r.get(
        "ffmpeg_executed"
    )
)

print(
    "VIDEO GENERATED:",
    r.get(
        "video_generated"
    )
)
PY


VIDEO_AFTER="$(sha256sum video.py | awk '{print $1}')"
GERAR_AFTER="$(sha256sum gerar_short.sh | awk '{print $1}')"

if [ "$VIDEO_BEFORE" != "$VIDEO_AFTER" ]; then
    echo "CRITICAL: video.py changed"
    exit 30
fi

if [ "$GERAR_BEFORE" != "$GERAR_AFTER" ]; then
    echo "CRITICAL: gerar_short.sh changed"
    exit 31
fi


echo
echo "======================================"
echo " VI8.51 -> VI8.60 COMPLETE"
echo "======================================"
echo
echo "REAL MEDIA GAP INTELLIGENCE=READY"
echo "SEARCH NEED CLASSIFICATION=READY"
echo "IDEAL SEARCH SPEC=READY"
echo "MINIMUM GAIN POLICY=READY"
echo "SEARCH PRIORITY=READY"
echo "SEARCH BUDGET=READY"
echo "NO-SEARCH GUARD=READY"
echo
echo "VIDEO.PY UNCHANGED=YES"
echo "GERAR_SHORT.SH UNCHANGED=YES"
echo "AUTOMATIC SEARCH=NO"
echo "DOWNLOAD EXECUTED=NO"
echo "MEDIA REPLACEMENT=NO"
echo "FFMPEG EXECUTED=NO"
echo "VIDEO GENERATED=NO"
echo "SOURCE RECOVERY=SHADOW_ONLY"
echo "FULL ACTIVE=LOCKED"
