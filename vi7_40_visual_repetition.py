#!/usr/bin/env python3

VERSION = "7.40"

def detect(sequence):
    warnings = []

    categories = [
        x.get("category")
        for x in sequence
    ]

    shots = [
        x.get("shot")
        for x in sequence
    ]

    for index in range(
        len(sequence) - 2
    ):
        c = categories[index:index+3]
        s = shots[index:index+3]

        if len(set(c)) == 1 and c[0]:
            warnings.append({
                "type": "category_triple",
                "scenes": [
                    sequence[index+j]["scene"]
                    for j in range(3)
                ],
                "value": c[0],
            })

        if len(set(s)) == 1 and s[0]:
            warnings.append({
                "type": "shot_triple",
                "scenes": [
                    sequence[index+j]["scene"]
                    for j in range(3)
                ],
                "value": s[0],
            })

    return {
        "version": VERSION,
        "warnings": warnings,
        "count": len(warnings),
    }

def self_test():
    sample = [
        {
            "scene": 1,
            "category": "DOCUMENT",
            "shot": "medium",
        },
        {
            "scene": 2,
            "category": "DOCUMENT",
            "shot": "medium",
        },
        {
            "scene": 3,
            "category": "DOCUMENT",
            "shot": "medium",
        },
    ]

    assert detect(sample)["count"] == 2

    print("VI7.40 VISUAL REPETITION=PASS")

if __name__ == "__main__":
    self_test()
