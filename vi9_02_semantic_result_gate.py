#!/usr/bin/env python3

import re

from vi9_wiki_search_adapter import wiki_search


VERSION = "9.02"

STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "at",
    "to", "for", "from", "with", "and", "or",
    "person", "people",
    "portrait", "photo", "photograph", "image",
    "shot", "medium", "wide", "close", "detail",
    "clear", "cinematic", "documentary",
    "dark", "moody",
}


def tokens(text):
    return {
        x.lower()
        for x in re.findall(
            r"[A-Za-zÀ-ÿ0-9'-]+",
            str(text or "")
        )
        if (
            len(x) >= 3
            and x.lower() not in STOPWORDS
        )
    }


def result_text(item):
    parts = []

    for key in (
        "title",
        "snippet",
        "description"
    ):
        value = item.get(key)

        if isinstance(value, str):
            parts.append(value)

    return " ".join(parts)


def score_result(query, item):

    q = tokens(query)
    r = tokens(
        result_text(item)
    )

    if not q:
        return {
            "score": 0.0,
            "shared": [],
            "query_tokens": [],
        }

    shared = q & r

    coverage = (
        len(shared)
        / len(q)
    )

    title_tokens = tokens(
        item.get("title", "")
    )

    title_shared = (
        q & title_tokens
    )

    title_bonus = min(
        0.30,
        len(title_shared) * 0.15
    )

    score = min(
        1.0,
        coverage + title_bonus
    )

    return {
        "score": round(
            score,
            3
        ),
        "shared": sorted(shared),
        "query_tokens": sorted(q),
        "title_shared": sorted(
            title_shared
        ),
    }


def evaluate_query(
    query,
    limit=5,
    threshold=0.34
):

    results = wiki_search(
        query,
        limit=limit
    )

    evaluated = []

    for item in results:

        evaluation = score_result(
            query,
            item
        )

        evaluated.append({
            "title":
                item.get("title"),

            "score":
                evaluation["score"],

            "shared":
                evaluation["shared"],

            "title_shared":
                evaluation["title_shared"],

            "accepted":
                evaluation["score"]
                >= threshold,
        })

    evaluated.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    accepted = [
        x
        for x in evaluated
        if x["accepted"]
    ]

    return {
        "query": query,
        "raw_count": len(results),
        "accepted_count":
            len(accepted),
        "accepted": accepted,
        "all": evaluated,
    }


def main():

    queries = [
        (
            "person hiding corner dark hallway "
            "shadows portrait clear face medium"
        ),
        "person hiding corner hallway",
        "person hiding corner",
    ]

    print(
        "===== VI9.02 SEMANTIC RESULT GATE ====="
    )

    winner = None

    for index, query in enumerate(
        queries,
        start=1
    ):

        print()
        print(
            f"PROBE {index}:",
            query
        )

        try:
            report = evaluate_query(
                query
            )

        except Exception as exc:
            print(
                "ERROR:",
                type(exc).__name__,
                str(exc)[:300]
            )
            continue

        print(
            "RAW RESULTS:",
            report["raw_count"]
        )

        print(
            "SEMANTICALLY ACCEPTED:",
            report["accepted_count"]
        )

        for item in report["all"][:5]:

            print(
                " ",
                f'{item["score"]:.3f}',
                "PASS"
                if item["accepted"]
                else "REJECT",
                "|",
                item["title"],
                "| shared=",
                item["shared"]
            )

        if (
            winner is None
            and report[
                "accepted_count"
            ] > 0
        ):
            winner = report

    print()
    print(
        "===== VI9.02 DECISION ====="
    )

    if winner:

        print(
            "STATUS: SEMANTIC_ROUTE_FOUND"
        )

        print(
            "QUERY:",
            winner["query"]
        )

        print(
            "ACCEPTED:",
            winner[
                "accepted_count"
            ]
        )

    else:

        print(
            "STATUS: WIKIPEDIA_ROUTE_REJECTED"
        )

        print(
            "REASON: "
            "no_semantically_relevant_result"
        )

    print()
    print(
        "NETWORK EXECUTED: True"
    )
    print(
        "DOWNLOAD EXECUTED: False"
    )
    print(
        "MEDIA MUTATED: False"
    )
    print(
        "FFMPEG EXECUTED: False"
    )
    print(
        "VIDEO GENERATED: False"
    )


if __name__ == "__main__":
    main()
