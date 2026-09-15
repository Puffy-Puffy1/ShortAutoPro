#!/usr/bin/env python3

VERSION = "8.74"

PROVIDERS = {
    "WIKIMEDIA": (
        "wikimedia",
        "commons.wikimedia",
    ),

    "WIKIPEDIA": (
        "wikipedia.org",
        "wikipedia",
    ),

    "PEXELS": (
        "pexels",
    ),

    "PIXABAY": (
        "pixabay",
    ),

    "UNSPLASH": (
        "unsplash",
    ),

    "GOOGLE": (
        "google",
    ),

    "BING": (
        "bing",
    ),

    "DUCKDUCKGO": (
        "duckduckgo",
    ),
}


def detect(text):
    low = str(
        text or ""
    ).lower()

    found = []

    for provider, terms in (
        PROVIDERS.items()
    ):
        if any(
            term in low
            for term in terms
        ):
            found.append(
                provider
            )

    return sorted(
        set(found)
    )


def self_test():
    assert (
        "WIKIMEDIA"
        in detect(
            "commons.wikimedia.org"
        )
    )

    print(
        "VI8.74 PROVIDER DETECTOR=PASS"
    )


if __name__ == "__main__":
    self_test()
