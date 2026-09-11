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
