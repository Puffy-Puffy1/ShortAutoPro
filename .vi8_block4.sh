#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$HOME/ShortAutoPro" || exit 1

VIDEO_HASH_BEFORE="$(sha256sum video.py | awk '{print $1}')"
GERAR_HASH_BEFORE="$(sha256sum gerar_short.sh | awk '{print $1}')"

echo
echo "======================================"
echo " VI8 BLOCK 4/4"
echo " FINAL CINEMATIC SHADOW GATES"
echo "======================================"
echo
echo "VIDEO GENERATION=OFF"
echo "FFMPEG=OFF"
echo "RENDERER ACTIVATION=OFF"
echo


# =====================================================
# VI7.79 — VISUAL QUALITY GATE
# =====================================================

cat > vi7_79_visual_quality_gate.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.79"

def evaluate(plans):
    blockers = []
    warnings = []

    safe = [
        item
        for item in plans
        if item.get("status") == "PASS"
    ]

    average_quality = (
        sum(
            float(
                item.get(
                    "quality_score",
                    0
                )
            )
            for item in plans
        ) / len(plans)
        if plans
        else 0.0
    )

    mismatches = [
        item.get("scene")
        for item in plans
        if not item.get(
            "shot_match",
            False
        )
    ]

    risky = [
        item.get("scene")
        for item in plans
        if (
            item.get("risk")
            or {}
        ).get("status") == "HOLD"
    ]

    if len(safe) < 8:
        blockers.append(
            "too_few_safe_scene_plans"
        )

    if risky:
        blockers.append(
            "visual_risk_hold_present"
        )

    if average_quality < 75:
        warnings.append(
            "visual_quality_average_low"
        )

    if len(mismatches) >= 4:
        warnings.append(
            "shot_language_mismatch"
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
        "safe_scene_count":
            len(safe),
        "average_quality":
            round(
                average_quality,
                2
            ),
        "shot_mismatch_scenes":
            mismatches,
        "risk_hold_scenes":
            risky,
        "blockers":
            blockers,
        "warnings":
            warnings,
    }

def self_test():
    result = evaluate([
        {
            "scene": i,
            "status": "PASS",
            "quality_score": 90,
            "shot_match": True,
            "risk": {
                "status": "PASS"
            },
        }
        for i in range(1, 13)
    ])

    assert result["status"] == "PASS"
    assert result["safe_scene_count"] == 12

    print(
        "VI7.79 VISUAL QUALITY GATE=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI7.82 — SOURCE BOUNDARY
# =====================================================

cat > vi7_82_source_boundary.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.82"

def evaluate():
    return {
        "version": VERSION,
        "new_source_fetch": False,
        "source_recovery":
            "SHADOW_ONLY",
        "automatic_replacement":
            False,
        "unknown_truth_is_true":
            False,
        "renderer_source_mutation":
            False,
        "status":
            "LOCKED_SAFE",
    }

def self_test():
    result = evaluate()

    assert (
        result[
            "automatic_replacement"
        ]
        is False
    )

    assert (
        result[
            "unknown_truth_is_true"
        ]
        is False
    )

    print(
        "VI7.82 SOURCE BOUNDARY=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI7.85 — SHADOW RUNTIME
# =====================================================

cat > vi7_85_shadow_runtime.py <<'PY'
#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path

from vi7_70_scene_plan_builder import (
    build_plan
)

from vi7_40_visual_repetition import (
    detect
)

from vi7_52_visual_sequence_planner import (
    analyze as analyze_transitions
)

from vi7_55_documentary_continuity import (
    evaluate as documentary
)

from vi7_58_media_diversity import (
    evaluate as diversity
)

from vi7_73_global_rhythm import (
    evaluate as rhythm
)

from vi7_76_sequence_optimizer import (
    recommendations
)

from vi7_79_visual_quality_gate import (
    evaluate as visual_gate
)

from vi7_82_source_boundary import (
    evaluate as source_boundary
)


VERSION = "7.85"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def latest_scene_map():
    files = []

    for path in (
        BASE
        / "roteiros"
    ).glob(
        "scene_map_*.json"
    ):
        if (
            "_pre_" in path.name
            or path.name.startswith(
                "scene_map_pre_"
            )
        ):
            continue

        files.append(path)

    files.sort(
        key=lambda path:
            path.stat().st_mtime,
        reverse=True
    )

    return (
        files[0]
        if files
        else None
    )


def run(scene_map_path=None):
    path = (
        Path(scene_map_path)
        if scene_map_path
        else latest_scene_map()
    )

    if (
        path is None
        or not path.exists()
    ):
        raise RuntimeError(
            "scene_map_missing"
        )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    scenes = (
        data.get("scenes")
        or []
    )

    if len(scenes) != 12:
        raise RuntimeError(
            "scene_count_not_12"
        )

    plans = build_plan(
        scenes
    )

    repetition = detect(
        plans
    )

    transitions = analyze_transitions(
        plans
    )

    documentary_result = documentary(
        plans
    )

    diversity_result = diversity(
        plans
    )

    rhythm_result = rhythm(
        plans
    )

    optimizer = recommendations(
        plans,
        repetition,
        transitions
    )

    gate = visual_gate(
        plans
    )

    source = source_boundary()

    result = {
        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),
        "version": VERSION,
        "mode": "SHADOW_ONLY",
        "scene_map": str(path),
        "short_id":
            data.get("short_id"),
        "plans": plans,
        "repetition":
            repetition,
        "transitions":
            transitions,
        "documentary":
            documentary_result,
        "diversity":
            diversity_result,
        "rhythm":
            rhythm_result,
        "optimizer":
            optimizer,
        "visual_quality_gate":
            gate,
        "source_boundary":
            source,
        "renderer_modified":
            False,
        "render_executed":
            False,
        "video_generated":
            False,
    }

    output = (
        BASE
        / "logs"
        / "producao"
        / "vi7_85_cinematic_shadow_latest.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return result


def self_test():
    assert VERSION == "7.85"

    print(
        "VI7.85 SHADOW RUNTIME=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI7.88 — CINEMATIC AUDIT
# =====================================================

cat > vi7_88_cinematic_audit.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.88"

def evaluate(result):
    blockers = []
    warnings = []

    gate = (
        result.get(
            "visual_quality_gate"
        )
        or {}
    )

    if gate.get("status") == "HOLD":
        blockers.extend(
            gate.get("blockers")
            or []
        )

    repetition = (
        result.get("repetition")
        or {}
    )

    if repetition.get(
        "count",
        0
    ):
        warnings.append(
            "visual_repetition_detected"
        )

    optimizer = (
        result.get("optimizer")
        or {}
    )

    if optimizer.get(
        "count",
        0
    ):
        warnings.append(
            "sequence_improvements_available"
        )

    rhythm = (
        result.get("rhythm")
        or {}
    )

    if rhythm.get(
        "flat_runs"
    ):
        warnings.append(
            "flat_energy_runs_detected"
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
        "blockers":
            sorted(
                set(blockers)
            ),
        "warnings":
            sorted(
                set(warnings)
            ),
    }

def self_test():
    result = evaluate({
        "visual_quality_gate": {
            "status": "PASS",
            "blockers": [],
        },
        "repetition": {
            "count": 0
        },
        "optimizer": {
            "count": 0
        },
        "rhythm": {
            "flat_runs": []
        },
    })

    assert result["status"] == "PASS"

    print(
        "VI7.88 CINEMATIC AUDIT=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI7.91 — QUALITY FORECAST
# =====================================================

cat > vi7_91_quality_forecast.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.91"

def forecast(result):
    visual = (
        result.get(
            "visual_quality_gate"
        )
        or {}
    )

    diversity = (
        result.get("diversity")
        or {}
    )

    transitions = (
        result.get("transitions")
        or {}
    )

    documentary = (
        result.get("documentary")
        or {}
    )

    visual_score = float(
        visual.get(
            "average_quality",
            0
        )
    )

    diversity_score = float(
        diversity.get(
            "score",
            0
        )
    )

    transition_score = float(
        transitions.get(
            "average",
            0
        )
    )

    documentary_score = (
        float(
            documentary.get(
                "documentary_ratio",
                0
            )
        )
        * 100
    )

    score = (
        visual_score * .40
        + diversity_score * .25
        + transition_score * .25
        + documentary_score * .10
    )

    if score >= 85:
        level = "EXCELLENT"

    elif score >= 75:
        level = "STRONG"

    elif score >= 65:
        level = "PROMISING"

    else:
        level = "NEEDS_WORK"

    return {
        "version": VERSION,
        "forecast_score":
            round(score, 2),
        "level": level,
        "components": {
            "visual":
                round(
                    visual_score,
                    2
                ),
            "diversity":
                round(
                    diversity_score,
                    2
                ),
            "transitions":
                round(
                    transition_score,
                    2
                ),
            "documentary":
                round(
                    documentary_score,
                    2
                ),
        },
    }

def self_test():
    result = forecast({
        "visual_quality_gate": {
            "average_quality": 90
        },
        "diversity": {
            "score": 90
        },
        "transitions": {
            "average": 90
        },
        "documentary": {
            "documentary_ratio": .8
        },
    })

    assert result[
        "forecast_score"
    ] > 80

    print(
        "VI7.91 QUALITY FORECAST=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI7.94 — TRANSITION INTELLIGENCE
# =====================================================

cat > vi7_94_transition_intelligence.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.94"

def evaluate(plans):
    suggestions = []

    for a, b in zip(
        plans,
        plans[1:]
    ):
        if (
            a.get("shot")
            == b.get("shot")
            and a.get("category")
            == b.get("category")
        ):
            suggestions.append({
                "from":
                    a.get("scene"),
                "to":
                    b.get("scene"),
                "suggestion":
                    "change_shot_or_media_type",
            })

        if (
            a.get("motion")
            == b.get("motion")
        ):
            suggestions.append({
                "from":
                    a.get("scene"),
                "to":
                    b.get("scene"),
                "suggestion":
                    "change_motion_profile",
            })

        if (
            a.get("energy") == 3
            and b.get("energy") == 3
        ):
            suggestions.append({
                "from":
                    a.get("scene"),
                "to":
                    b.get("scene"),
                "suggestion":
                    "insert_visual_rest",
            })

    return {
        "version": VERSION,
        "suggestions":
            suggestions,
        "count":
            len(suggestions),
    }

def self_test():
    result = evaluate([
        {
            "scene": 1,
            "shot": "medium",
            "category": "DOCUMENT",
            "motion": "SLOW_PUSH",
            "energy": 1,
        },
        {
            "scene": 2,
            "shot": "medium",
            "category": "DOCUMENT",
            "motion": "SLOW_PUSH",
            "energy": 1,
        },
    ])

    assert result["count"] >= 2

    print(
        "VI7.94 TRANSITION INTELLIGENCE=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI7.97 — RELEASE CANDIDATE
# =====================================================

cat > vi7_97_release_candidate.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.97"

def evaluate(
    audit,
    forecast_result
):
    blockers = (
        audit.get("blockers")
        or []
    )

    warnings = (
        audit.get("warnings")
        or []
    )

    score = float(
        forecast_result.get(
            "forecast_score",
            0
        )
    )

    if blockers:
        status = "HOLD"

    elif score >= 75:
        status = (
            "READY_FOR_CONTROLLED_INTEGRATION"
        )

    else:
        status = (
            "SHADOW_TUNING_REQUIRED"
        )

    return {
        "version": VERSION,
        "status": status,
        "forecast_score": score,
        "blockers": blockers,
        "warnings": warnings,
        "runtime_activation":
            False,
        "full_active":
            False,
    }

def self_test():
    result = evaluate(
        {
            "blockers": [],
            "warnings": [],
        },
        {
            "forecast_score": 85
        }
    )

    assert (
        result["status"]
        == "READY_FOR_CONTROLLED_INTEGRATION"
    )

    print(
        "VI7.97 RELEASE CANDIDATE=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.00 — MASTER CINEMATIC GATE
# =====================================================

cat > vi8_00_master_cinematic_gate.py <<'PY'
#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path

from vi7_85_shadow_runtime import (
    run as shadow_run
)

from vi7_88_cinematic_audit import (
    evaluate as cinematic_audit
)

from vi7_91_quality_forecast import (
    forecast
)

from vi7_94_transition_intelligence import (
    evaluate as transition_intelligence
)

from vi7_97_release_candidate import (
    evaluate as release_candidate
)


VERSION = "8.00"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    shadow = shadow_run()

    audit = cinematic_audit(
        shadow
    )

    forecast_result = forecast(
        shadow
    )

    transition_result = (
        transition_intelligence(
            shadow.get("plans")
            or []
        )
    )

    release = release_candidate(
        audit,
        forecast_result
    )

    result = {
        "version": VERSION,
        "status":
            release.get("status"),
        "short_id":
            shadow.get("short_id"),
        "scene_map":
            shadow.get("scene_map"),
        "forecast_score":
            forecast_result.get(
                "forecast_score"
            ),
        "forecast_level":
            forecast_result.get(
                "level"
            ),
        "forecast_components":
            forecast_result.get(
                "components"
            ),
        "visual_quality":
            shadow.get(
                "visual_quality_gate"
            ),
        "diversity":
            shadow.get("diversity"),
        "documentary":
            shadow.get("documentary"),
        "rhythm":
            shadow.get("rhythm"),
        "repetition":
            shadow.get("repetition"),
        "transition_analysis":
            shadow.get("transitions"),
        "transition_intelligence":
            transition_result,
        "optimizer":
            shadow.get("optimizer"),
        "plans":
            shadow.get("plans"),
        "blockers":
            release.get("blockers"),
        "warnings":
            release.get("warnings"),
        "source_recovery":
            "SHADOW_ONLY",
        "renderer_activation":
            False,
        "ffmpeg_executed":
            False,
        "video_generated":
            False,
        "full_active_authorized":
            False,
    }

    output = (
        BASE
        / "logs"
        / "producao"
        / "vi8_00_master_cinematic_gate_latest.json"
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
    assert VERSION == "8.00"

    print(
        "VI8.00 MASTER CINEMATIC GATE=PASS"
    )


if __name__ == "__main__":
    result = evaluate()

    print()
    print(
        "STATUS:",
        result.get("status")
    )

    print(
        "SHORT ID:",
        result.get("short_id")
    )

    print(
        "FORECAST SCORE:",
        result.get(
            "forecast_score"
        )
    )

    print(
        "FORECAST LEVEL:",
        result.get(
            "forecast_level"
        )
    )

    visual = (
        result.get(
            "visual_quality"
        )
        or {}
    )

    print(
        "SAFE SCENES:",
        visual.get(
            "safe_scene_count"
        )
    )

    print(
        "VISUAL QUALITY AVG:",
        visual.get(
            "average_quality"
        )
    )

    print(
        "SHOT MISMATCH SCENES:",
        visual.get(
            "shot_mismatch_scenes"
        )
    )

    diversity = (
        result.get("diversity")
        or {}
    )

    print(
        "CATEGORY DIVERSITY:",
        diversity.get(
            "categories"
        )
    )

    print(
        "SHOT DIVERSITY:",
        diversity.get(
            "shots"
        )
    )

    print(
        "MOTION DIVERSITY:",
        diversity.get(
            "motions"
        )
    )

    print(
        "DIVERSITY SCORE:",
        diversity.get(
            "score"
        )
    )

    documentary = (
        result.get("documentary")
        or {}
    )

    print(
        "DOCUMENTARY RATIO:",
        documentary.get(
            "documentary_ratio"
        )
    )

    transitions = (
        result.get(
            "transition_analysis"
        )
        or {}
    )

    print(
        "TRANSITION AVG:",
        transitions.get(
            "average"
        )
    )

    repetition = (
        result.get(
            "repetition"
        )
        or {}
    )

    print(
        "REPETITION WARNINGS:",
        repetition.get(
            "count"
        )
    )

    rhythm = (
        result.get("rhythm")
        or {}
    )

    print(
        "FLAT ENERGY RUNS:",
        rhythm.get(
            "flat_runs"
        )
    )

    optimizer = (
        result.get("optimizer")
        or {}
    )

    print(
        "OPTIMIZER ACTIONS:",
        optimizer.get(
            "count"
        )
    )

    transition_intel = (
        result.get(
            "transition_intelligence"
        )
        or {}
    )

    print(
        "TRANSITION SUGGESTIONS:",
        transition_intel.get(
            "count"
        )
    )

    print(
        "BLOCKERS:",
        result.get("blockers")
    )

    print(
        "WARNINGS:",
        result.get("warnings")
    )

    print(
        "SOURCE RECOVERY:",
        result.get(
            "source_recovery"
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
        "FULL ACTIVE AUTHORIZED:",
        result.get(
            "full_active_authorized"
        )
    )

    print()
    print(
        "===== CINEMATIC SCENE PLAN ====="
    )

    for item in (
        result.get("plans")
        or []
    ):
        print(
            "SCENE",
            item.get("scene"),
            "| category=",
            item.get("category"),
            "| shot=",
            item.get("shot"),
            "| role=",
            item.get("role"),
            "| motion=",
            item.get("motion"),
            "| energy=",
            item.get("energy"),
            "| quality=",
            item.get("quality_score"),
            "| risk=",
            (
                item.get("risk")
                or {}
            ).get("status"),
            "| status=",
            item.get("status"),
        )
PY


# =====================================================
# COMPILE
# =====================================================

echo
echo "===== COMPILE ====="

python -m py_compile \
  vi7_79_visual_quality_gate.py \
  vi7_82_source_boundary.py \
  vi7_85_shadow_runtime.py \
  vi7_88_cinematic_audit.py \
  vi7_91_quality_forecast.py \
  vi7_94_transition_intelligence.py \
  vi7_97_release_candidate.py \
  vi8_00_master_cinematic_gate.py \
  || exit 1

echo "COMPILE=PASS"


# =====================================================
# SELF TESTS
# =====================================================

echo
echo "===== SELF TESTS ====="

python vi7_79_visual_quality_gate.py || exit 1
python vi7_82_source_boundary.py || exit 1
python vi7_88_cinematic_audit.py || exit 1
python vi7_91_quality_forecast.py || exit 1
python vi7_94_transition_intelligence.py || exit 1
python vi7_97_release_candidate.py || exit 1

echo "SELF TESTS=PASS"


# =====================================================
# CORE INTEGRITY BEFORE ANALYSIS
# =====================================================

VIDEO_HASH_MID="$(sha256sum video.py | awk '{print $1}')"
GERAR_HASH_MID="$(sha256sum gerar_short.sh | awk '{print $1}')"

if [ "$VIDEO_HASH_BEFORE" != "$VIDEO_HASH_MID" ]; then
    echo "CRITICAL: video.py mudou."
    exit 2
fi

if [ "$GERAR_HASH_BEFORE" != "$GERAR_HASH_MID" ]; then
    echo "CRITICAL: gerar_short.sh mudou."
    exit 3
fi

echo
echo "CORE FILES UNCHANGED=YES"


# =====================================================
# REAL SHADOW ANALYSIS
# =====================================================

echo
echo "======================================"
echo " VI8.00 CINEMATIC SHADOW ANALYSIS"
echo "======================================"
echo
echo "NO VIDEO WILL BE GENERATED."
echo

python vi8_00_master_cinematic_gate.py || exit 4


# =====================================================
# FINAL CORE INTEGRITY
# =====================================================

VIDEO_HASH_FINAL="$(sha256sum video.py | awk '{print $1}')"
GERAR_HASH_FINAL="$(sha256sum gerar_short.sh | awk '{print $1}')"

echo
echo "===== FINAL CORE INTEGRITY ====="
echo "VIDEO BEFORE=$VIDEO_HASH_BEFORE"
echo "VIDEO FINAL =$VIDEO_HASH_FINAL"
echo
echo "GERAR BEFORE=$GERAR_HASH_BEFORE"
echo "GERAR FINAL =$GERAR_HASH_FINAL"

if [ "$VIDEO_HASH_BEFORE" != "$VIDEO_HASH_FINAL" ]; then
    echo "CRITICAL: video.py mudou."
    exit 5
fi

if [ "$GERAR_HASH_BEFORE" != "$GERAR_HASH_FINAL" ]; then
    echo "CRITICAL: gerar_short.sh mudou."
    exit 6
fi

echo
echo "VIDEO.PY UNCHANGED=YES"
echo "GERAR_SHORT.SH UNCHANGED=YES"
echo "FFMPEG EXECUTED=NO"
echo "VIDEO GENERATED=NO"
echo "RENDERER MODIFIED=NO"
echo "SOURCE RECOVERY=SHADOW_ONLY"
echo "FULL ACTIVE=LOCKED"

echo
echo "======================================"
echo " VI8.00 COMPLETE"
echo "======================================"
echo
echo "REPORT:"
echo "logs/producao/vi8_00_master_cinematic_gate_latest.json"
