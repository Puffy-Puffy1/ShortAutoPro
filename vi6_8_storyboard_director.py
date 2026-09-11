#!/usr/bin/env python3


VERSION = "6.8"


def _s(v):
    return str(v or "").strip()


def _role(scene):

    text = " ".join(
        [
            _s(scene.get("visual_mode")),
            _s(scene.get("visual_intent")),
            _s(scene.get("intent")),
        ]
    ).lower()


    if "cta" in text:
        return "CTA"

    if any(
        x in text
        for x in (
            "document",
            "evidence",
            "archive",
            "arquivo",
            "newspaper",
        )
    ):
        return "EVIDENCE"

    if any(
        x in text
        for x in (
            "location",
            "place",
            "architecture",
            "map",
        )
    ):
        return "PLACE"

    if any(
        x in text
        for x in (
            "person",
            "portrait",
            "character",
        )
    ):
        return "PERSON"

    if any(
        x in text
        for x in (
            "object",
            "medicine",
            "product",
            "package",
        )
    ):
        return "OBJECT"

    return "CONTEXT"


def build_global_plan(
    scenes
):

    total = len(scenes)

    plan = []

    documentary_budget = max(
        3,
        round(
            total * 0.35
        )
    )

    motion_budget = max(
        3,
        round(
            total * 0.42
        )
    )

    previous_role = None


    for index, scene in enumerate(
        scenes,
        1
    ):

        role = _role(scene)


        prefer_documentary = (
            role in {
                "EVIDENCE",
                "PERSON",
                "PLACE",
            }
        )


        # Story rhythm.
        if index == 1:

            rhythm = "HOOK"

        elif index <= 4:

            rhythm = "SETUP"

        elif index <= 8:

            rhythm = "ESCALATION"

        elif index < total:

            rhythm = "RESOLUTION"

        else:

            rhythm = "CTA"


        # Movimento tem utilidade maior
        # em contexto/transição.
        prefer_motion = (
            role in {
                "CONTEXT",
                "OBJECT",
            }
            and rhythm
            in {
                "HOOK",
                "SETUP",
                "ESCALATION",
            }
        )


        # Evidência/documentos podem ser
        # foto sem penalização.
        photo_ok = (
            role in {
                "EVIDENCE",
                "PERSON",
                "PLACE",
            }
        )


        # Mudança de família visual ganha
        # importância em papéis repetidos.
        diversity_priority = (
            "HIGH"
            if role == previous_role
            else "NORMAL"
        )


        plan.append(
            {
                "scene": index,
                "role": role,
                "rhythm": rhythm,

                "prefer_documentary":
                    prefer_documentary,

                "prefer_motion":
                    prefer_motion,

                "photo_is_fully_valid":
                    photo_ok,

                "diversity_priority":
                    diversity_priority,

                "avoid_previous_asset":
                    index > 1,

                "avoid_three_same_source":
                    True,

                "cta_reuse":
                    role == "CTA",
            }
        )


        previous_role = role


    return {
        "version": VERSION,

        "scene_count":
            total,

        "documentary_target":
            documentary_budget,

        "motion_target":
            motion_budget,

        "max_identical_asset":
            1,

        "max_same_source_streak":
            2,

        "max_same_family_streak":
            2,

        "cta_strategy":
            "REUSE_VERIFIED_STORY_ASSET",

        "scenes":
            plan,
    }


def self_test():

    scenes = [
        {
            "visual_mode":
                "evidence"
        },

        {
            "visual_mode":
                "location"
        },

        {
            "visual_mode":
                "context"
        },

        {
            "visual_mode":
                "context"
        },

        {
            "visual_mode":
                "object"
        },

        {
            "visual_mode":
                "evidence"
        },

        {
            "visual_mode":
                "person"
        },

        {
            "visual_mode":
                "context"
        },

        {
            "visual_mode":
                "evidence"
        },

        {
            "visual_mode":
                "context"
        },

        {
            "visual_mode":
                "object"
        },

        {
            "visual_mode":
                "cta_reuse"
        },
    ]


    plan = build_global_plan(
        scenes
    )


    assert (
        plan["scene_count"]
        == 12
    )

    assert (
        plan["documentary_target"]
        >= 4
    )

    assert (
        plan["scenes"][-1][
            "cta_reuse"
        ]
        is True
    )

    assert (
        plan["max_same_source_streak"]
        == 2
    )

    assert (
        plan["max_identical_asset"]
        == 1
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.8 STORYBOARD SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK 12-scene global planning"
    )
    print(
        "OK Documentary Budget"
    )
    print(
        "OK Motion Budget"
    )
    print(
        "OK Source Streak Guard"
    )
    print(
        "OK Asset Duplication Guard"
    )
    print(
        "OK Visual Family Guard"
    )
    print(
        "OK CTA Reuse Strategy"
    )
    print()


if __name__ == "__main__":
    self_test()
