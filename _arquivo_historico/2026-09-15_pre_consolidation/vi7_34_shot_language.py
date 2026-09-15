#!/usr/bin/env python3

VERSION = "7.34"

PREFERRED = {
    "FACE": ("medium","close_up"),
    "DOCUMENT": ("close_up","medium"),
    "EVIDENCE": ("close_up","medium"),
    "LOCATION": ("wide","medium"),
    "OBJECT": ("close_up","medium"),
    "ABSTRACT": ("medium","wide"),
    "GENERAL": ("medium",),
}

def normalize(value):
    value = str(value or "").lower().strip()

    aliases = {
        "closeup": "close_up",
        "close-up": "close_up",
        "close": "close_up",
    }

    return aliases.get(
        value,
        value
    )

def evaluate(category, shot):
    shot = normalize(shot)

    preferred = PREFERRED.get(
        category,
        ("medium",)
    )

    return {
        "version": VERSION,
        "category": category,
        "shot": shot,
        "preferred": preferred,
        "match": shot in preferred,
    }

def self_test():
    assert evaluate(
        "LOCATION",
        "wide"
    )["match"]

    print("VI7.34 SHOT LANGUAGE=PASS")

if __name__ == "__main__":
    self_test()
