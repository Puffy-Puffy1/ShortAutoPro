#!/usr/bin/env python3

import json
import re
import time
from pathlib import Path

import requests


VERSION = "90.00"

BASE = Path.home() / "ShortAutoPro"

VI80 = (
    BASE / "logs/producao/"
    "vi80_00_context_first_global_search_latest.json"
)

VI70 = (
    BASE / "logs/producao/"
    "vi70_00_global_visual_casting_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi90_00_resilient_provider_orchestrator_latest.json"
)

COMMONS = (
    "https://commons.wikimedia.org/w/api.php"
)

ARCHIVE = (
    "https://archive.org/advancedsearch.php"
)

HEADERS = {
    "User-Agent":
        "ShortAutoPro/90.00 "
        "(resilient metadata research)"
}


MAX_RESULTS = 12
MAX_RETRIES = 4

MIN_CONTEXT = 28
MIN_SEMANTIC = 26
MIN_SCORE = 60

_cache = {}


STOP = {
    "the", "and", "for", "with", "from",
    "this", "that", "into", "about",
    "photo", "image", "video",
    "documentary", "cinematic",
    "medium", "wide", "close",
    "shot", "clear", "scene",
    "person", "people",
}


def load_gate(path):
    if not path.exists():
        return {}

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return data.get(
        "gate",
        data
    )


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


def request_json(
    provider,
    url,
    params,
    timeout
):
    key = (
        provider,
        tuple(
            sorted(
                (
                    str(k),
                    str(v)
                )
                for k, v
                in params.items()
            )
        )
    )

    if key in _cache:
        return {
            "status": "CACHE",
            "data": _cache[key],
            "attempts": 0,
        }

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

        except Exception as exc:
            if attempt == MAX_RETRIES:
                return {
                    "status":
                        "ERROR",

                    "reason":
                        type(exc).__name__
                        + ": "
                        + str(exc)[:180],

                    "attempts":
                        attempt,
                }

            time.sleep(wait)
            wait = min(
                wait * 2,
                30
            )
            continue

        if r.status_code == 429:
            retry = r.headers.get(
                "Retry-After"
            )

            try:
                retry = int(retry)
            except Exception:
                retry = wait

            retry = max(
                5,
                min(
                    retry,
                    45
                )
            )

            if attempt == MAX_RETRIES:
                return {
                    "status":
                        "RATE_LIMITED",

                    "reason":
                        "HTTP 429",

                    "attempts":
                        attempt,
                }

            time.sleep(retry)

            wait = min(
                wait * 2,
                45
            )

            continue

        if r.status_code in {
            500, 502, 503, 504
        }:
            if attempt == MAX_RETRIES:
                return {
                    "status":
                        "ERROR",

                    "reason":
                        f"HTTP {r.status_code}",

                    "attempts":
                        attempt,
                }

            time.sleep(wait)

            wait = min(
                wait * 2,
                30
            )

            continue

        try:
            r.raise_for_status()
            data = r.json()

        except Exception as exc:
            return {
                "status":
                    "ERROR",

                "reason":
                    type(exc).__name__
                    + ": "
                    + str(exc)[:180],

                "attempts":
                    attempt,
            }

        _cache[key] = data

        return {
            "status":
                "OK",

            "data":
                data,

            "attempts":
                attempt,
        }

    return {
        "status":
            "ERROR",

        "reason":
            "unexpected_retry_exit",

        "attempts":
            MAX_RETRIES,
    }


def commons_search(query):
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

    result = request_json(
        "COMMONS",
        COMMONS,
        params,
        20
    )

    if result[
        "status"
    ] not in {
        "OK",
        "CACHE",
    }:
        return result

    pages = (
        result["data"]
        .get("query", {})
        .get("pages", [])
    )

    return {
        **result,
        "pages": pages,
    }


def archive_search(query):
    params = {
        "q":
            f'({query}) AND mediatype:movies',

        "fl[]":
            "identifier,title,description,licenseurl,creator",

        "rows":
            MAX_RESULTS,

        "page":
            1,

        "output":
            "json",
    }

    result = request_json(
        "ARCHIVE",
        ARCHIVE,
        params,
        25
    )

    if result[
        "status"
    ] not in {
        "OK",
        "CACHE",
    }:
        return result

    docs = (
        result["data"]
        .get("response", {})
        .get("docs", [])
    )

    return {
        **result,
        "docs": docs,
    }


def factual_variants(queries):
    result = []
    seen = set()

    for q in queries:
        parts = [
            x
            for x in words(q)
            if x.lower()
            not in {
                "dark",
                "mysterious",
                "vintage",
                "old",
                "historic",
                "view",
                "background",
                "foreground",
            }
        ]

        variants = [
            q,
            " ".join(parts),
            " ".join(parts[:5]),
            " ".join(parts[:3]),
        ]

        for v in variants:
            v = v.strip()

            if not v:
                continue

            key = v.lower()

            if key in seen:
                continue

            seen.add(key)
            result.append(v)

    return result[:5]


def commons_candidate_count(
    query,
    desired
):
    result = commons_search(
        query
    )

    if result[
        "status"
    ] not in {
        "OK",
        "CACHE",
    }:
        return {
            "status":
                result["status"],

            "count":
                0,

            "qualified":
                0,

            "reason":
                result.get(
                    "reason"
                ),
        }

    wanted = (
        "IMAGE"
        if desired
        == "ARCHIVAL_IMAGE"
        else desired
    )

    count = 0

    for page in result[
        "pages"
    ]:
        info_list = (
            page.get(
                "imageinfo"
            )
            or []
        )

        if not info_list:
            continue

        info = info_list[0]

        mime = str(
            info.get("mime")
            or ""
        ).lower()

        mediatype = str(
            info.get(
                "mediatype"
            )
            or ""
        ).lower()

        family = (
            "VIDEO"
            if (
                mime.startswith(
                    "video/"
                )
                or mediatype
                == "video"
            )
            else "IMAGE"
        )

        if family == wanted:
            count += 1

    return {
        "status":
            result["status"],

        "count":
            count,

        "qualified":
            count,

        "reason":
            None,
    }


def archive_candidate_count(query):
    result = archive_search(
        query
    )

    if result[
        "status"
    ] not in {
        "OK",
        "CACHE",
    }:
        return {
            "status":
                result["status"],

            "count":
                0,

            "reason":
                result.get(
                    "reason"
                ),
        }

    return {
        "status":
            result["status"],

        "count":
            len(
                result["docs"]
            ),

        "reason":
            None,
    }


def route_scene(item):
    scene = item.get(
        "scene"
    )

    desired = item.get(
        "desired_family"
    )

    queries = factual_variants(
        item.get(
            "queries"
        )
        or []
    )

    attempts = []

    total_candidates = 0

    commons_rate_limited = False

    for query in queries:
        if desired in {
            "IMAGE",
            "ARCHIVAL_IMAGE",
        }:
            c = commons_candidate_count(
                query,
                desired
            )

            attempts.append({
                "provider":
                    "COMMONS",

                "query":
                    query,

                **c,
            })

            total_candidates += (
                c["count"]
            )

            if c[
                "status"
            ] == "RATE_LIMITED":
                commons_rate_limited = True
                break

        elif desired == "VIDEO":
            a = archive_candidate_count(
                query
            )

            attempts.append({
                "provider":
                    "ARCHIVE",

                "query":
                    query,

                **a,
            })

            total_candidates += (
                a["count"]
            )

            # Commons only as secondary video
            # source, and only while healthy.
            if (
                a["count"] == 0
                and not commons_rate_limited
            ):
                c = commons_candidate_count(
                    query,
                    "VIDEO"
                )

                attempts.append({
                    "provider":
                        "COMMONS",

                    "query":
                        query,

                    **c,
                })

                total_candidates += (
                    c["count"]
                )

                if c[
                    "status"
                ] == "RATE_LIMITED":
                    commons_rate_limited = True

        if total_candidates > 0:
            break

        time.sleep(.7)

    if total_candidates > 0:
        decision = (
            "PROVIDER_ROUTE_RECOVERED"
        )

    elif commons_rate_limited:
        decision = (
            "KEEP_CURRENT_RATE_LIMIT_SAFE"
        )

    else:
        decision = (
            "KEEP_CURRENT_NO_PROVIDER_RESULT"
        )

    return {
        "scene":
            scene,

        "desired_family":
            desired,

        "queries":
            queries,

        "attempts":
            attempts,

        "total_candidates":
            total_candidates,

        "decision":
            decision,
    }


def evaluate():
    vi80 = load_gate(
        VI80
    )

    vi70 = load_gate(
        VI70
    )

    if not vi80:
        raise RuntimeError(
            "vi80_missing"
        )

    inputs = (
        vi80.get(
            "results"
        )
        or []
    )

    results = [
        route_scene(
            item
        )
        for item in inputs
    ]

    recovered = [
        x["scene"]
        for x in results
        if x[
            "decision"
        ]
        == "PROVIDER_ROUTE_RECOVERED"
    ]

    rate_safe = [
        x["scene"]
        for x in results
        if x[
            "decision"
        ]
        == "KEEP_CURRENT_RATE_LIMIT_SAFE"
    ]

    blockers = []

    warnings = []

    if rate_safe:
        warnings.append(
            "commons_rate_limit_safely_handled"
        )

    status = (
        "HOLD"
        if blockers
        else
        "VI90_RESILIENT_PROVIDER_ORCHESTRATOR_CERTIFIED"
    )

    report = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            vi80.get(
                "short_id"
            ),

        "recovered_scenes":
            recovered,

        "rate_limit_safe_scenes":
            rate_safe,

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
        " VI90 RESILIENT PROVIDER ORCHESTRATOR"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "RECOVERED SCENES:",
        r[
            "recovered_scenes"
        ]
    )

    print(
        "RATE-LIMIT SAFE:",
        r[
            "rate_limit_safe_scenes"
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

    for x in r[
        "results"
    ]:
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
            x["decision"]
        )

        print(
            " TOTAL CANDIDATES:",
            x[
                "total_candidates"
            ]
        )

        for a in x[
            "attempts"
        ]:
            print(
                "  ",
                a[
                    "provider"
                ],
                "|",
                a["query"],
                "| status=",
                a["status"],
                "| count=",
                a["count"],
                "| reason=",
                a.get(
                    "reason"
                ),
            )

        print()

    print(
        "NETWORK EXECUTED:",
        r[
            "network_executed"
        ]
    )

    print(
        "DOWNLOAD EXECUTED:",
        r[
            "download_executed"
        ]
    )

    print(
        "PRODUCTION MEDIA MUTATED:",
        r[
            "production_media_mutated"
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
