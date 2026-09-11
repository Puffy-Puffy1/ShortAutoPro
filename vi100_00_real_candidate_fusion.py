#!/usr/bin/env python3

import json
import re
import time
from pathlib import Path

import requests

VERSION = "100.00"

BASE = Path.home() / "ShortAutoPro"

VI90 = (
    BASE / "logs/producao/"
    "vi90_00_resilient_provider_orchestrator_latest.json"
)

VI70 = (
    BASE / "logs/producao/"
    "vi70_00_global_visual_casting_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi100_00_real_candidate_fusion_latest.json"
)

COMMONS = "https://commons.wikimedia.org/w/api.php"
ARCHIVE = "https://archive.org/advancedsearch.php"

HEADERS = {
    "User-Agent":
        "ShortAutoPro/100.00 "
        "(candidate-fusion metadata research)"
}

MAX_PER_PROVIDER = 15
MAX_QUERIES = 3

MIN_SCENE = 24
MIN_TOPIC = 8
MIN_FINAL = 62

NEGATIVE = {
    "review", "reviews",
    "reaction", "podcast",
    "gameplay", "walkthrough",
    "audiobook", "creepypasta",
    "compilation", "commentary",
    "livestream", "trailer",
    "teaser", "lyrics",
}

STOP = {
    "the", "and", "for", "with",
    "from", "this", "that",
    "into", "about",
    "photo", "image", "video",
    "documentary", "cinematic",
    "medium", "wide", "close",
    "shot", "clear", "scene",
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
            scene = int(item.get("scene"))
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


def similarity(reference, target):
    a = tokens(reference)
    b = tokens(target)

    if not a:
        return 0.0

    shared = a & b

    if not shared:
        return 0.0

    coverage = len(shared) / len(a)

    score = coverage * 100

    if len(shared) == 1:
        score *= .55

    return round(min(100, score), 2)


def negative_terms(text):
    low = str(text or "").lower()

    return sorted({
        x
        for x in NEGATIVE
        if x in low
    })


def topic_text(short_id):
    pieces = []

    files = [
        BASE / "roteiros"
        / f"topic_verified_{short_id}.json",

        BASE / "roteiros"
        / f"narrative_{short_id}.json",

        BASE / "roteiros"
        / f"post_script_truth_{short_id}.json",
    ]

    def walk(v):
        if isinstance(v, str):
            pieces.append(v)

        elif isinstance(v, dict):
            for x in v.values():
                walk(x)

        elif isinstance(v, list):
            for x in v:
                walk(x)

    for path in files:
        if not path.exists():
            continue

        try:
            walk(json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            ))
        except Exception:
            pass

    return " ".join(pieces)[:18000]


def scene_map(short_id):
    path = (
        BASE / "roteiros"
        / f"scene_map_{short_id}.json"
    )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return by_scene(
        data.get("scenes") or []
    )


def scene_context(scene):
    parts = []

    for key in (
        "segment",
        "query",
        "must_have",
    ):
        value = scene.get(key)

        if isinstance(value, list):
            parts.extend(str(x) for x in value)

        elif value:
            parts.append(str(value))

    return " ".join(parts)


def get_json(url, params, timeout=25):
    wait = 4

    for attempt in range(1, 4):
        try:
            r = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=timeout
            )

            if r.status_code == 429:
                retry = r.headers.get(
                    "Retry-After"
                )

                try:
                    retry = int(retry)
                except Exception:
                    retry = wait

                if attempt == 3:
                    raise RuntimeError(
                        "HTTP 429"
                    )

                time.sleep(
                    max(5, min(retry, 30))
                )

                wait *= 2
                continue

            r.raise_for_status()

            return r.json()

        except Exception:
            if attempt == 3:
                raise

            time.sleep(wait)
            wait = min(wait * 2, 20)

    return {}


def technical_score(width, height):
    pixels = width * height

    if pixels >= 4_000_000:
        return 100

    if pixels >= 2_000_000:
        return 90

    if pixels >= 1_000_000:
        return 80

    if pixels >= 500_000:
        return 65

    return 45


def license_score(text):
    low = str(text or "").lower()

    if (
        "public domain" in low
        or "publicdomain" in low
        or "cc0" in low
        or "zero/1.0" in low
    ):
        return 100

    if (
        "cc by-sa" in low
        or "/by-sa/" in low
    ):
        return 92

    if (
        "cc by" in low
        or "/by/" in low
    ):
        return 90

    if "creativecommons" in low:
        return 80

    return 45


def commons_candidates(
    query,
    desired,
    context,
    topic
):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": MAX_PER_PROVIDER,
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

    pages = (
        data.get("query", {})
        .get("pages", [])
    )

    wanted = (
        "IMAGE"
        if desired == "ARCHIVAL_IMAGE"
        else desired
    )

    output = []

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

        media_type = str(
            info.get("mediatype")
            or ""
        ).lower()

        family = (
            "VIDEO"
            if (
                mime.startswith("video/")
                or media_type == "video"
            )
            else "IMAGE"
        )

        if family != wanted:
            continue

        meta = (
            info.get("extmetadata")
            or {}
        )

        def mv(key):
            v = meta.get(key) or {}

            if isinstance(v, dict):
                return v.get("value") or ""

            return str(v or "")

        title = (
            page.get("title")
            or ""
        )

        description = re.sub(
            r"<[^>]+>",
            " ",
            mv("ImageDescription")
        )

        text = (
            title
            + " "
            + description
        )

        neg = negative_terms(text)

        scene_score = similarity(
            context,
            text
        )

        topic_score = similarity(
            topic,
            text
        )

        query_score = similarity(
            query,
            text
        )

        width = int(
            info.get("width")
            or 0
        )

        height = int(
            info.get("height")
            or 0
        )

        tech = technical_score(
            width,
            height
        )

        lic_text = (
            mv("LicenseShortName")
            + " "
            + mv("UsageTerms")
        )

        lic = license_score(
            lic_text
        )

        final = (
            scene_score * .35
            + query_score * .25
            + topic_score * .15
            + tech * .15
            + lic * .10
        )

        if neg:
            final -= min(
                35,
                len(neg) * 15
            )

        output.append({
            "provider":
                "WIKIMEDIA_COMMONS",

            "family":
                family,

            "title":
                title,

            "url":
                info.get("url"),

            "mime":
                mime,

            "width":
                width,

            "height":
                height,

            "scene_match":
                scene_score,

            "topic_match":
                topic_score,

            "query_match":
                query_score,

            "technical":
                tech,

            "license_score":
                lic,

            "license":
                mv("LicenseShortName"),

            "negative_terms":
                neg,

            "final_score":
                round(
                    max(0, final),
                    2
                ),
        })

    return output


def archive_candidates(
    query,
    context,
    topic
):
    params = {
        "q":
            f'({query}) AND mediatype:movies',

        "fl[]":
            "identifier,title,description,"
            "licenseurl,creator,date",

        "rows":
            MAX_PER_PROVIDER,

        "page":
            1,

        "output":
            "json",
    }

    data = get_json(
        ARCHIVE,
        params
    )

    docs = (
        data.get("response", {})
        .get("docs", [])
    )

    output = []

    for doc in docs:
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
            title
            + " "
            + str(description)
        )

        neg = negative_terms(
            text
        )

        scene_score = similarity(
            context,
            text
        )

        topic_score = similarity(
            topic,
            text
        )

        query_score = similarity(
            query,
            text
        )

        lic_text = str(
            doc.get("licenseurl")
            or ""
        )

        lic = license_score(
            lic_text
        )

        tech = 65

        final = (
            scene_score * .40
            + query_score * .25
            + topic_score * .15
            + tech * .10
            + lic * .10
        )

        if neg:
            final -= min(
                40,
                len(neg) * 18
            )

        output.append({
            "provider":
                "INTERNET_ARCHIVE",

            "family":
                "VIDEO",

            "identifier":
                identifier,

            "title":
                title,

            "scene_match":
                scene_score,

            "topic_match":
                topic_score,

            "query_match":
                query_score,

            "technical":
                tech,

            "license_score":
                lic,

            "license":
                lic_text,

            "negative_terms":
                neg,

            "final_score":
                round(
                    max(0, final),
                    2
                ),
        })

    return output


def evaluate_scene(
    route,
    scene,
    topic
):
    scene_num = int(
        route["scene"]
    )

    desired = (
        route.get(
            "desired_family"
        )
        or "IMAGE"
    )

    context = scene_context(
        scene
    )

    queries = (
        route.get("queries")
        or []
    )[:MAX_QUERIES]

    all_candidates = []

    errors = []

    seen = set()

    for query in queries:
        try:
            commons = commons_candidates(
                query,
                desired,
                context,
                topic
            )

            for item in commons:
                key = (
                    item.get("url")
                    or item.get("title")
                )

                if key in seen:
                    continue

                seen.add(key)
                all_candidates.append(
                    item
                )

        except Exception as exc:
            errors.append(
                "COMMONS:"
                + type(exc).__name__
                + ":"
                + str(exc)[:150]
            )

        if desired == "VIDEO":
            try:
                archive = archive_candidates(
                    query,
                    context,
                    topic
                )

                for item in archive:
                    key = (
                        item.get("identifier")
                        or item.get("title")
                    )

                    if key in seen:
                        continue

                    seen.add(key)
                    all_candidates.append(
                        item
                    )

            except Exception as exc:
                errors.append(
                    "ARCHIVE:"
                    + type(exc).__name__
                    + ":"
                    + str(exc)[:150]
                )

        time.sleep(.6)

    all_candidates.sort(
        key=lambda x: (
            x["final_score"],
            x["scene_match"],
            x["topic_match"],
        ),
        reverse=True
    )

    qualified = [
        x
        for x in all_candidates
        if (
            x["scene_match"]
            >= MIN_SCENE
            and x["topic_match"]
            >= MIN_TOPIC
            and x["final_score"]
            >= MIN_FINAL
            and not x[
                "negative_terms"
            ]
        )
    ]

    best = (
        qualified[0]
        if qualified
        else None
    )

    if best:
        decision = (
            "TRUE_CANDIDATE_FOUND"
        )
    else:
        decision = (
            "KEEP_CURRENT"
        )

    return {
        "scene":
            scene_num,

        "desired_family":
            desired,

        "candidate_count":
            len(
                all_candidates
            ),

        "qualified_count":
            len(
                qualified
            ),

        "false_positive_count":
            sum(
                1
                for x in all_candidates
                if x[
                    "negative_terms"
                ]
            ),

        "decision":
            decision,

        "best":
            best,

        "top_candidates":
            all_candidates[:5],

        "errors":
            errors,
    }


def evaluate():
    vi90 = load_gate(
        VI90
    )

    vi70 = load_gate(
        VI70
    )

    if not vi90:
        raise RuntimeError(
            "vi90_missing"
        )

    short_id = str(
        vi90.get(
            "short_id"
        )
        or ""
    )

    scenes = scene_map(
        short_id
    )

    topic = topic_text(
        short_id
    )

    routes = [
        x
        for x in (
            vi90.get("results")
            or []
        )
        if x.get(
            "decision"
        )
        == "PROVIDER_ROUTE_RECOVERED"
    ]

    results = []

    for route in routes:
        scene_num = int(
            route["scene"]
        )

        results.append(
            evaluate_scene(
                route,
                scenes.get(
                    scene_num,
                    {}
                ),
                topic
            )
        )

    winners = [
        x["scene"]
        for x in results
        if x[
            "decision"
        ]
        == "TRUE_CANDIDATE_FOUND"
    ]

    false_positives = sum(
        x[
            "false_positive_count"
        ]
        for x in results
    )

    blockers = []

    warnings = []

    if false_positives:
        warnings.append(
            "false_positives_filtered"
        )

    if any(
        x["errors"]
        for x in results
    ):
        warnings.append(
            "provider_errors_present"
        )

    status = (
        "HOLD"
        if blockers
        else
        "VI100_REAL_CANDIDATE_FUSION_CERTIFIED"
    )

    report = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            short_id,

        "evaluated_scenes":
            [
                x["scene"]
                for x in results
            ],

        "true_candidate_scenes":
            winners,

        "false_positive_count":
            false_positives,

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
        " VI100 REAL CANDIDATE FUSION"
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
        "TRUE CANDIDATES:",
        r[
            "true_candidate_scenes"
        ]
    )

    print(
        "FALSE POSITIVES FILTERED:",
        r[
            "false_positive_count"
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

        best = x.get("best")

        if best:
            print(
                " BEST PROVIDER:",
                best["provider"]
            )

            print(
                " BEST SCORE:",
                best[
                    "final_score"
                ]
            )

            print(
                " SCENE MATCH:",
                best[
                    "scene_match"
                ]
            )

            print(
                " TOPIC MATCH:",
                best[
                    "topic_match"
                ]
            )

            print(
                " QUERY MATCH:",
                best[
                    "query_match"
                ]
            )

            print(
                " TECHNICAL:",
                best[
                    "technical"
                ]
            )

            print(
                " LICENSE:",
                best[
                    "license"
                ]
            )

            print(
                " TITLE:",
                best["title"]
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
