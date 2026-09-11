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
