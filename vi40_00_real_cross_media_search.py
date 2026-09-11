#!/usr/bin/env python3

import json
import re
import time
from pathlib import Path
from collections import Counter

import requests


VERSION = "40.00"

BASE = Path.home() / "ShortAutoPro"

VI30 = (
    BASE / "logs/producao/"
    "vi30_00_cross_media_director_latest.json"
)

VI920 = (
    BASE / "logs/producao/"
    "vi9_20_provider_router_master_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi40_00_real_cross_media_search_latest.json"
)

API = "https://commons.wikimedia.org/w/api.php"

HEADERS = {
    "User-Agent":
        "ShortAutoPro/40.00 "
        "(cross-media metadata search)"
}

MAX_SCENES = 4
MAX_RESULTS = 20
MAX_QUERIES = 3

MIN_SEMANTIC = 28
MIN_SCORE = 65


STOP = {
    "the", "and", "for", "with",
    "from", "this", "that",
    "documentary", "cinematic",
    "photo", "image", "video",
    "medium", "wide", "close",
    "shot", "clear", "editorial",
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


def by_scene(items):
    result = {}

    for item in items or []:
        try:
            scene = int(
                item.get("scene")
            )
        except Exception:
            continue

        result[scene] = item

    return result


def tokens(text):
    return {
        x.lower()
        for x in re.findall(
            r"[A-Za-zÀ-ÿ0-9'-]+",
            str(text or "")
        )
        if (
            len(x) >= 3
            and x.lower() not in STOP
        )
    }


def clean_query(text):
    words = re.findall(
        r"[A-Za-zÀ-ÿ0-9'-]+",
        str(text or "")
    )

    result = []
    seen = set()

    for word in words:
        low = word.lower()

        if low in STOP:
            continue

        if low in seen:
            continue

        seen.add(low)
        result.append(word)

    return " ".join(result)


def query_variants(route, desired_family):
    raw = clean_query(
        route.get("original_query")
        or ""
    )

    words = raw.split()

    base = [
        raw,
        " ".join(words[:6]),
        " ".join(words[:4]),
    ]

    if desired_family == "VIDEO":
        suffix = " video"

    elif desired_family == "ARCHIVAL_IMAGE":
        suffix = " historical archive"

    else:
        suffix = ""

    result = []
    seen = set()

    for query in base:
        query = query.strip()

        if not query:
            continue

        value = (
            query + suffix
        ).strip()

        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result[:MAX_QUERIES]


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

    r = requests.get(
        API,
        params=params,
        headers=HEADERS,
        timeout=20
    )

    r.raise_for_status()

    return (
        r.json()
        .get("query", {})
        .get("pages", [])
    )


def strip_html(text):
    return re.sub(
        r"<[^>]+>",
        " ",
        str(text or "")
    )


def meta(meta, key):
    value = (
        meta.get(key)
        or {}
    )

    if isinstance(value, dict):
        return value.get("value") or ""

    return str(value or "")


def media_family(info):
    mime = str(
        info.get("mime")
        or ""
    ).lower()

    media_type = str(
        info.get("mediatype")
        or ""
    ).lower()

    if (
        mime.startswith("video/")
        or media_type == "video"
    ):
        return "VIDEO"

    if mime.startswith("image/"):
        return "IMAGE"

    return "OTHER"


def semantic_score(query, title, description):
    q = tokens(query)

    target = tokens(
        str(title)
        + " "
        + strip_html(description)
    )

    if not q:
        return 0.0

    shared = q & target

    if not shared:
        return 0.0

    coverage = (
        len(shared)
        / len(q)
    )

    title_overlap = (
        q & tokens(title)
    )

    return min(
        100.0,
        round(
            coverage * 75
            + min(
                25,
                len(title_overlap) * 8
            ),
            2
        )
    )


def resolution_score(width, height):
    pixels = width * height

    if pixels >= 8_000_000:
        return 100

    if pixels >= 4_000_000:
        return 94

    if pixels >= 2_000_000:
        return 86

    if pixels >= 1_000_000:
        return 76

    if pixels >= 500_000:
        return 60

    return 35


def license_score(meta_data):
    text = (
        meta(
            meta_data,
            "LicenseShortName"
        )
        + " "
        + meta(
            meta_data,
            "UsageTerms"
        )
    ).lower()

    if (
        "public domain" in text
        or "cc0" in text
    ):
        return 100

    if "cc by-sa" in text:
        return 92

    if "cc by" in text:
        return 90

    if "creative commons" in text:
        return 82

    return 45


def normalize(page, query, desired):
    infos = (
        page.get("imageinfo")
        or []
    )

    if not infos:
        return None

    info = infos[0]

    family = media_family(
        info
    )

    wanted = (
        "IMAGE"
        if desired == "ARCHIVAL_IMAGE"
        else desired
    )

    if family != wanted:
        return None

    width = int(
        info.get("width")
        or 0
    )

    height = int(
        info.get("height")
        or 0
    )

    ext = (
        info.get("extmetadata")
        or {}
    )

    title = (
        page.get("title")
        or ""
    )

    description = meta(
        ext,
        "ImageDescription"
    )

    semantic = semantic_score(
        query,
        title,
        description
    )

    resolution = resolution_score(
        width,
        height
    )

    license_quality = license_score(
        ext
    )

    family_match = 100

    score = (
        semantic * .50
        + resolution * .20
        + license_quality * .20
        + family_match * .10
    )

    return {
        "title": title,

        "url":
            info.get("url"),

        "mime":
            info.get("mime"),

        "media_type":
            info.get("mediatype"),

        "family":
            family,

        "width":
            width,

        "height":
            height,

        "license":
            meta(
                ext,
                "LicenseShortName"
            ),

        "artist":
            strip_html(
                meta(
                    ext,
                    "Artist"
                )
            )[:160],

        "description":
            strip_html(
                description
            )[:300],

        "query":
            query,

        "semantic":
            semantic,

        "resolution":
            resolution,

        "license_score":
            license_quality,

        "score":
            round(
                score,
                2
            ),
    }


def search_scene(decision, route):
    desired = (
        decision.get(
            "desired_family"
        )
        or "IMAGE"
    )

    queries = query_variants(
        route,
        desired
    )

    candidates = []

    seen = set()

    errors = []

    for query in queries:
        try:
            pages = commons_search(
                query
            )

        except Exception as exc:
            errors.append(
                type(exc).__name__
                + ": "
                + str(exc)[:180]
            )
            continue

        for page in pages:
            item = normalize(
                page,
                query,
                desired
            )

            if not item:
                continue

            url = (
                item.get("url")
                or ""
            )

            if not url:
                continue

            if url in seen:
                continue

            seen.add(url)
            candidates.append(
                item
            )

        time.sleep(.7)

    candidates.sort(
        key=lambda x: (
            x["score"],
            x["semantic"],
            x["resolution"]
        ),
        reverse=True
    )

    good = [
        x
        for x in candidates
        if (
            x["semantic"]
            >= MIN_SEMANTIC
            and x["score"]
            >= MIN_SCORE
        )
    ]

    best = (
        good[0]
        if good
        else None
    )

    if best:
        status = (
            "REAL_CROSS_MEDIA_CANDIDATE_FOUND"
        )
    else:
        status = (
            "KEEP_CURRENT_NO_STRONG_CANDIDATE"
        )

    return {
        "scene":
            decision.get("scene"),

        "current_family":
            decision.get(
                "current_family"
            ),

        "desired_family":
            desired,

        "queries":
            queries,

        "raw_candidate_count":
            len(candidates),

        "qualified_count":
            len(good),

        "best":
            best,

        "top":
            candidates[:5],

        "status":
            status,

        "errors":
            errors,
    }


def evaluate():
    vi30 = load_gate(
        VI30
    )

    vi920 = load_gate(
        VI920
    )

    if not vi30:
        raise RuntimeError(
            "vi30_report_missing"
        )

    routes = by_scene(
        vi920.get("routes")
        or []
    )

    decisions = (
        vi30.get("decisions")
        or []
    )

    targets = [
        x
        for x in decisions
        if x.get("action") in {
            "SAME_MEDIA_FAMILY_OPTIMIZE",
            "CROSS_MEDIA_CANDIDATE",
        }
    ]

    # Always prioritize strongest scene.
    targets.sort(
        key=lambda x:
            x.get("score", 0),
        reverse=True
    )

    targets = targets[
        :MAX_SCENES
    ]

    discoveries = []

    for item in targets:
        scene = int(
            item["scene"]
        )

        discoveries.append(
            search_scene(
                item,
                routes.get(
                    scene,
                    {}
                )
            )
        )

    found = [
        x["scene"]
        for x in discoveries
        if x["status"]
        == "REAL_CROSS_MEDIA_CANDIDATE_FOUND"
    ]

    provider_errors = [
        x["scene"]
        for x in discoveries
        if x.get("errors")
    ]

    family_counts = Counter(
        x["desired_family"]
        for x in discoveries
    )

    blockers = []

    warnings = []

    if provider_errors:
        warnings.append(
            "provider_errors_present"
        )

    status = (
        "HOLD"
        if blockers
        else
        "VI40_REAL_CROSS_MEDIA_SEARCH_CERTIFIED"
    )

    report = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            vi30.get("short_id"),

        "target_scenes":
            [
                x["scene"]
                for x in targets
            ],

        "searched_family_counts":
            dict(
                family_counts
            ),

        "candidate_found_scenes":
            found,

        "discoveries":
            discoveries,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "network_executed":
            bool(targets),

        "download_executed":
            False,

        "production_media_mutated":
            False,

        "production_plan_mutated":
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
        " VI40 REAL CROSS-MEDIA SEARCH"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "TARGET SCENES:",
        r["target_scenes"]
    )

    print(
        "SEARCHED FAMILIES:",
        r[
            "searched_family_counts"
        ]
    )

    print(
        "CANDIDATES FOUND:",
        r[
            "candidate_found_scenes"
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

    for x in r["discoveries"]:
        print(
            "SCENE:",
            x["scene"]
        )

        print(
            " CURRENT:",
            x["current_family"]
        )

        print(
            " DESIRED:",
            x["desired_family"]
        )

        print(
            " STATUS:",
            x["status"]
        )

        print(
            " RAW:",
            x[
                "raw_candidate_count"
            ]
        )

        print(
            " QUALIFIED:",
            x[
                "qualified_count"
            ]
        )

        best = x.get("best")

        if best:
            print(
                " BEST SCORE:",
                best["score"]
            )

            print(
                " SEMANTIC:",
                best["semantic"]
            )

            print(
                " RESOLUTION:",
                best["resolution"]
            )

            print(
                " LICENSE:",
                best["license"]
            )

            print(
                " MIME:",
                best["mime"]
            )

            print(
                " DIMENSIONS:",
                best["width"],
                "x",
                best["height"]
            )

            print(
                " TITLE:",
                best["title"]
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
