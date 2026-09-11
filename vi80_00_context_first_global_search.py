#!/usr/bin/env python3

import json
import re
import time
from pathlib import Path

import requests


VERSION = "80.00"

BASE = Path.home() / "ShortAutoPro"

VI70 = (
    BASE / "logs/producao/"
    "vi70_00_global_visual_casting_latest.json"
)

VI10 = (
    BASE / "logs/producao/"
    "vi10_00_visual_director_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi80_00_context_first_global_search_latest.json"
)

COMMONS = (
    "https://commons.wikimedia.org/w/api.php"
)

ARCHIVE = (
    "https://archive.org/advancedsearch.php"
)

HEADERS = {
    "User-Agent":
        "ShortAutoPro/80.00 "
        "(context-first metadata research)"
}


MAX_SEARCH_SCENES = 6
MAX_QUERY_VARIANTS = 3
MAX_RESULTS = 15

MIN_CONTEXT = 32
MIN_SEMANTIC = 30
MIN_SCORE = 65


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


def similarity(reference, candidate):
    a = tokens(reference)
    b = tokens(candidate)

    if not a:
        return 0.0

    shared = a & b

    if not shared:
        return 0.0

    score = (
        len(shared)
        / len(a)
        * 100
    )

    if len(shared) == 1:
        score *= .55

    return round(
        min(100, score),
        2
    )


def load_scene_map(short_id):
    path = (
        BASE / "roteiros"
        / f"scene_map_{short_id}.json"
    )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def topic_text(short_id):
    files = [
        BASE / "roteiros"
        / f"topic_verified_{short_id}.json",

        BASE / "roteiros"
        / f"narrative_{short_id}.json",

        BASE / "roteiros"
        / f"post_script_truth_{short_id}.json",
    ]

    pieces = []

    def walk(value):
        if isinstance(value, str):
            pieces.append(value)

        elif isinstance(value, dict):
            for v in value.values():
                walk(v)

        elif isinstance(value, list):
            for v in value:
                walk(v)

    for path in files:
        if not path.exists():
            continue

        try:
            walk(
                json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )
            )
        except Exception:
            pass

    return " ".join(
        pieces
    )[:16000]


def scene_text(scene):
    parts = []

    for key in (
        "segment",
        "query",
        "must_have",
    ):
        value = scene.get(key)

        if isinstance(value, list):
            parts.extend(
                str(x)
                for x in value
            )

        elif value:
            parts.append(
                str(value)
            )

    return " ".join(parts)


def clean_query(text):
    seen = set()
    output = []

    for word in words(text):
        low = word.lower()

        if low in STOP:
            continue

        if low in seen:
            continue

        seen.add(low)
        output.append(word)

    return " ".join(output)


def query_variants(scene):
    raw = clean_query(
        scene.get("query")
        or scene.get("segment")
        or ""
    )

    parts = raw.split()

    variants = [
        raw,
        " ".join(parts[:6]),
        " ".join(parts[:4]),
    ]

    result = []
    seen = set()

    for q in variants:
        q = q.strip()

        if not q:
            continue

        if q.lower() in seen:
            continue

        seen.add(
            q.lower()
        )

        result.append(q)

    return result[
        :MAX_QUERY_VARIANTS
    ]


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
        COMMONS,
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
        ],

        "rows":
            MAX_RESULTS,

        "page":
            1,

        "output":
            "json",
    }

    r = requests.get(
        ARCHIVE,
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


def commons_candidates(
    query,
    scene_context,
    topic,
    desired_family
):
    output = []

    for page in commons_search(
        query
    ):
        infos = (
            page.get(
                "imageinfo"
            )
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
                mime.startswith(
                    "video/"
                )
                or media_type
                == "video"
            )
            else "IMAGE"
        )

        wanted = (
            "IMAGE"
            if desired_family
            == "ARCHIVAL_IMAGE"
            else desired_family
        )

        if family != wanted:
            continue

        meta = (
            info.get(
                "extmetadata"
            )
            or {}
        )

        def mv(key):
            value = (
                meta.get(key)
                or {}
            )

            if isinstance(
                value,
                dict
            ):
                return (
                    value.get(
                        "value"
                    )
                    or ""
                )

            return str(
                value or ""
            )

        title = (
            page.get("title")
            or ""
        )

        description = re.sub(
            r"<[^>]+>",
            " ",
            mv(
                "ImageDescription"
            )
        )

        candidate_text = (
            title
            + " "
            + description
        )

        semantic = similarity(
            query,
            candidate_text
        )

        context = similarity(
            scene_context,
            candidate_text
        )

        topic_match = similarity(
            topic,
            candidate_text
        )

        width = int(
            info.get("width")
            or 0
        )

        height = int(
            info.get("height")
            or 0
        )

        pixels = (
            width * height
        )

        if pixels >= 4_000_000:
            technical = 95
        elif pixels >= 2_000_000:
            technical = 86
        elif pixels >= 1_000_000:
            technical = 75
        else:
            technical = 55

        license_text = (
            mv("LicenseShortName")
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
            license_score = 55

        score = (
            semantic * .25
            + context * .30
            + topic_match * .20
            + technical * .15
            + license_score * .10
        )

        if (
            context < MIN_CONTEXT
            or semantic < MIN_SEMANTIC
        ):
            continue

        if score < MIN_SCORE:
            continue

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

            "license":
                mv(
                    "LicenseShortName"
                ),

            "semantic":
                semantic,

            "context":
                context,

            "topic_match":
                topic_match,

            "technical":
                technical,

            "score":
                round(
                    score,
                    2
                ),
        })

    return output


def archive_candidates(
    query,
    scene_context,
    topic
):
    output = []

    for doc in archive_search(
        query
    ):
        identifier = str(
            doc.get(
                "identifier"
            )
            or ""
        )

        if not identifier:
            continue

        title = str(
            doc.get("title")
            or ""
        )

        description = (
            doc.get(
                "description"
            )
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

        semantic = similarity(
            query,
            text
        )

        context = similarity(
            scene_context,
            text
        )

        topic_match = similarity(
            topic,
            text
        )

        if (
            semantic < MIN_SEMANTIC
            or context < MIN_CONTEXT
        ):
            continue

        license_url = str(
            doc.get(
                "licenseurl"
            )
            or ""
        )

        license_score = (
            90
            if "creativecommons"
            in license_url.lower()
            else 50
        )

        technical = 65

        score = (
            semantic * .25
            + context * .35
            + topic_match * .20
            + technical * .10
            + license_score * .10
        )

        if score < MIN_SCORE:
            continue

        output.append({
            "provider":
                "INTERNET_ARCHIVE",

            "family":
                "VIDEO",

            "identifier":
                identifier,

            "title":
                title,

            "license":
                license_url,

            "semantic":
                semantic,

            "context":
                context,

            "topic_match":
                topic_match,

            "technical":
                technical,

            "score":
                round(
                    score,
                    2
                ),
        })

    return output


def search_scene(
    scene_num,
    scene,
    plan,
    topic
):
    desired = (
        plan.get(
            "desired_family"
        )
        or plan.get(
            "current_family"
        )
        or "IMAGE"
    )

    context = scene_text(
        scene
    )

    candidates = []

    errors = []

    seen = set()

    queries = query_variants(
        scene
    )

    for query in queries:
        try:
            found = commons_candidates(
                query,
                context,
                topic,
                desired
            )

            for item in found:
                key = (
                    item.get("url")
                    or item.get(
                        "identifier"
                    )
                    or item.get(
                        "title"
                    )
                )

                if key in seen:
                    continue

                seen.add(key)
                candidates.append(
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
                found = archive_candidates(
                    query,
                    context,
                    topic
                )

                for item in found:
                    key = (
                        item.get(
                            "identifier"
                        )
                        or item.get(
                            "title"
                        )
                    )

                    if key in seen:
                        continue

                    seen.add(key)
                    candidates.append(
                        item
                    )

            except Exception as exc:
                errors.append(
                    "ARCHIVE:"
                    + type(exc).__name__
                    + ":"
                    + str(exc)[:150]
                )

        time.sleep(.5)

    candidates.sort(
        key=lambda x: (
            x["score"],
            x["context"],
            x["topic_match"],
        ),
        reverse=True
    )

    best = (
        candidates[0]
        if candidates
        else None
    )

    return {
        "scene":
            scene_num,

        "current_family":
            plan.get(
                "current_family"
            ),

        "desired_family":
            desired,

        "queries":
            queries,

        "candidate_count":
            len(candidates),

        "best":
            best,

        "top":
            candidates[:5],

        "decision":
            (
                "CONTEXT_CANDIDATE_FOUND"
                if best
                else "KEEP_CURRENT"
            ),

        "errors":
            errors,
    }


def evaluate():
    vi70 = load_gate(
        VI70
    )

    vi10 = load_gate(
        VI10
    )

    if not vi70:
        raise RuntimeError(
            "vi70_missing"
        )

    short_id = str(
        vi70.get(
            "short_id"
        )
        or ""
    )

    scene_map = load_scene_map(
        short_id
    )

    scenes = by_scene(
        scene_map.get(
            "scenes"
        )
        or []
    )

    plans70 = by_scene(
        vi70.get(
            "decisions"
        )
        or []
    )

    plans10 = by_scene(
        vi10.get(
            "plans"
        )
        or []
    )

    topic = topic_text(
        short_id
    )

    priorities = []

    for scene in range(
        1,
        13
    ):
        p70 = plans70.get(
            scene,
            {}
        )

        p10 = plans10.get(
            scene,
            {}
        )

        current = (
            p70.get(
                "current_family"
            )
        )

        desired = (
            p70.get(
                "desired_family"
            )
        )

        score = 0

        if (
            current
            != desired
        ):
            score += 30

        if not p10.get(
            "shot_match",
            True
        ):
            score += 25

        score += max(
            0,
            float(
                p10.get(
                    "ideal_score"
                )
                or 0
            )
            -
            float(
                p10.get(
                    "current_score"
                )
                or 0
            )
        )

        if p10.get(
            "identity"
        ) == "CAUTION":
            score -= 25

        # Scene 7 already passed through
        # deep verification and context rejection.
        if scene == 7:
            score -= 100

        priorities.append(
            (
                score,
                scene
            )
        )

    priorities.sort(
        reverse=True
    )

    target_scenes = [
        scene
        for score, scene
        in priorities
        if score > 0
    ][
        :MAX_SEARCH_SCENES
    ]

    results = []

    for scene in target_scenes:
        results.append(
            search_scene(
                scene,
                scenes.get(
                    scene,
                    {}
                ),
                plans70.get(
                    scene,
                    {}
                ),
                topic
            )
        )

    found = [
        x["scene"]
        for x in results
        if x["decision"]
        == "CONTEXT_CANDIDATE_FOUND"
    ]

    blockers = []

    warnings = []

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
        "VI80_CONTEXT_FIRST_GLOBAL_SEARCH_CERTIFIED"
    )

    report = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            short_id,

        "target_scenes":
            target_scenes,

        "candidate_found_scenes":
            found,

        "results":
            results,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "network_executed":
            bool(target_scenes),

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
        " VI80 CONTEXT-FIRST GLOBAL SEARCH"
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

    for x in r["results"]:
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
            " DECISION:",
            x["decision"]
        )

        print(
            " CANDIDATES:",
            x["candidate_count"]
        )

        best = x.get(
            "best"
        )

        if best:
            print(
                " BEST PROVIDER:",
                best["provider"]
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
                " CONTEXT:",
                best["context"]
            )

            print(
                " TOPIC:",
                best["topic_match"]
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
        r["ffmpeg_executed"]
    )

    print(
        "VIDEO GENERATED:",
        r["video_generated"]
    )
