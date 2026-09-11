#!/usr/bin/env python3

import re

VERSION = "8.04"

STOP = {
    "the","a","an","of","to","and","or",
    "de","da","do","das","dos","e","em",
    "um","uma","para","com","que",
}

def words(text):
    return {
        token
        for token in re.findall(
            r"[a-zA-ZÀ-ÿ0-9]+",
            str(text or "").lower()
        )
        if (
            len(token) >= 3
            and token not in STOP
        )
    }

def evaluate(scene, candidate):
    scene_text = " ".join([
        str(scene.get("segment") or ""),
        str(scene.get("query") or ""),
        " ".join(
            str(x)
            for x in (
                scene.get("must_have")
                or []
            )
        ),
    ])

    media_text = " ".join([
        str(
            candidate.get(
                "query"
            )
            or ""
        ),
        str(
            (
                candidate.get(
                    "metadata"
                )
                or {}
            ).get(
                "title"
            )
            or ""
        ),
        str(
            (
                candidate.get(
                    "metadata"
                )
                or {}
            ).get(
                "description"
            )
            or ""
        ),
    ])

    a = words(scene_text)
    b = words(media_text)

    if not a:
        return {
            "version": VERSION,
            "score": 50.0,
            "overlap": [],
        }

    overlap = sorted(
        a & b
    )

    ratio = (
        len(overlap)
        / len(a)
    )

    score = min(
        100.0,
        40 + ratio * 80
    )

    return {
        "version": VERSION,
        "score": round(
            score,
            2
        ),
        "overlap": overlap,
    }

def self_test():
    result = evaluate(
        {
            "segment":
                "a ransom note was found",
            "query":
                "handwritten ransom note",
        },
        {
            "query":
                "ransom note handwritten paper",
            "metadata": {},
        }
    )

    assert result["score"] > 50

    print(
        "VI8.04 NARRATIVE RELEVANCE=PASS"
    )

if __name__ == "__main__":
    self_test()
