#!/usr/bin/env python3

import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests


VERSION = "50.00"

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
    "vi50_00_multi_provider_video_latest.json"
)

COMMONS_API = (
    "https://commons.wikimedia.org/w/api.php"
)

ARCHIVE_API = (
    "https://archive.org/advancedsearch.php"
)

HEADERS = {
    "User-Agent":
        "ShortAutoPro/50.00 "
        "(metadata-only visual research)"
}

MAX_SCENES = 3
MAX_VARIANTS = 5

MIN_SEMANTIC = 32
MIN_TOTAL_SCORE = 62


STOP = {
    "the", "and", "for", "with",
    "from", "this", "that",
    "documentary", "cinematic",
    "editorial", "video",
    "footage", "photo", "image",
    "medium", "wide", "close",
    "shot", "clear", "dark",
    "shadow", "shadows",
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
    out = {}

    for item in items or []:
        try:
            scene = int(
                item.get("scene")
            )
        except Exception:
            continue

        out[scene] = item

    return out


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


def clean_query(text):
    seen = set()
    out = []

    for word in words(text):
        low = word.lower()

        if low in STOP:
            continue

        if low in seen:
            continue

        seen.add(low)
        out.append(word)

    return " ".join(out)


def query_variants(raw):
    cleaned = clean_query(raw)

    w = cleaned.split()

    variants = [
        cleaned,
        " ".join(w[:7]),
        " ".join(w[:5]),
        " ".join(w[:4]),
        " ".join(w[:3]),
    ]

    out = []
    seen = set()

    for q in variants:
        q = q.strip()

        if not q:
            continue

        key = q.lower()

        if key in seen:
            continue

        seen.add(key)
        out.append(q)

    return out[:MAX_VARIANTS]


def semantic_score(query, text):
    q = tokens(query)
    t = tokens(text)

    if not q:
        return 0.0

    shared = q & t

    if not shared:
        return 0.0

    coverage = (
        len(shared)
        / len(q)
    )

    score = coverage * 100

    if len(shared) == 1:
        score *= .65

    return round(
        min(100, score),
        2
    )


def commons_search(query):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 30,
        "prop": "imageinfo",
        "iiprop":
            "url|size|mime|mediatype|extmetadata",
        "format": "json",
        "formatversion": 2,
    }

    r = requests.get(
        COMMONS_API,
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


def commons_candidates(query):
    out = []

    for page in commons_search(query):
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

        if not (
            mime.startswith("video/")
            or mediatype == "video"
        ):
            continue

        meta = (
            info.get("extmetadata")
            or {}
        )

        def mv(key):
            value = (
                meta.get(key)
                or {}
            )

            if isinstance(value, dict):
                return (
                    value.get("value")
                    or ""
                )

            return str(value or "")

        title = (
            page.get("title")
            or ""
        )

        desc = re.sub(
            r"<[^>]+>",
            " ",
            mv("ImageDescription")
        )

        semantic = semantic_score(
            query,
            title + " " + desc
        )

        width = int(
            info.get("width")
            or 0
        )

        height = int(
            info.get("height")
            or 0
        )

        pixels = width * height

        if pixels >= 2_000_000:
            technical = 95
        elif pixels >= 1_000_000:
            technical = 82
        elif pixels >= 500_000:
            technical = 68
        else:
            technical = 50

        license_name = mv(
            "LicenseShortName"
        )

        license_text = (
            license_name
            + " "
            + mv("UsageTerms")
        ).lower()

        if (
            "public domain"
            in license_text
            or "cc0"
            in license_text
        ):
            license_score = 100

        elif (
            "cc by"
            in license_text
        ):
            license_score = 90

        else:
            license_score = 60

        score = (
            semantic * .55
            + technical * .20
            + license_score * .15
            + 90 * .10
        )

        out.append({
            "provider":
                "WIKIMEDIA_COMMONS",

            "query":
                query,

            "title":
                title,

            "description":
                desc[:350],

            "url":
                info.get("url"),

            "mime":
                mime,

            "width":
                width,

            "height":
                height,

            "license":
                license_name,

            "semantic":
                semantic,

            "technical":
                technical,

            "provider_trust":
                90,

            "score":
                round(score, 2),
        })

    return out


def archive_search(query):
    params = {
        "q":
            f'({query}) AND mediatype:movies',

        "fl[]": [
            "identifier",
            "title",
            "description",
            "licenseurl",
            "creator",
            "date",
        ],

        "rows": 30,
        "page": 1,
        "output": "json",
    }

    r = requests.get(
        ARCHIVE_API,
        params=params,
        headers=HEADERS,
        timeout=25
    )

    r.raise_for_status()

    return (
        r.json()
        .get("response", {})
        .get("docs", [])
    )


def archive_candidates(query):
    out = []

    for doc in archive_search(query):
        identifier = str(
            doc.get("identifier")
            or ""
        )

        if not identifier:
            continue

        title = str(
            doc.get("title")
            or ""
        )

        description = doc.get(
            "description"
        )

        if isinstance(
            description,
            list
        ):
            description = " ".join(
                str(x)
                for x in description
            )

        description = re.sub(
            r"<[^>]+>",
            " ",
            str(description or "")
        )

        semantic = semantic_score(
            query,
            title + " " + description
        )

        license_url = str(
            doc.get("licenseurl")
            or ""
        )

        if (
            "creativecommons"
            in license_url.lower()
        ):
            license_score = 85

        elif license_url:
            license_score = 65

        else:
            license_score = 45

        # At metadata-only stage we cannot
        # claim actual resolution.
        technical = 65

        provider_trust = 82

        score = (
            semantic * .60
            + technical * .15
            + license_score * .15
            + provider_trust * .10
        )

        out.append({
            "provider":
                "INTERNET_ARCHIVE",

            "query":
                query,

            "title":
                title,

            "description":
                description[:350],

            "identifier":
                identifier,

            "item_url":
                (
                    "https://archive.org/"
                    "details/"
                    + quote(identifier)
                ),

            "license":
                license_url,

            "semantic":
                semantic,

            "technical":
                technical,

            "provider_trust":
                provider_trust,

            "score":
                round(
                    score,
                    2
                ),
        })

    return out


def discover_scene(scene, route):
    raw = (
        route.get(
            "original_query"
        )
        or ""
    )

    variants = query_variants(
        raw
    )

    candidates = []

    errors = []

    seen = set()

    provider_counts = {
        "WIKIMEDIA_COMMONS": 0,
        "INTERNET_ARCHIVE": 0,
    }

    for query in variants:
        for provider_func in (
            commons_candidates,
            archive_candidates,
        ):
            try:
                found = provider_func(
                    query
                )

            except Exception as exc:
                errors.append(
                    {
                        "provider":
                            provider_func.__name__,

                        "query":
                            query,

                        "error":
                            type(exc).__name__
                            + ": "
                            + str(exc)[:180],
                    }
                )

                continue

            for item in found:
                key = (
                    item.get("url")
                    or item.get("identifier")
                    or (
                        item["provider"]
                        + "|"
                        + item["title"]
                    )
                )

                key = str(key)

                if key in seen:
                    continue

                seen.add(key)

                provider_counts[
                    item["provider"]
                ] += 1

                candidates.append(
                    item
                )

            time.sleep(.5)

    candidates.sort(
        key=lambda x: (
            x["score"],
            x["semantic"],
            x[
                "provider_trust"
            ]
        ),
        reverse=True
    )

    qualified = [
        x
        for x in candidates
        if (
            x["semantic"]
            >= MIN_SEMANTIC
            and x["score"]
            >= MIN_TOTAL_SCORE
        )
    ]

    best = (
        qualified[0]
        if qualified
        else None
    )

    # Provider agreement bonus:
    # if multiple providers return
    # semantically strong candidates,
    # confidence increases.
    strong_providers = {
        x["provider"]
        for x in qualified[:10]
    }

    if best:
        confidence = (
            best["score"]
        )

        if len(
            strong_providers
        ) >= 2:
            confidence = min(
                100,
                confidence + 6
            )

        decision = (
            "BETTER_VIDEO_CANDIDATE_FOUND"
        )

    else:
        confidence = 0

        decision = (
            "KEEP_CURRENT"
        )

    return {
        "scene":
            scene,

        "query_variants":
            variants,

        "provider_counts":
            provider_counts,

        "candidate_count":
            len(candidates),

        "qualified_count":
            len(qualified),

        "strong_providers":
            sorted(
                strong_providers
            ),

        "best":
            best,

        "top_candidates":
            qualified[:5],

        "decision":
            decision,

        "confidence":
            round(
                confidence,
                2
            ),

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
            "vi30_missing"
        )

    routes = by_scene(
        vi920.get("routes")
        or []
    )

    targets = [
        x
        for x in (
            vi30.get(
                "decisions"
            )
            or []
        )
        if (
            x.get(
                "desired_family"
            )
            == "VIDEO"
            and x.get(
                "action"
            )
            in {
                "SAME_MEDIA_FAMILY_OPTIMIZE",
                "CROSS_MEDIA_CANDIDATE",
            }
        )
    ]

    targets.sort(
        key=lambda x:
            x.get(
                "score",
                0
            ),
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
            discover_scene(
                scene,
                routes.get(
                    scene,
                    {}
                )
            )
        )

    found = [
        x["scene"]
        for x in discoveries
        if x[
            "decision"
        ]
        == "BETTER_VIDEO_CANDIDATE_FOUND"
    ]

    blockers = []

    warnings = []

    if any(
        x.get("errors")
        for x in discoveries
    ):
        warnings.append(
            "some_provider_errors"
        )

    status = (
        "HOLD"
        if blockers
        else
        "VI50_MULTI_PROVIDER_VIDEO_CERTIFIED"
    )

    result = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            vi30.get(
                "short_id"
            ),

        "target_scenes":
            [
                x["scene"]
                for x in targets
            ],

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
            {"gate": result},
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return result


if __name__ == "__main__":
    r = evaluate()

    print()
    print(
        "=============================================="
    )
    print(
        " VI50 MULTI-PROVIDER VIDEO DISCOVERY"
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
        "VIDEO CANDIDATES FOUND:",
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
            " DECISION:",
            x["decision"]
        )

        print(
            " CANDIDATES:",
            x[
                "candidate_count"
            ]
        )

        print(
            " QUALIFIED:",
            x[
                "qualified_count"
            ]
        )

        print(
            " PROVIDERS:",
            x[
                "provider_counts"
            ]
        )

        print(
            " STRONG PROVIDERS:",
            x[
                "strong_providers"
            ]
        )

        print(
            " CONFIDENCE:",
            x["confidence"]
        )

        best = x.get("best")

        if best:
            print(
                " BEST PROVIDER:",
                best[
                    "provider"
                ]
            )

            print(
                " BEST SCORE:",
                best["score"]
            )

            print(
                " SEMANTIC:",
                best["semantic"]
            )

            print(
                " TITLE:",
                best["title"]
            )

            print(
                " LICENSE:",
                best.get(
                    "license"
                )
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
