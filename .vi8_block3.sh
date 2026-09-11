#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$HOME/ShortAutoPro" || exit 1


cat > vi7_52_visual_sequence_planner.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.52"

def transition_score(a, b):
    score = 100

    if a.get("category") == b.get("category"):
        score -= 20

    if a.get("shot") == b.get("shot"):
        score -= 15

    if a.get("motion") == b.get("motion"):
        score -= 20

    if (
        a.get("energy") == 3
        and b.get("energy") == 3
    ):
        score -= 10

    return max(0, score)

def analyze(scenes):
    transitions = []

    for a, b in zip(
        scenes,
        scenes[1:]
    ):
        transitions.append({
            "from": a.get("scene"),
            "to": b.get("scene"),
            "score": transition_score(
                a,
                b
            ),
        })

    average = (
        sum(
            x["score"]
            for x in transitions
        ) / len(transitions)
        if transitions
        else 100.0
    )

    return {
        "version": VERSION,
        "average": round(
            average,
            2
        ),
        "transitions": transitions,
    }

def self_test():
    assert transition_score(
        {
            "category": "DOCUMENT",
            "shot": "medium",
            "motion": "SLOW_PUSH",
            "energy": 1,
        },
        {
            "category": "LOCATION",
            "shot": "wide",
            "motion": "HORIZONTAL_DISCOVERY",
            "energy": 2,
        }
    ) == 100

    print(
        "VI7.52 VISUAL SEQUENCE PLANNER=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


cat > vi7_55_documentary_continuity.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.55"

DOCUMENTARY = {
    "DOCUMENT",
    "EVIDENCE",
    "LOCATION",
}

def evaluate(scenes):
    documentary = sum(
        1
        for item in scenes
        if item.get("category")
        in DOCUMENTARY
    )

    total = len(scenes)

    ratio = (
        documentary / total
        if total
        else 0
    )

    return {
        "version": VERSION,
        "documentary_scenes":
            documentary,
        "total_scenes":
            total,
        "documentary_ratio":
            round(ratio, 3),
        "status": (
            "PASS"
            if ratio >= .40
            else "PASS_WITH_WARNINGS"
        ),
    }

def self_test():
    result = evaluate([
        {"category": "DOCUMENT"},
        {"category": "LOCATION"},
        {"category": "FACE"},
    ])

    assert (
        result[
            "documentary_ratio"
        ] > .5
    )

    print(
        "VI7.55 DOCUMENTARY CONTINUITY=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


cat > vi7_58_media_diversity.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.58"

def evaluate(scenes):
    categories = [
        x.get("category")
        for x in scenes
        if x.get("category")
    ]

    shots = [
        x.get("shot")
        for x in scenes
        if x.get("shot")
    ]

    motions = [
        x.get("motion")
        for x in scenes
        if x.get("motion")
    ]

    category_diversity = len(
        set(categories)
    )

    shot_diversity = len(
        set(shots)
    )

    motion_diversity = len(
        set(motions)
    )

    score = (
        min(category_diversity, 5) * 8
        + min(shot_diversity, 3) * 10
        + min(motion_diversity, 6) * 5
    )

    return {
        "version": VERSION,
        "categories":
            category_diversity,
        "shots":
            shot_diversity,
        "motions":
            motion_diversity,
        "score":
            min(100, score),
    }

def self_test():
    result = evaluate([
        {
            "category": "DOCUMENT",
            "shot": "close_up",
            "motion": "DOCUMENT_SCAN",
        },
        {
            "category": "LOCATION",
            "shot": "wide",
            "motion": "HORIZONTAL_DISCOVERY",
        },
    ])

    assert result["score"] > 0

    print(
        "VI7.58 MEDIA DIVERSITY=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


cat > vi7_70_scene_plan_builder.py <<'PY'
#!/usr/bin/env python3

from vi7_31_visual_ontology import classify
from vi7_34_shot_language import (
    evaluate as shot_eval,
    normalize
)
from vi7_43_narrative_energy import (
    energy,
    role
)
from vi7_46_cinematic_motion_planner import choose
from vi7_49_scene_quality_score import score
from vi7_61_subject_preservation import constraints
from vi7_64_visual_risk_intelligence import (
    evaluate as risk_eval
)
from vi7_67_cinematic_scene_contract import build

VERSION = "7.70"

def build_plan(scenes):
    result = []
    previous_motion = None

    for index, scene in enumerate(
        scenes,
        start=1
    ):
        number = int(
            scene.get(
                "scene",
                index
            )
        )

        category = classify(scene)

        shot = normalize(
            scene.get(
                "shot_type"
            )
            or "medium"
        )

        shot_result = shot_eval(
            category,
            shot
        )

        narrative_energy = energy(
            number
        )

        narrative_role = role(
            number
        )

        if narrative_role in {
            "HOOK",
            "CTA",
        }:
            motion = "MICRO_HOLD"
        else:
            motion = choose(
                category,
                narrative_energy,
                previous_motion
            )

        quality = score(
            scene,
            category,
            shot_result["match"]
        )

        preservation = constraints(
            category
        )

        risk = risk_eval(
            scene,
            category
        )

        contract = build(
            number,
            category,
            shot,
            motion,
            narrative_energy,
            quality,
            risk,
            preservation
        )

        contract["role"] = (
            narrative_role
        )

        contract["query"] = (
            scene.get("query")
        )

        contract["shot_match"] = (
            shot_result["match"]
        )

        result.append(
            contract
        )

        if (
            contract.get("status")
            == "PASS"
        ):
            previous_motion = motion

    return result

def self_test():
    sample = [{
        "scene": 1,
        "segment": "Hook",
        "query": "old letter paper",
        "visual_mode": "document",
        "shot_type": "close_up",
        "must_have": ["paper"],
        "avoid": [],
    }]

    result = build_plan(sample)

    assert len(result) == 1

    print(
        "VI7.70 SCENE PLAN BUILDER=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


cat > vi7_73_global_rhythm.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.73"

def evaluate(plans):
    energies = [
        x.get(
            "energy",
            1
        )
        for x in plans
    ]

    flat_runs = []

    for i in range(
        len(energies) - 2
    ):
        if (
            energies[i]
            == energies[i+1]
            == energies[i+2]
        ):
            flat_runs.append([
                i + 1,
                i + 2,
                i + 3,
            ])

    return {
        "version": VERSION,
        "energies": energies,
        "flat_runs": flat_runs,
        "status": (
            "PASS_WITH_WARNINGS"
            if flat_runs
            else "PASS"
        ),
    }

def self_test():
    result = evaluate([
        {"energy": 1},
        {"energy": 1},
        {"energy": 1},
    ])

    assert len(
        result["flat_runs"]
    ) == 1

    print(
        "VI7.73 GLOBAL RHYTHM=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


cat > vi7_76_sequence_optimizer.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.76"

def recommendations(
    plans,
    repetition,
    transitions
):
    actions = []

    for warning in repetition.get(
        "warnings",
        []
    ):
        actions.append({
            "type":
                "BREAK_REPETITION",
            "scenes":
                warning.get("scenes"),
            "reason":
                warning.get("type"),
        })

    for item in transitions.get(
        "transitions",
        []
    ):
        if item.get(
            "score",
            100
        ) < 60:
            actions.append({
                "type":
                    "IMPROVE_TRANSITION",
                "from":
                    item.get("from"),
                "to":
                    item.get("to"),
                "score":
                    item.get("score"),
            })

    return {
        "version": VERSION,
        "actions": actions,
        "count": len(actions),
    }

def self_test():
    result = recommendations(
        [],
        {
            "warnings": [{
                "type":
                    "shot_triple",
                "scenes":
                    [1,2,3],
            }]
        },
        {
            "transitions": []
        }
    )

    assert result["count"] == 1

    print(
        "VI7.76 SEQUENCE OPTIMIZER=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


python -m py_compile \
  vi7_52_visual_sequence_planner.py \
  vi7_55_documentary_continuity.py \
  vi7_58_media_diversity.py \
  vi7_70_scene_plan_builder.py \
  vi7_73_global_rhythm.py \
  vi7_76_sequence_optimizer.py \
  || exit 1

python vi7_52_visual_sequence_planner.py || exit 1
python vi7_55_documentary_continuity.py || exit 1
python vi7_58_media_diversity.py || exit 1
python vi7_70_scene_plan_builder.py || exit 1
python vi7_73_global_rhythm.py || exit 1
python vi7_76_sequence_optimizer.py || exit 1

echo
echo "======================================"
echo " VI8 BLOCK 3/4 COMPLETE"
echo "======================================"
echo "GLOBAL SCENE PLANNING=INSTALLED"
echo "TRANSITION ANALYSIS=INSTALLED"
echo "DOCUMENTARY CONTINUITY=INSTALLED"
echo "MEDIA DIVERSITY=INSTALLED"
echo "GLOBAL RHYTHM=INSTALLED"
echo "SEQUENCE OPTIMIZER=INSTALLED"
echo "VIDEO GENERATED=NO"
echo "FFMPEG EXECUTED=NO"
echo "RENDERER MODIFIED=NO"
