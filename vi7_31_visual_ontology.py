#!/usr/bin/env python3

VERSION = "7.31"

RULES = {
    "FACE": (
        "portrait","girl","boy","woman","man","father",
        "mother","person","face","child"
    ),
    "DOCUMENT": (
        "document","letter","note","paper","newspaper",
        "clipping","passport","file","archive","calendar"
    ),
    "EVIDENCE": (
        "evidence","dna","cash","money","weapon",
        "forensic","crime scene","police tape"
    ),
    "LOCATION": (
        "house","building","street","basement",
        "corridor","hallway","room","city",
        "landscape","exterior","interior"
    ),
    "OBJECT": (
        "object","microphone","phone","camera",
        "equipment","notepad"
    ),
}

def classify(scene):
    text = " ".join(
        str(scene.get(k) or "")
        for k in (
            "segment","query","visual_mode","shot_type"
        )
    ).lower()

    scores = {
        category: sum(
            1 for token in tokens
            if token in text
        )
        for category, tokens in RULES.items()
    }

    best = max(scores, key=scores.get)

    if scores[best] == 0:
        mode = str(
            scene.get("visual_mode") or ""
        ).lower()

        fallback = {
            "document": "DOCUMENT",
            "evidence": "EVIDENCE",
            "location": "LOCATION",
            "architecture": "LOCATION",
            "object": "OBJECT",
            "abstract_context": "ABSTRACT",
        }

        return fallback.get(
            mode,
            "GENERAL"
        )

    return best

def self_test():
    assert classify({
        "query": "handwritten ransom note paper"
    }) == "DOCUMENT"

    assert classify({
        "query": "young girl portrait"
    }) == "FACE"

    print("VI7.31 VISUAL ONTOLOGY=PASS")

if __name__ == "__main__":
    self_test()
