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
