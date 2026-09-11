#!/usr/bin/env python3

import json
import re
import time
from pathlib import Path

import requests


VERSION = "150.00"

BASE = Path.home() / "ShortAutoPro"

VI120 = (
    BASE / "logs/producao/"
    "vi120_00_query_intelligence_latest.json"
)

VI70 = (
    BASE / "logs/producao/"
    "vi70_00_global_visual_casting_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi150_00_query_tournament_latest.json"
)

COMMONS = "https://commons.wikimedia.org/w/api.php"
ARCHIVE = "https://archive.org/advancedsearch.php"

HEADERS = {
    "User-Agent":
        "ShortAutoPro/150.00 "
        "(query-tournament metadata research)"
}

MAX_QUERIES_PER_PROVIDER = 3
MAX_RESULTS = 12
MAX_RETRIES = 3

MIN_RESULT_RELEVANCE = 24
MIN_TOURNAMENT_SCORE = 40


STOP = {
    "the", "and", "for", "with",
    "from", "this", "that",
    "into", "about", "photo",
    "image", "video", "film",
    "footage", "location",
    "archive", "historical",
    "cinematic", "scene",
}


NEGATIVE = {
    "review",
    "reviews",
    "reaction",
    "podcast",
    "gameplay",
    "walkthrough",
    "audiobook",
    "creepypasta",
    "compilation",
    "commentary",
    "trailer",
    "teaser",
    "lyrics",
}


def load_gate(path):
    if not path.exists():
        return {}

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return data.get("gate", data)


def words(text):
    return re.findall(
        r"[A-Za-zÀ-ÿ0-9'-]+",
        str(text or "")
    )


def tokens(text):
    return {
        w.lower()
        for w in words(text)
        if (
            len(w) >= 3
            and w.lower() not in STOP
        )
    }


def similarity(a, b):
    aa = tokens(a)
    bb = tokens(b)

    if not aa:
        return 0.0

    shared = aa & bb

    if not shared:
        return 0.0

    score = (
        len(shared)
        / len(aa)
        * 100
    )

    if len(shared) == 1:
        score *= .55

    return round(
        min(100, score),
        2
    )


def negative_terms(text):
    low = str(text or "").lower()

    return sorted({
        x
        for x in NEGATIVE
        if x in low
    })


def get_json(
    url,
    params,
    timeout=25
):
    wait = 4

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):
        try:
            r = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=timeout
            )

            if r.status_code == 429:
                if attempt == MAX_RETRIES:
                    return {
                        "_status":
                            "RATE_LIMITED"
                    }

                retry = r.headers.get(
                    "Retry-After"
                )

                try:
                    retry = int(retry)
                except Exception:
                    retry = wait

                time.sleep(
                    max(
                        5,
                        min(
                            retry,
                            30
                        )
                    )
                )

                wait *= 2
                continue

            r.raise_for_status()

            data = r.json()
            data["_status"] = "OK"

            return data

        except Exception as exc:
            if attempt == MAX_RETRIES:
                return {
                    "_status":
                        "ERROR",

                    "_error":
                        type(exc).__name__
                        + ": "
                        + str(exc)[:180],
                }

            time.sleep(wait)

            wait = min(
                wait * 2,
                20
            )

    return {
        "_status":
            "ERROR"
    }


def commons_test(
    query,
    desired_family
):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": MAX_RESULTS,
        "prop": "imageinfo",
        "iiprop":
            "url|size|mime|mediatype|extmetadata",
        "format": "json",
        "formatversion": 2,
    }

    data = get_json(
        COMMONS,
        params
    )

    status = data.get(
        "_status",
        "ERROR"
    )

    if status != "OK":
        return {
            "provider":
                "COMMONS",

            "query":
                query,

            "status":
                status,

            "raw":
                0,

            "relevant":
                0,

            "best_relevance":
                0,

            "negative":
                0,

            "score":
                0,
        }

    pages = (
        data.get("query", {})
        .get("pages", [])
    )

    wanted = (
        "IMAGE"
        if desired_family
        == "ARCHIVAL_IMAGE"
        else desired_family
    )

    raw = 0
    relevant = 0
    negative_count = 0
    best = 0.0

    for page in pages:
        infos = (
            page.get("imageinfo")
            or []
        )

        if not infos:
            continue

        info = infos[0]

        mime = str(
            info.get("mime")
            or ""
        ).lower()

        mediatype = str(
            info.get("mediatype")
            or ""
        ).lower()

        family = (
            "VIDEO"
            if (
                mime.startswith("video/")
                or mediatype == "video"
            )
            else "IMAGE"
        )

        if family != wanted:
            continue

        raw += 1

        meta = (
            info.get("extmetadata")
            or {}
        )

        def mv(key):
            v = meta.get(key) or {}

            if isinstance(v, dict):
                return v.get("value") or ""

            return str(v or "")

        text = (
            str(page.get("title") or "")
            + " "
            + re.sub(
                r"<[^>]+>",
                " ",
                mv("ImageDescription")
            )
        )

        neg = negative_terms(text)

        if neg:
            negative_count += 1

        relevance = similarity(
            query,
            text
        )

        best = max(
            best,
            relevance
        )

        if (
            relevance
            >= MIN_RESULT_RELEVANCE
            and not neg
        ):
            relevant += 1

    precision = (
        relevant / raw * 100
        if raw
        else 0
    )

    score = (
        min(raw, 10) * 2
        + min(relevant, 8) * 8
        + precision * .35
        + best * .25
        - negative_count * 5
    )

    return {
        "provider":
            "COMMONS",

        "query":
            query,

        "status":
            "OK",

        "raw":
            raw,

        "relevant":
            relevant,

        "precision":
            round(
                precision,
                2
            ),

        "best_relevance":
            round(
                best,
                2
            ),

        "negative":
            negative_count,

        "score":
            round(
                max(0, score),
                2
            ),
    }


def archive_test(query):
    params = {
        "q":
            f'({query}) AND mediatype:movies',

        "fl[]":
            "identifier,title,description",

        "rows":
            MAX_RESULTS,

        "page":
            1,

        "output":
            "json",
    }

    data = get_json(
        ARCHIVE,
        params
    )

    status = data.get(
        "_status",
        "ERROR"
    )

    if status != "OK":
        return {
            "provider":
                "ARCHIVE",

            "query":
                query,

            "status":
                status,

            "raw":
                0,

            "relevant":
                0,

            "best_relevance":
                0,

            "negative":
                0,

            "score":
                0,
        }

    docs = (
        data.get("response", {})
        .get("docs", [])
    )

    raw = len(docs)
    relevant = 0
    negative_count = 0
    best = 0.0

    for doc in docs:
        description = (
            doc.get("description")
            or ""
        )

        if isinstance(
            description,
            list
        ):
            description = " ".join(
                str(x)
                for x in description
            )

        text = (
            str(doc.get("title") or "")
            + " "
            + str(description)
        )

        neg = negative_terms(text)

        if neg:
            negative_count += 1

        relevance = similarity(
            query,
            text
        )

        best = max(
            best,
            relevance
        )

        if (
            relevance
            >= MIN_RESULT_RELEVANCE
            and not neg
        ):
            relevant += 1

    precision = (
        relevant / raw * 100
        if raw
        else 0
    )

    score = (
        min(raw, 10) * 2
        + min(relevant, 8) * 8
        + precision * .35
        + best * .25
        - negative_count * 5
    )

    return {
        "provider":
            "ARCHIVE",

        "query":
            query,

        "status":
            "OK",

        "raw":
            raw,

        "relevant":
            relevant,

        "precision":
            round(
                precision,
                2
            ),

        "best_relevance":
            round(
                best,
                2
            ),

        "negative":
            negative_count,

        "score":
            round(
                max(0, score),
                2
            ),
    }


def evaluate_scene(item):
    scene = int(
        item["scene"]
    )

    desired = item.get(
        "desired_family"
    )

    commons_queries = [
        x["query"]
        for x in (
            item.get(
                "commons_queries"
            )
            or []
        )[
            :MAX_QUERIES_PER_PROVIDER
        ]
    ]

    archive_queries = [
        x["query"]
        for x in (
            item.get(
                "archive_queries"
            )
            or []
        )[
            :MAX_QUERIES_PER_PROVIDER
        ]
    ]

    tests = []

    for query in commons_queries:
        tests.append(
            commons_test(
                query,
                desired
            )
        )

        time.sleep(.8)

    if desired == "VIDEO":
        for query in archive_queries:
            tests.append(
                archive_test(
                    query
                )
            )

            time.sleep(.8)

    valid = [
        x
        for x in tests
        if x["status"] == "OK"
    ]

    valid.sort(
        key=lambda x: (
            x["score"],
            x.get(
                "precision",
                0
            ),
            x["relevant"],
            x["best_relevance"],
        ),
        reverse=True
    )

    winner = (
        valid[0]
        if valid
        and valid[0][
            "score"
        ] >= MIN_TOURNAMENT_SCORE
        and valid[0][
            "relevant"
        ] > 0
        else None
    )

    provider_errors = [
        x
        for x in tests
        if x["status"]
        not in {
            "OK"
        }
    ]

    return {
        "scene":
            scene,

        "category":
            item.get(
                "category"
            ),

        "desired_family":
            desired,

        "original_query":
            item.get(
                "original_query"
            ),

        "tests":
            tests,

        "winner":
            winner,

        "decision":
            (
                "QUERY_WINNER_FOUND"
                if winner
                else
                "NO_STRONG_QUERY"
            ),

        "provider_errors":
            provider_errors,
    }


def evaluate():
    vi120 = load_gate(
        VI120
    )

    if not vi120:
        raise RuntimeError(
            "vi120_missing"
        )

    inputs = (
        vi120.get(
            "results"
        )
        or []
    )

    results = []

    for item in inputs:
        results.append(
            evaluate_scene(
                item
            )
        )

    winning_scenes = [
        x["scene"]
        for x in results
        if x[
            "decision"
        ]
        == "QUERY_WINNER_FOUND"
    ]

    winners = {
        str(x["scene"]):
            x["winner"]
        for x in results
        if x.get("winner")
    }

    total_queries = sum(
        len(x["tests"])
        for x in results
    )

    total_relevant = sum(
        sum(
            t.get(
                "relevant",
                0
            )
            for t in x["tests"]
        )
        for x in results
    )

    rate_limited = [
        {
            "scene":
                x["scene"],

            "provider":
                t["provider"],

            "query":
                t["query"],
        }
        for x in results
        for t in x["tests"]
        if t["status"]
        == "RATE_LIMITED"
    ]

    blockers = []

    warnings = []

    if rate_limited:
        warnings.append(
            "provider_rate_limit_encountered"
        )

    if not winning_scenes:
        warnings.append(
            "no_strong_query_winners"
        )

    status = (
        "HOLD"
        if blockers
        else
        "VI150_QUERY_TOURNAMENT_CERTIFIED"
    )

    report = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            vi120.get(
                "short_id"
            ),

        "evaluated_scenes":
            [
                x["scene"]
                for x in results
            ],

        "winning_scenes":
            winning_scenes,

        "winners":
            winners,

        "total_queries_tested":
            total_queries,

        "total_relevant_results":
            total_relevant,

        "results":
            results,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "network_executed":
            bool(results),

        "download_executed":
            False,

        "production_media_mutated":
            False,

        "production_plan_mutated":
            False,

        "automatic_replace":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "source_recovery":
            "SHADOW_ONLY",
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUT.write_text(
        json.dumps(
            {"gate": report},
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return report


if __name__ == "__main__":
    r = evaluate()

    print()
    print(
        "=============================================="
    )
    print(
        " VI150 QUERY TOURNAMENT"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "EVALUATED:",
        r[
            "evaluated_scenes"
        ]
    )

    print(
        "WINNING SCENES:",
        r[
            "winning_scenes"
        ]
    )

    print(
        "QUERIES TESTED:",
        r[
            "total_queries_tested"
        ]
    )

    print(
        "RELEVANT RESULTS:",
        r[
            "total_relevant_results"
        ]
    )

    print(
        "BLOCKERS:",
        r["blockers"]
    )

    print(
        "WARNINGS:",
        r["warnings"]
    )

    print()

    for x in r["results"]:
        print(
            "SCENE:",
            x["scene"]
        )

        print(
            " DESIRED:",
            x[
                "desired_family"
            ]
        )

        print(
            " DECISION:",
            x[
                "decision"
            ]
        )

        for test in sorted(
            x["tests"],
            key=lambda z:
                z["score"],
            reverse=True
        ):
            print(
                "  ",
                test["provider"],
                "| score=",
                test["score"],
                "| raw=",
                test["raw"],
                "| relevant=",
                test["relevant"],
                "| precision=",
                test.get(
                    "precision"
                ),
                "| best=",
                test[
                    "best_relevance"
                ],
                "|",
                test["query"],
            )

        winner = x.get(
            "winner"
        )

        if winner:
            print(
                " WINNER:",
                winner[
                    "provider"
                ],
                "|",
                winner[
                    "query"
                ],
                "| SCORE:",
                winner[
                    "score"
                ]
            )

        print()

    print(
        "NETWORK EXECUTED:",
        r["network_executed"]
    )

    print(
        "DOWNLOAD EXECUTED:",
        r["download_executed"]
    )

    print(
        "PRODUCTION MEDIA MUTATED:",
        r[
            "production_media_mutated"
        ]
    )

    print(
        "AUTOMATIC REPLACE:",
        r[
            "automatic_replace"
        ]
    )

    print(
        "FFMPEG EXECUTED:",
        r[
            "ffmpeg_executed"
        ]
    )

    print(
        "VIDEO GENERATED:",
        r[
            "video_generated"
        ]
    )
