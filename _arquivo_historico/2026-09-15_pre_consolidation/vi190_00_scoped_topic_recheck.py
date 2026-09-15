#!/usr/bin/env python3

import json
import re
import time
from collections import Counter
from pathlib import Path

import requests


VERSION = "190.00"

BASE = Path.home() / "ShortAutoPro"

VI150 = (
    BASE / "logs/producao/"
    "vi150_00_query_tournament_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi190_00_scoped_topic_recheck_latest.json"
)

COMMONS = "https://commons.wikimedia.org/w/api.php"
ARCHIVE_SEARCH = "https://archive.org/advancedsearch.php"
ARCHIVE_META = "https://archive.org/metadata/"

HEADERS = {
    "User-Agent":
        "ShortAutoPro/190.00 "
        "(scoped-topic deep verification)"
}

MAX_RESULTS = 12

VIDEO_EXT = {
    ".mp4", ".webm", ".ogv",
    ".mpeg", ".mpg", ".mov", ".m4v"
}

STOP = {
    "the", "and", "for", "with", "from",
    "this", "that", "into", "about",
    "scene", "image", "photo", "video",
    "film", "footage", "cinematic",
    "dark", "old", "historic",
    "official", "paper", "document",
    "file", "medium", "wide", "close",
}

NEGATIVE = {
    "review", "reviews", "reaction",
    "podcast", "gameplay", "walkthrough",
    "audiobook", "creepypasta",
    "compilation", "commentary",
    "livestream", "trailer", "teaser",
    "lyrics",
}


def load_gate(path):
    if not path.exists():
        return {}

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    return data.get("gate", data)


def words(text):
    return re.findall(
        r"[A-Za-zÀ-ÿ0-9'-]+",
        str(text or "")
    )


def tokens(text):
    return {
        x.lower()
        for x in words(text)
        if (
            len(x) >= 3
            and x.lower() not in STOP
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

    coverage = len(shared) / len(a)

    score = coverage * 100

    if len(shared) == 1:
        score *= .65

    return round(min(100, score), 2)


def proper_entities(text):
    raw = re.findall(
        r"\b(?:[A-Z][a-zÀ-ÿ]+"
        r"(?:\s+[A-Z][a-zÀ-ÿ]+)+)\b",
        str(text or "")
    )

    out = []
    seen = set()

    for value in raw:
        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        out.append(value)

    return out


def scene_text(scene):
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


def load_scenes(short_id):
    path = (
        BASE / "roteiros"
        / f"scene_map_{short_id}.json"
    )

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    result = {}

    for item in data.get("scenes") or []:
        try:
            number = int(item.get("scene"))
        except Exception:
            continue

        result[number] = item

    return result


def build_scoped_topic(scenes):
    texts = []

    entity_counter = Counter()
    token_counter = Counter()

    for number in sorted(scenes):
        text = scene_text(
            scenes[number]
        )

        texts.append(text)

        for entity in proper_entities(text):
            entity_counter[
                entity
            ] += 1

        for token in tokens(text):
            token_counter[
                token
            ] += 1

    # Entities that occur repeatedly across the
    # current short receive authority.
    dominant_entities = [
        entity
        for entity, count
        in entity_counter.most_common()
        if count >= 2
    ]

    # Also retain strongest recurring topic words.
    dominant_tokens = [
        token
        for token, count
        in token_counter.most_common(30)
        if count >= 2
    ]

    scoped_text = " ".join(
        texts
        + dominant_entities
        + dominant_tokens
    )

    return {
        "text":
            scoped_text,

        "entities":
            dominant_entities[:12],

        "entity_counts":
            dict(
                entity_counter.most_common(20)
            ),

        "dominant_tokens":
            dominant_tokens[:30],
    }


def negative_terms(text):
    low = str(text or "").lower()

    return sorted({
        x for x in NEGATIVE
        if x in low
    })


def request_json(url, params=None):
    wait = 5

    for attempt in range(1, 4):
        try:
            r = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=25
            )

            if r.status_code == 429:
                if attempt == 3:
                    raise RuntimeError("HTTP 429")

                retry = r.headers.get("Retry-After")

                try:
                    retry = int(retry)
                except Exception:
                    retry = wait

                time.sleep(
                    max(5, min(retry, 30))
                )

                wait = min(wait * 2, 30)
                continue

            r.raise_for_status()
            return r.json()

        except Exception:
            if attempt == 3:
                raise

            time.sleep(wait)
            wait = min(wait * 2, 20)

    return {}


def entity_matches(
    scene_entities,
    global_entities,
    text
):
    low = str(text or "").lower()

    scene_hits = [
        x
        for x in scene_entities
        if x.lower() in low
    ]

    global_hits = [
        x
        for x in global_entities
        if x.lower() in low
    ]

    return {
        "scene":
            scene_hits,

        "global":
            global_hits,
    }


def context_scores(
    candidate_text,
    scene_context,
    scoped_topic,
    scene_entities,
    global_entities
):
    scene_match = similarity(
        scene_context,
        candidate_text
    )

    topic_match = similarity(
        scoped_topic,
        candidate_text
    )

    entity = entity_matches(
        scene_entities,
        global_entities,
        candidate_text
    )

    specific_scene = (
        tokens(scene_context)
        & tokens(candidate_text)
    )

    return {
        "scene_match":
            scene_match,

        "topic_match":
            topic_match,

        "entity_matches":
            entity,

        "specific_scene_matches":
            sorted(specific_scene),

        "entity_gate":
            bool(
                entity["scene"]
                or entity["global"]
            ),
    }


def usable_video_files(metadata):
    output = []

    for item in (
        metadata.get("files")
        or []
    ):
        name = str(
            item.get("name")
            or ""
        )

        ext = Path(name).suffix.lower()

        fmt = str(
            item.get("format")
            or ""
        ).lower()

        if not (
            ext in VIDEO_EXT
            or "mpeg4" in fmt
            or "webm" in fmt
            or "h.264" in fmt
        ):
            continue

        def number(key):
            try:
                return float(
                    item.get(key)
                    or 0
                )
            except Exception:
                return 0

        size = int(number("size"))
        width = int(number("width"))
        height = int(number("height"))
        length = number("length")

        score = 35

        if size >= 50_000_000:
            score += 20
        elif size >= 10_000_000:
            score += 15

        if width >= 1280:
            score += 20
        elif width >= 720:
            score += 10

        if height >= 720:
            score += 10

        if length >= 5:
            score += 15

        output.append({
            "name": name,
            "size": size,
            "width": width,
            "height": height,
            "length": length,
            "format":
                item.get("format"),
            "score":
                min(100, score),
        })

    output.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return output


def archive_check(
    query,
    scene_context,
    scoped,
    scene_entities
):
    params = {
        "q":
            f'({query}) AND mediatype:movies',

        "fl[]":
            "identifier,title,description,"
            "licenseurl,creator,date",

        "rows":
            MAX_RESULTS,

        "page":
            1,

        "output":
            "json",
    }

    data = request_json(
        ARCHIVE_SEARCH,
        params
    )

    docs = (
        data.get("response", {})
        .get("docs", [])
    )

    results = []

    for doc in docs:
        identifier = str(
            doc.get("identifier")
            or ""
        )

        if not identifier:
            continue

        metadata = request_json(
            ARCHIVE_META + identifier
        )

        meta = (
            metadata.get("metadata")
            or {}
        )

        title = str(
            meta.get("title")
            or doc.get("title")
            or ""
        )

        description = (
            meta.get("description")
            or doc.get("description")
            or ""
        )

        if isinstance(description, list):
            description = " ".join(
                str(x)
                for x in description
            )

        subject = (
            meta.get("subject")
            or ""
        )

        if isinstance(subject, list):
            subject = " ".join(
                str(x)
                for x in subject
            )

        text = (
            title
            + " "
            + str(description)
            + " "
            + str(subject)
        )

        context = context_scores(
            text,
            scene_context,
            scoped["text"],
            scene_entities,
            scoped["entities"]
        )

        neg = negative_terms(text)

        files = usable_video_files(
            metadata
        )

        best_file = (
            files[0]
            if files
            else None
        )

        file_score = (
            best_file["score"]
            if best_file
            else 0
        )

        license_text = str(
            meta.get("licenseurl")
            or doc.get("licenseurl")
            or ""
        ).lower()

        license_pass = (
            "creativecommons" in license_text
            or "publicdomain" in license_text
        )

        final = (
            context["scene_match"] * .35
            + context["topic_match"] * .20
            + file_score * .20
            + (
                15
                if context["entity_gate"]
                else 0
            )
            + (
                10
                if license_pass
                else 0
            )
        )

        if neg:
            final -= 40

        gates = {
            "scene_match":
                context["scene_match"] >= 30,

            "topic_match":
                context["topic_match"] >= 8,

            "entity_truth":
                context["entity_gate"],

            "real_video":
                best_file is not None,

            "license":
                license_pass,

            "negative_filter":
                not bool(neg),

            "final_score":
                final >= 68,
        }

        decision = (
            "TRUE_VIDEO_CANDIDATE"
            if all(gates.values())
            else "REJECT"
        )

        results.append({
            "provider":
                "INTERNET_ARCHIVE",

            "identifier":
                identifier,

            "title":
                title,

            "context":
                context,

            "negative_terms":
                neg,

            "best_file":
                best_file,

            "license":
                license_text,

            "final_score":
                round(final, 2),

            "gates":
                gates,

            "decision":
                decision,
        })

        time.sleep(.35)

    return results


def commons_check(
    query,
    scene_context,
    scoped,
    scene_entities
):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": MAX_RESULTS,
        "prop": "imageinfo",
        "iiprop":
            "url|size|mime|extmetadata",
        "format": "json",
        "formatversion": 2,
    }

    data = request_json(
        COMMONS,
        params
    )

    pages = (
        data.get("query", {})
        .get("pages", [])
    )

    results = []

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

        if mime.startswith("video/"):
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
                return value.get("value") or ""

            return str(value or "")

        title = str(
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
            + " "
            + mv("Categories")
        )

        context = context_scores(
            text,
            scene_context,
            scoped["text"],
            scene_entities,
            scoped["entities"]
        )

        neg = negative_terms(text)

        width = int(
            info.get("width")
            or 0
        )

        height = int(
            info.get("height")
            or 0
        )

        pixels = width * height

        if pixels >= 4_000_000:
            tech = 100
        elif pixels >= 2_000_000:
            tech = 90
        elif pixels >= 1_000_000:
            tech = 80
        else:
            tech = 60

        license_text = (
            mv("LicenseShortName")
            + " "
            + mv("UsageTerms")
        ).lower()

        license_pass = (
            "public domain" in license_text
            or "cc0" in license_text
            or "cc by" in license_text
        )

        final = (
            context["scene_match"] * .35
            + context["topic_match"] * .25
            + tech * .15
            + (
                15
                if context["entity_gate"]
                else 0
            )
            + (
                10
                if license_pass
                else 0
            )
        )

        if neg:
            final -= 40

        gates = {
            "scene_match":
                context["scene_match"] >= 30,

            "topic_match":
                context["topic_match"] >= 8,

            "entity_truth":
                context["entity_gate"],

            "license":
                license_pass,

            "negative_filter":
                not bool(neg),

            "final_score":
                final >= 68,
        }

        decision = (
            "TRUE_IMAGE_CANDIDATE"
            if all(gates.values())
            else "REJECT"
        )

        results.append({
            "provider":
                "WIKIMEDIA_COMMONS",

            "title":
                title,

            "url":
                info.get("url"),

            "context":
                context,

            "width":
                width,

            "height":
                height,

            "license":
                mv("LicenseShortName"),

            "final_score":
                round(final, 2),

            "gates":
                gates,

            "decision":
                decision,
        })

    return results


def evaluate():
    vi150 = load_gate(VI150)

    if not vi150:
        raise RuntimeError(
            "vi150_missing"
        )

    short_id = str(
        vi150.get("short_id")
        or ""
    )

    scenes = load_scenes(
        short_id
    )

    scoped = build_scoped_topic(
        scenes
    )

    winners = (
        vi150.get("winners")
        or {}
    )

    results = []

    for key, winner in winners.items():
        scene_num = int(key)

        scene = scenes.get(
            scene_num,
            {}
        )

        context = scene_text(scene)

        scene_entities = proper_entities(
            context
        )

        provider = str(
            winner.get("provider")
            or ""
        )

        query = str(
            winner.get("query")
            or ""
        )

        if provider == "ARCHIVE":
            checks = archive_check(
                query,
                context,
                scoped,
                scene_entities
            )

        elif provider == "COMMONS":
            checks = commons_check(
                query,
                context,
                scoped,
                scene_entities
            )

        else:
            checks = []

        checks.sort(
            key=lambda x:
                x["final_score"],
            reverse=True
        )

        approved = [
            x
            for x in checks
            if x["decision"].startswith(
                "TRUE_"
            )
        ]

        best = (
            approved[0]
            if approved
            else None
        )

        results.append({
            "scene":
                scene_num,

            "provider":
                provider,

            "query":
                query,

            "scene_entities":
                scene_entities,

            "checked":
                len(checks),

            "approved":
                len(approved),

            "decision":
                (
                    "TRUE_SCOPED_CANDIDATE_FOUND"
                    if best
                    else "KEEP_CURRENT"
                ),

            "best":
                best,

            "top_checks":
                checks[:5],
        })

    approved_scenes = [
        x["scene"]
        for x in results
        if x["decision"]
        == "TRUE_SCOPED_CANDIDATE_FOUND"
    ]

    result = {
        "version":
            VERSION,

        "status":
            "VI190_SCOPED_TOPIC_RECHECK_CERTIFIED",

        "short_id":
            short_id,

        "scoped_entities":
            scoped["entities"],

        "entity_counts":
            scoped["entity_counts"],

        "dominant_tokens":
            scoped["dominant_tokens"],

        "evaluated_scenes":
            [
                x["scene"]
                for x in results
            ],

        "approved_scenes":
            approved_scenes,

        "results":
            results,

        "blockers":
            [],

        "warnings":
            (
                []
                if approved_scenes
                else [
                    "no_candidate_passed_scoped_truth_gate"
                ]
            ),

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
        " VI190 SCOPED TOPIC + DEEP RECHECK"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "SCOPED ENTITIES:",
        r["scoped_entities"]
    )

    print(
        "DOMINANT TOKENS:",
        r["dominant_tokens"]
    )

    print(
        "EVALUATED:",
        r["evaluated_scenes"]
    )

    print(
        "APPROVED:",
        r["approved_scenes"]
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
            " PROVIDER:",
            x["provider"]
        )

        print(
            " QUERY:",
            x["query"]
        )

        print(
            " SCENE ENTITIES:",
            x["scene_entities"]
        )

        print(
            " CHECKED:",
            x["checked"]
        )

        print(
            " APPROVED:",
            x["approved"]
        )

        print(
            " DECISION:",
            x["decision"]
        )

        best = x.get("best")

        if best:
            print(
                " WINNER:",
                best.get("title")
            )

            print(
                " FINAL SCORE:",
                best.get("final_score")
            )

            print(
                " CONTEXT:",
                best.get("context")
            )

            print(
                " GATES:",
                best.get("gates")
            )

            if best.get("best_file"):
                print(
                    " BEST FILE:",
                    best["best_file"]
                )

        print()

        for check in x["top_checks"]:
            print(
                "  -",
                check["decision"],
                "|",
                check.get("title"),
                "| score=",
                check.get("final_score"),
                "| scene=",
                check["context"][
                    "scene_match"
                ],
                "| topic=",
                check["context"][
                    "topic_match"
                ],
                "| entities=",
                check["context"][
                    "entity_matches"
                ],
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
