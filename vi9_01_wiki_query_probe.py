#!/usr/bin/env python3

import re
from vi9_wiki_search_adapter import wiki_search


VISUAL_TERMS = {
    "portrait",
    "clear",
    "face",
    "medium",
    "shot",
    "close",
    "wide",
    "detail",
    "documentary",
    "photograph",
    "photo",
    "image",
    "dark",
    "shadows",
    "shadow",
}


def clean_query(text):
    words = re.findall(
        r"[A-Za-zÀ-ÿ0-9'-]+",
        str(text or "")
    )

    cleaned = [
        word
        for word in words
        if word.lower()
        not in VISUAL_TERMS
    ]

    return " ".join(cleaned)


def variants(query):
    base = clean_query(query)

    words = base.split()

    candidates = [
        query,
        base,
        " ".join(words[:6]),
        " ".join(words[:4]),
        " ".join(words[:3]),
    ]

    result = []
    seen = set()

    for item in candidates:
        item = item.strip()

        key = item.lower()

        if (
            item
            and key not in seen
        ):
            seen.add(key)
            result.append(item)

    return result


if __name__ == "__main__":

    original = (
        "person hiding corner dark hallway "
        "shadows portrait clear face medium"
    )

    print("===== VI9.01 WIKI QUERY INTELLIGENCE =====")
    print("ORIGINAL:", original)
    print()

    attempts = variants(original)

    winner = None

    for index, query in enumerate(
        attempts,
        start=1
    ):
        print(
            f"PROBE {index}:",
            query
        )

        try:
            results = wiki_search(
                query,
                limit=5
            )

        except Exception as exc:
            print(
                "  ERROR:",
                type(exc).__name__,
                str(exc)[:300]
            )
            continue

        print(
            "  RESULTS:",
            len(results)
        )

        for n, item in enumerate(
            results[:3],
            start=1
        ):
            print(
                f"    {n}.",
                item.get("title")
            )

        if results and winner is None:
            winner = {
                "query": query,
                "results": results,
            }

        print()

    print("===== RESULT =====")

    if winner:
        print(
            "STATUS: QUERY_ROUTE_FOUND"
        )

        print(
            "WINNING QUERY:",
            winner["query"]
        )

        print(
            "RESULT COUNT:",
            len(
                winner["results"]
            )
        )

    else:
        print(
            "STATUS: WIKI_NOT_SUITABLE_FOR_THIS_SCENE"
        )

    print()
    print("DOWNLOAD EXECUTED: False")
    print("MEDIA MUTATED: False")
    print("FFMPEG EXECUTED: False")
    print("VIDEO GENERATED: False")
