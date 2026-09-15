#!/usr/bin/env python3

VERSION = "8.73"


def classify(name):
    low = str(name or "").lower()

    if any(
        token in low
        for token in (
            "download",
            "baixar",
        )
    ):
        return "DOWNLOAD"

    if any(
        token in low
        for token in (
            "search",
            "buscar",
            "busca",
            "query",
        )
    ):
        return "SEARCH"

    if any(
        token in low
        for token in (
            "source",
            "provider",
            "fonte",
        )
    ):
        return "SOURCE_ROUTING"

    if any(
        token in low
        for token in (
            "image",
            "imagem",
            "media",
            "midia",
        )
    ):
        return "MEDIA"

    return "OTHER"


def self_test():
    assert (
        classify(
            "search_images"
        )
        == "SEARCH"
    )

    assert (
        classify(
            "download_media"
        )
        == "DOWNLOAD"
    )

    print(
        "VI8.73 SEARCH FUNCTION CLASSIFIER=PASS"
    )


if __name__ == "__main__":
    self_test()
