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
