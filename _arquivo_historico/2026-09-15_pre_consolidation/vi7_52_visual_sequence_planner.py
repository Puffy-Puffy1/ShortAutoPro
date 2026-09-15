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
