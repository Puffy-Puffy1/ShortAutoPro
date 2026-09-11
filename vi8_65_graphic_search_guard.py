#!/usr/bin/env python3

VERSION = "8.65"

GRAPHIC = {
    "corpse",
    "dead body",
    "bloody body",
    "gore",
    "graphic wound",
    "autopsy photo",
    "severed",
}

SAFE_REPLACEMENTS = {
    "corpse":
        "crime scene",

    "dead body":
        "crime scene",

    "bloody body":
        "forensic scene",

    "gore":
        "forensic evidence",

    "graphic wound":
        "forensic evidence",

    "autopsy photo":
        "forensic archive",

    "severed":
        "forensic evidence",
}


def sanitize(query):
    original = str(
        query or ""
    )

    output = original

    removed = []

    for unsafe in GRAPHIC:
        if unsafe in output.lower():
            replacement = (
                SAFE_REPLACEMENTS[
                    unsafe
                ]
            )

            import re

            output = re.sub(
                re.escape(unsafe),
                replacement,
                output,
                flags=re.I
            )

            removed.append(
                unsafe
            )

    return {
        "version": VERSION,
        "original": original,
        "query": output,
        "changed":
            output != original,
        "removed_terms":
            sorted(removed),
    }


def self_test():
    result = sanitize(
        "crime dead body basement"
    )

    assert (
        "dead body"
        not in result[
            "query"
        ].lower()
    )

    print(
        "VI8.65 GRAPHIC SEARCH GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
