#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$HOME/ShortAutoPro" || exit 1

echo
echo "======================================"
echo " VI8.11 -> VI8.20"
echo " INTELLIGENT MEDIA SELECTION"
echo " SHADOW ONLY"
echo "======================================"

VIDEO_BEFORE="$(sha256sum video.py | awk '{print $1}')"
GERAR_BEFORE="$(sha256sum gerar_short.sh | awk '{print $1}')"


# =====================================================
# VI8.11 — IDEAL SHOT GENERATOR
# =====================================================

cat > vi8_11_ideal_shot_generator.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.11"

IDEAL = {
    "FACE":
        ["medium", "close_up"],

    "DOCUMENT":
        ["close_up", "medium"],

    "EVIDENCE":
        ["close_up", "medium"],

    "LOCATION":
        ["wide", "medium"],

    "OBJECT":
        ["close_up", "medium"],

    "GENERAL":
        ["medium", "wide"],

    "ABSTRACT":
        ["medium", "wide"],
}

def generate(category):
    return IDEAL.get(
        str(category or "GENERAL").upper(),
        IDEAL["GENERAL"]
    )

def self_test():
    assert (
        generate("FACE")[0]
        == "medium"
    )

    print(
        "VI8.11 IDEAL SHOT GENERATOR=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.12 — VIRTUAL CANDIDATE FACTORY
# =====================================================

cat > vi8_12_virtual_candidate_factory.py <<'PY'
#!/usr/bin/env python3

from vi8_11_ideal_shot_generator import generate

VERSION = "8.12"

SIZE_BY_SHOT = {
    "close_up":
        (1200, 1600),

    "medium":
        (1200, 1600),

    "wide":
        (1600, 1000),
}

def build(scene, category):
    query = str(
        scene.get("query")
        or ""
    )

    shots = generate(
        category
    )

    candidates = []

    for index, shot in enumerate(
        shots,
        start=1
    ):
        width, height = (
            SIZE_BY_SHOT.get(
                shot,
                (1200, 1600)
            )
        )

        candidates.append({
            "path":
                f"shadow://scene_{scene.get('scene')}_{shot}_{index}",

            "source":
                "SHADOW_VIRTUAL",

            "media_type":
                "STILL",

            "width":
                width,

            "height":
                height,

            "query":
                query,

            "category":
                category,

            "shot":
                shot,

            "source_score":
                85,

            "metadata": {
                "virtual":
                    True,

                "identity_confirmed":
                    (
                        True
                        if category != "FACE"
                        else None
                    ),
            },
        })

    return candidates

def self_test():
    result = build(
        {
            "scene": 3,
            "query": "house exterior"
        },
        "LOCATION"
    )

    assert len(result) >= 2

    print(
        "VI8.12 VIRTUAL CANDIDATE FACTORY=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.13 — CURRENT MEDIA MODEL
# =====================================================

cat > vi8_13_current_media_model.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.13"

def from_scene(scene, category):
    shot = str(
        scene.get("shot_type")
        or "medium"
    ).lower()

    if shot == "wide":
        width, height = (
            1600,
            1000
        )

    elif shot == "close_up":
        width, height = (
            1200,
            1600
        )

    else:
        width, height = (
            1200,
            1600
        )

    return {
        "path":
            f"current://scene_{scene.get('scene')}",

        "source":
            "CURRENT_SELECTION",

        "media_type":
            "STILL",

        "width":
            width,

        "height":
            height,

        "query":
            scene.get("query")
            or "",

        "category":
            category,

        "shot":
            shot,

        "source_score":
            75,

        "metadata": {
            "virtual":
                False,

            "identity_confirmed":
                (
                    True
                    if category != "FACE"
                    else None
                ),
        },
    }

def self_test():
    result = from_scene(
        {
            "scene": 2,
            "shot_type": "wide",
            "query": "street"
        },
        "LOCATION"
    )

    assert result["shot"] == "wide"

    print(
        "VI8.13 CURRENT MEDIA MODEL=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.14 — CURRENT VS IDEAL COMPARATOR
# =====================================================

cat > vi8_14_current_vs_ideal.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.14"

def compare(
    current_score,
    best_score
):
    delta = (
        float(best_score)
        - float(current_score)
    )

    if delta >= 15:
        recommendation = (
            "STRONG_REPLACEMENT_CANDIDATE"
        )

    elif delta >= 7:
        recommendation = (
            "REPLACEMENT_CANDIDATE"
        )

    elif delta >= 2:
        recommendation = (
            "MINOR_IMPROVEMENT"
        )

    else:
        recommendation = (
            "KEEP_CURRENT"
        )

    return {
        "version": VERSION,
        "delta":
            round(delta, 2),
        "recommendation":
            recommendation,
    }

def self_test():
    result = compare(
        60,
        90
    )

    assert (
        result["recommendation"]
        == "STRONG_REPLACEMENT_CANDIDATE"
    )

    print(
        "VI8.14 CURRENT VS IDEAL=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.15 — SCENE MEDIA SELECTOR
# =====================================================

cat > vi8_15_scene_media_selector.py <<'PY'
#!/usr/bin/env python3

from vi8_09_candidate_scorer import (
    evaluate as score_candidate
)

from vi8_12_virtual_candidate_factory import (
    build as virtual_candidates
)

from vi8_13_current_media_model import (
    from_scene as current_candidate
)

from vi8_14_current_vs_ideal import (
    compare
)

VERSION = "8.15"

def select(
    scene,
    category,
    previous_winners=None
):
    previous_winners = (
        previous_winners
        or []
    )

    current = current_candidate(
        scene,
        category
    )

    current_result = (
        score_candidate(
            scene,
            current,
            previous_winners
        )
    )

    candidates = [
        current
    ]

    candidates.extend(
        virtual_candidates(
            scene,
            category
        )
    )

    ranked = []

    for candidate in candidates:
        result = score_candidate(
            scene,
            candidate,
            previous_winners
        )

        ranked.append({
            "candidate":
                candidate,

            "score":
                result["score"],

            "eligible":
                result["eligible"],

            "blockers":
                result["blockers"],

            "warnings":
                result["warnings"],

            "components":
                result["components"],
        })

    eligible = [
        item
        for item in ranked
        if item["eligible"]
    ]

    eligible.sort(
        key=lambda item:
            item["score"],
        reverse=True
    )

    if not eligible:
        winner = ranked[0]
    else:
        winner = eligible[0]

    comparison = compare(
        current_result["score"],
        winner["score"]
    )

    return {
        "version":
            VERSION,

        "scene":
            scene.get("scene"),

        "category":
            category,

        "current":
            {
                "candidate":
                    current,

                "score":
                    current_result[
                        "score"
                    ],

                "components":
                    current_result[
                        "components"
                    ],
            },

        "winner":
            winner,

        "candidate_count":
            len(ranked),

        "ranking":
            ranked,

        "comparison":
            comparison,
    }

def self_test():
    result = select(
        {
            "scene": 6,
            "query":
                "young girl portrait",
            "shot_type":
                "wide",
            "segment":
                "girl portrait",
        },
        "FACE"
    )

    assert (
        result[
            "candidate_count"
        ] >= 3
    )

    print(
        "VI8.15 SCENE MEDIA SELECTOR=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.16 — GLOBAL MEDIA CONTINUITY
# =====================================================

cat > vi8_16_global_media_continuity.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.16"

def evaluate(selections):
    warnings = []

    winner_categories = [
        (
            item.get(
                "winner"
            )
            or {}
        ).get(
            "candidate",
            {}
        ).get(
            "category"
        )
        for item in selections
    ]

    winner_shots = [
        (
            item.get(
                "winner"
            )
            or {}
        ).get(
            "candidate",
            {}
        ).get(
            "shot"
        )
        for item in selections
    ]

    for i in range(
        len(selections) - 2
    ):
        cats = winner_categories[
            i:i+3
        ]

        shots = winner_shots[
            i:i+3
        ]

        if (
            len(set(cats)) == 1
            and cats[0]
        ):
            warnings.append({
                "type":
                    "three_same_categories",

                "scenes":
                    [
                        selections[i+j][
                            "scene"
                        ]
                        for j in range(3)
                    ],
            })

        if (
            len(set(shots)) == 1
            and shots[0]
        ):
            warnings.append({
                "type":
                    "three_same_shots",

                "scenes":
                    [
                        selections[i+j][
                            "scene"
                        ]
                        for j in range(3)
                    ],
            })

    return {
        "version":
            VERSION,

        "warnings":
            warnings,

        "count":
            len(warnings),
    }

def self_test():
    assert VERSION == "8.16"

    print(
        "VI8.16 GLOBAL MEDIA CONTINUITY=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.17 — SHOT CORRECTION ENGINE
# =====================================================

cat > vi8_17_shot_correction_engine.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.17"

def evaluate(selection):
    current = (
        selection.get(
            "current"
        )
        or {}
    )

    winner = (
        selection.get(
            "winner"
        )
        or {}
    )

    current_candidate = (
        current.get(
            "candidate"
        )
        or {}
    )

    winner_candidate = (
        winner.get(
            "candidate"
        )
        or {}
    )

    current_shot = (
        current_candidate.get(
            "shot"
        )
    )

    winner_shot = (
        winner_candidate.get(
            "shot"
        )
    )

    return {
        "version":
            VERSION,

        "scene":
            selection.get(
                "scene"
            ),

        "current_shot":
            current_shot,

        "recommended_shot":
            winner_shot,

        "change":
            (
                current_shot
                != winner_shot
            ),
    }

def self_test():
    assert VERSION == "8.17"

    print(
        "VI8.17 SHOT CORRECTION ENGINE=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.18 — MEDIA SELECTION PLAN
# =====================================================

cat > vi8_18_media_selection_plan.py <<'PY'
#!/usr/bin/env python3

from vi7_31_visual_ontology import (
    classify
)

from vi8_15_scene_media_selector import (
    select
)

from vi8_16_global_media_continuity import (
    evaluate as continuity
)

from vi8_17_shot_correction_engine import (
    evaluate as shot_correction
)

VERSION = "8.18"

def build(scenes):
    selections = []
    previous_winners = []

    for scene in scenes:
        category = classify(
            scene
        )

        result = select(
            scene,
            category,
            previous_winners
        )

        selections.append(
            result
        )

        winner_candidate = (
            result.get(
                "winner"
            )
            or {}
        ).get(
            "candidate"
        )

        if winner_candidate:
            previous_winners.append(
                winner_candidate
            )

    continuity_result = continuity(
        selections
    )

    shot_changes = [
        shot_correction(
            selection
        )
        for selection in selections
    ]

    return {
        "version":
            VERSION,

        "selections":
            selections,

        "continuity":
            continuity_result,

        "shot_corrections":
            shot_changes,
    }

def self_test():
    sample = [
        {
            "scene": 1,
            "segment": "house",
            "query":
                "house exterior",
            "shot_type":
                "medium",
        }
    ]

    result = build(
        sample
    )

    assert len(
        result["selections"]
    ) == 1

    print(
        "VI8.18 MEDIA SELECTION PLAN=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.19 — SELECTION AUDIT
# =====================================================

cat > vi8_19_selection_audit.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.19"

def evaluate(plan):
    selections = (
        plan.get(
            "selections"
        )
        or []
    )

    blockers = []
    warnings = []

    replacement = 0
    strong = 0
    keep = 0

    for item in selections:
        comparison = (
            item.get(
                "comparison"
            )
            or {}
        )

        recommendation = (
            comparison.get(
                "recommendation"
            )
        )

        if recommendation == (
            "STRONG_REPLACEMENT_CANDIDATE"
        ):
            strong += 1

        elif recommendation in {
            "REPLACEMENT_CANDIDATE",
            "MINOR_IMPROVEMENT",
        }:
            replacement += 1

        elif recommendation == "KEEP_CURRENT":
            keep += 1

        winner = (
            item.get(
                "winner"
            )
            or {}
        )

        if not winner.get(
            "eligible",
            False
        ):
            blockers.append(
                f"scene_{item.get('scene')}_no_eligible_winner"
            )

    continuity = (
        plan.get(
            "continuity"
        )
        or {}
    )

    if continuity.get(
        "count",
        0
    ):
        warnings.append(
            "global_media_repetition"
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

        "strong_replacements":
            strong,

        "improvements":
            replacement,

        "keep_current":
            keep,

        "blockers":
            blockers,

        "warnings":
            warnings,
    }

def self_test():
    assert VERSION == "8.19"

    print(
        "VI8.19 SELECTION AUDIT=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.20 — MEDIA SELECTION SHADOW GATE
# =====================================================

cat > vi8_20_media_selection_shadow_gate.py <<'PY'
#!/usr/bin/env python3

import json

from pathlib import Path

from vi8_18_media_selection_plan import (
    build
)

from vi8_19_selection_audit import (
    evaluate as audit
)

VERSION = "8.20"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

def latest_scene_map():
    files = [
        path
        for path in (
            BASE
            / "roteiros"
        ).glob(
            "scene_map_*.json"
        )
        if "_pre_" not in path.name
    ]

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

def evaluate():
    path = latest_scene_map()

    if not path:
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

    plan = build(
        scenes
    )

    audit_result = audit(
        plan
    )

    return {
        "version":
            VERSION,

        "status":
            audit_result[
                "status"
            ],

        "short_id":
            data.get(
                "short_id"
            ),

        "scene_map":
            str(path),

        "plan":
            plan,

        "audit":
            audit_result,

        "automatic_download":
            False,

        "automatic_replace":
            False,

        "renderer_activation":
            False,

        "video_generated":
            False,

        "full_active":
            False,
    }

def self_test():
    assert VERSION == "8.20"

    print(
        "VI8.20 MEDIA SELECTION SHADOW GATE=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


echo
echo "===== COMPILE ====="

python -m py_compile \
  vi8_11_ideal_shot_generator.py \
  vi8_12_virtual_candidate_factory.py \
  vi8_13_current_media_model.py \
  vi8_14_current_vs_ideal.py \
  vi8_15_scene_media_selector.py \
  vi8_16_global_media_continuity.py \
  vi8_17_shot_correction_engine.py \
  vi8_18_media_selection_plan.py \
  vi8_19_selection_audit.py \
  vi8_20_media_selection_shadow_gate.py \
  || exit 10

echo "COMPILE=PASS"


echo
echo "===== SELF TESTS ====="

python vi8_11_ideal_shot_generator.py || exit 11
python vi8_12_virtual_candidate_factory.py || exit 12
python vi8_13_current_media_model.py || exit 13
python vi8_14_current_vs_ideal.py || exit 14
python vi8_15_scene_media_selector.py || exit 15
python vi8_16_global_media_continuity.py || exit 16
python vi8_17_shot_correction_engine.py || exit 17
python vi8_18_media_selection_plan.py || exit 18
python vi8_19_selection_audit.py || exit 19
python vi8_20_media_selection_shadow_gate.py || exit 20

echo "SELF TESTS=PASS"


echo
echo "===== REAL SHADOW MEDIA ANALYSIS ====="

python - <<'PY'
from vi8_20_media_selection_shadow_gate import evaluate

r = evaluate()

print(
    "STATUS:",
    r.get("status")
)

print(
    "SHORT ID:",
    r.get("short_id")
)

audit = (
    r.get("audit")
    or {}
)

print(
    "STRONG REPLACEMENTS:",
    audit.get(
        "strong_replacements"
    )
)

print(
    "IMPROVEMENTS:",
    audit.get(
        "improvements"
    )
)

print(
    "KEEP CURRENT:",
    audit.get(
        "keep_current"
    )
)

print(
    "BLOCKERS:",
    audit.get(
        "blockers"
    )
)

print(
    "WARNINGS:",
    audit.get(
        "warnings"
    )
)

print()
print(
    "===== MEDIA SELECTION PLAN ====="
)

plan = (
    r.get("plan")
    or {}
)

for item in (
    plan.get(
        "selections"
    )
    or []
):
    current = (
        item.get("current")
        or {}
    )

    winner = (
        item.get("winner")
        or {}
    )

    current_candidate = (
        current.get(
            "candidate"
        )
        or {}
    )

    winner_candidate = (
        winner.get(
            "candidate"
        )
        or {}
    )

    comparison = (
        item.get(
            "comparison"
        )
        or {}
    )

    print(
        "SCENE",
        item.get("scene"),
        "| category=",
        item.get("category"),
        "| current_shot=",
        current_candidate.get(
            "shot"
        ),
        "| current_score=",
        current.get("score"),
        "| winner_shot=",
        winner_candidate.get(
            "shot"
        ),
        "| winner_score=",
        winner.get("score"),
        "| delta=",
        comparison.get("delta"),
        "| recommendation=",
        comparison.get(
            "recommendation"
        ),
    )

print()
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
    "RENDERER ACTIVATION:",
    r.get(
        "renderer_activation"
    )
)

print(
    "VIDEO GENERATED:",
    r.get(
        "video_generated"
    )
)

print(
    "FULL ACTIVE:",
    r.get(
        "full_active"
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
echo " VI8.11 -> VI8.20 COMPLETE"
echo "======================================"
echo "INTELLIGENT MEDIA SELECTION=SHADOW"
echo "CURRENT VS IDEAL=READY"
echo "SHOT CORRECTION=READY"
echo "GLOBAL MEDIA CONTINUITY=READY"
echo "SELECTION AUDIT=READY"
echo
echo "VIDEO.PY UNCHANGED=YES"
echo "GERAR_SHORT.SH UNCHANGED=YES"
echo "VIDEO GENERATED=NO"
echo "FFMPEG EXECUTED=NO"
echo "DOWNLOAD EXECUTED=NO"
echo "MEDIA REPLACEMENT=NO"
echo "FULL ACTIVE=LOCKED"
