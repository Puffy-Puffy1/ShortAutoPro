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
