#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$HOME/ShortAutoPro" || exit 1


cat > vi7_46_cinematic_motion_planner.py <<'PY'
#!/usr/bin/env python3

from vi7_37_motion_safety import profiles

VERSION = "7.46"

ENERGY = {
    "MICRO_HOLD": 0,
    "FACE_SAFE_PUSH": 1,
    "SLOW_PUSH": 1,
    "DOCUMENT_SCAN": 1,
    "DETAIL_PUSH": 2,
    "MICRO_DISCOVERY": 2,
    "HORIZONTAL_DISCOVERY": 2,
    "ARCHITECTURE_DRIFT": 2,
    "REVERSE_DRIFT": 2,
}

def choose(category, narrative_energy, previous_profile=None):
    candidates = list(profiles(category))

    if not candidates:
        return None

    target = min(
        max(int(narrative_energy), 0),
        2
    )

    ranked = sorted(
        candidates,
        key=lambda profile: abs(
            ENERGY.get(profile, 1)
            - target
        )
    )

    for candidate in ranked:
        if (
            previous_profile
            and candidate == previous_profile
        ):
            continue

        return candidate

    return ranked[0]

def self_test():
    result = choose(
        "FACE",
        2
    )

    assert result in {
        "FACE_SAFE_PUSH",
        "SLOW_PUSH",
        "MICRO_HOLD",
    }

    assert (
        choose(
            "LOCATION",
            2
        )
        is not None
    )

    print(
        "VI7.46 CINEMATIC MOTION PLANNER=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


cat > vi7_49_scene_quality_score.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.49"

def score(
    scene,
    category,
    shot_match
):
    value = 50.0

    query = str(
        scene.get("query") or ""
    ).strip()

    must = (
        scene.get("must_have")
        or []
    )

    avoid = (
        scene.get("avoid")
        or []
    )

    visual_mode = str(
        scene.get("visual_mode")
        or ""
    ).strip()

    if query:
        value += 15

    if len(query.split()) >= 4:
        value += 10

    if must:
        value += 10

    if avoid:
        value += 5

    if shot_match:
        value += 10

    if visual_mode:
        value += 5

    if category in {
        "DOCUMENT",
        "EVIDENCE",
        "LOCATION",
        "FACE",
    }:
        value += 5

    return min(
        100.0,
        value
    )

def self_test():
    scene = {
        "query":
            "old handwritten letter paper",
        "must_have":
            ["paper"],
        "avoid":
            ["phone"],
        "visual_mode":
            "document",
    }

    result = score(
        scene,
        "DOCUMENT",
        True
    )

    assert result >= 90

    print(
        "VI7.49 SCENE QUALITY SCORE=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


cat > vi7_61_subject_preservation.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.61"

def constraints(category):

    if category == "FACE":
        return {
            "center_bias": True,
            "lateral_motion": False,
            "max_energy": 1,
            "crop_sensitivity": "HIGH",
        }

    if category == "DOCUMENT":
        return {
            "center_bias": False,
            "lateral_motion": True,
            "max_energy": 2,
            "crop_sensitivity": "MEDIUM",
        }

    if category == "LOCATION":
        return {
            "center_bias": False,
            "lateral_motion": True,
            "max_energy": 2,
            "crop_sensitivity": "LOW",
        }

    if category == "EVIDENCE":
        return {
            "center_bias": True,
            "lateral_motion": True,
            "max_energy": 2,
            "crop_sensitivity": "MEDIUM",
        }

    return {
        "center_bias": False,
        "lateral_motion": True,
        "max_energy": 2,
        "crop_sensitivity": "MEDIUM",
    }

def self_test():
    face = constraints("FACE")

    assert (
        face["lateral_motion"]
        is False
    )

    assert (
        face["max_energy"]
        == 1
    )

    print(
        "VI7.61 SUBJECT PRESERVATION=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


cat > vi7_64_visual_risk_intelligence.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.64"

def evaluate(
    scene,
    category
):
    risk = 0
    reasons = []

    query = str(
        scene.get("query")
        or ""
    ).lower()

    avoid = " ".join(
        str(x)
        for x in (
            scene.get("avoid")
            or []
        )
    ).lower()

    if category == "FACE":
        risk += 2

        reasons.append(
            "identity_sensitive_visual"
        )

    if category == "DOCUMENT":
        risk += 1

        reasons.append(
            "text_legibility_risk"
        )

    graphic_terms = (
        "corpse",
        "dead body",
        "blood",
        "graphic",
        "open wound",
        "severed",
        "gore",
    )

    if any(
        token in query
        for token in graphic_terms
    ):
        risk += 4

        reasons.append(
            "graphic_visual_risk"
        )

    if any(
        token in avoid
        for token in (
            "adult woman",
            "teenager",
            "wrong person",
        )
    ):
        risk += 1

        reasons.append(
            "identity_mismatch_risk"
        )

    if risk >= 5:
        status = "HOLD"

    elif risk >= 2:
        status = "CAUTION"

    else:
        status = "PASS"

    return {
        "version": VERSION,
        "risk": risk,
        "reasons": reasons,
        "status": status,
    }

def self_test():
    result = evaluate(
        {
            "query":
                "young girl portrait",
            "avoid":
                ["adult woman"],
        },
        "FACE"
    )

    assert result["risk"] >= 2

    print(
        "VI7.64 VISUAL RISK INTELLIGENCE=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


cat > vi7_67_cinematic_scene_contract.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.67"

LATERAL_PROFILES = {
    "HORIZONTAL_DISCOVERY",
    "ARCHITECTURE_DRIFT",
    "REVERSE_DRIFT",
    "DOCUMENT_SCAN",
}

PROFILE_ENERGY = {
    "MICRO_HOLD": 0,
    "FACE_SAFE_PUSH": 1,
    "SLOW_PUSH": 1,
    "DOCUMENT_SCAN": 1,
    "DETAIL_PUSH": 2,
    "MICRO_DISCOVERY": 2,
    "HORIZONTAL_DISCOVERY": 2,
    "ARCHITECTURE_DRIFT": 2,
    "REVERSE_DRIFT": 2,
}

def build(
    scene_number,
    category,
    shot,
    motion,
    energy,
    quality,
    risk,
    preservation
):
    blockers = []
    warnings = []

    if (
        preservation.get(
            "lateral_motion"
        ) is False
        and motion in LATERAL_PROFILES
    ):
        blockers.append(
            "subject_lateral_motion_violation"
        )

    motion_energy = PROFILE_ENERGY.get(
        motion,
        1
    )

    if motion_energy > preservation.get(
        "max_energy",
        2
    ):
        blockers.append(
            "motion_energy_exceeds_subject_limit"
        )

    if risk.get("status") == "HOLD":
        blockers.append(
            "visual_risk_hold"
        )

    if risk.get("status") == "CAUTION":
        warnings.append(
            "visual_risk_caution"
        )

    if quality < 70:
        warnings.append(
            "scene_quality_low"
        )

    return {
        "version": VERSION,
        "scene": scene_number,
        "category": category,
        "shot": shot,
        "motion": motion,
        "energy": energy,
        "motion_energy":
            motion_energy,
        "quality_score": quality,
        "risk": risk,
        "preservation":
            preservation,
        "status": (
            "PASS"
            if not blockers
            else "HOLD"
        ),
        "blockers": blockers,
        "warnings": warnings,
    }

def self_test():
    result = build(
        4,
        "FACE",
        "medium",
        "FACE_SAFE_PUSH",
        1,
        95,
        {
            "status":
                "CAUTION"
        },
        {
            "lateral_motion":
                False,
            "max_energy":
                1,
        }
    )

    assert (
        result["status"]
        == "PASS"
    )

    print(
        "VI7.67 CINEMATIC SCENE CONTRACT=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


python -m py_compile \
  vi7_46_cinematic_motion_planner.py \
  vi7_49_scene_quality_score.py \
  vi7_61_subject_preservation.py \
  vi7_64_visual_risk_intelligence.py \
  vi7_67_cinematic_scene_contract.py \
  || exit 1

python vi7_46_cinematic_motion_planner.py || exit 1
python vi7_49_scene_quality_score.py || exit 1
python vi7_61_subject_preservation.py || exit 1
python vi7_64_visual_risk_intelligence.py || exit 1
python vi7_67_cinematic_scene_contract.py || exit 1


echo
echo "======================================"
echo " VI8 BLOCK 2/4 COMPLETE"
echo "======================================"
echo "CINEMATIC MOTION=INSTALLED"
echo "SUBJECT PRESERVATION=INSTALLED"
echo "VISUAL RISK=INSTALLED"
echo "SCENE QUALITY=INSTALLED"
echo "SCENE CONTRACTS=INSTALLED"
echo "VIDEO GENERATED=NO"
echo "FFMPEG EXECUTED=NO"
echo "RENDERER MODIFIED=NO"
