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
