#!/usr/bin/env python3

import json
import re
import time
from pathlib import Path

import requests


VERSION = "170.00"

BASE = Path.home() / "ShortAutoPro"

VI150 = (
    BASE / "logs/producao/"
    "vi150_00_query_tournament_latest.json"
)

VI120 = (
    BASE / "logs/producao/"
    "vi120_00_query_intelligence_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi170_00_deep_winner_inspection_latest.json"
)

COMMONS = "https://commons.wikimedia.org/w/api.php"
ARCHIVE_SEARCH = "https://archive.org/advancedsearch.php"
ARCHIVE_META = "https://archive.org/metadata/"

HEADERS = {
    "User-Agent":
        "ShortAutoPro/170.00 "
        "(deep winner verification)"
}

MAX_CANDIDATES = 12

MIN_SCENE_MATCH = 25
MIN_TOPIC_MATCH = 10
MIN_FINAL = 68

VIDEO_EXTENSIONS = {
    ".mp4",
    ".webm",
    ".ogv",
    ".mpeg",
    ".mpg",
    ".mov",
    ".m4v",
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
    "livestream",
    "trailer",
    "teaser",
    "lyrics",
}


GENERIC = {
    "document",
    "file",
    "paper",
    "official",
    "image",
    "photo",
    "archive",
    "historical",
    "video",
    "film",
    "footage",
    "location",
    "hotel",
}


STOP = {
    "the", "and", "for", "with",
    "from", "this", "that",
    "into", "about", "over",
    "under", "onto", "dark",
    "cinematic", "scene",
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
            n = int(item.get("scene"))
        except Exception:
            continue

        out[n] = item

    return out


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


def specific_tokens(text):
    return {
        x
        for x in tokens(text)
        if x not in GENERIC
    }


def similarity(reference, target):
    a = tokens(reference)
    b = tokens(target)

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


def negatives(text):
    low = str(text or "").lower()

    return sorted({
        x
        for x in NEGATIVE
        if x in low
    })


def proper_entities(text):
    values = re.findall(
        r"\b(?:[A-Z][a-zÀ-ÿ]+"
        r"(?:\s+[A-Z][a-zÀ-ÿ]+)+)\b",
        str(text or "")
    )

    seen = set()
    out = []

    for value in values:
        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        out.append(value)

    return out[:12]


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


def scene_text(scene):
    parts = []

    for key in (
        "segment",
        "query",
        "must_have",
        "avoid",
    ):
        value = scene.get(key)

        if isinstance(value, list):
            parts.extend(
                str(x)
                for x in value
            )

        elif value:
            parts.append(str(value))

    return " ".join(parts)


def topic_text(short_id):
    pieces = []

    paths = [
        BASE / "roteiros"
        / f"topic_verified_{short_id}.json",

        BASE / "roteiros"
        / f"narrative_{short_id}.json",

        BASE / "roteiros"
        / f"post_script_truth_{short_id}.json",
    ]

    def walk(value):
        if isinstance(value, str):
            pieces.append(value)

        elif isinstance(value, dict):
            for v in value.values():
                walk(v)

        elif isinstance(value, list):
            for v in value:
                walk(v)

    for path in paths:
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

    return " ".join(pieces)[:20000]


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
                    raise RuntimeError(
                        "HTTP 429"
                    )

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
                        min(retry, 30)
                    )
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


def entity_match(entities, text):
    low = str(text or "").lower()

    matched = [
        entity
        for entity in entities
        if entity.lower() in low
    ]

    return matched


def contextual_scores(
    text,
    scene_context,
    topic,
    entities
):
    scene_score = similarity(
        scene_context,
        text
    )

    topic_score = similarity(
        topic,
        text
    )

    matched_entities = entity_match(
        entities,
        text
    )

    scene_specific = (
        specific_tokens(
            scene_context
        )
        & tokens(text)
    )

    topic_specific = (
        specific_tokens(topic)
        & tokens(text)
    )

    return {
        "scene_match":
            scene_score,

        "topic_match":
            topic_score,

        "matched_entities":
            matched_entities,

        "scene_specific_matches":
            sorted(scene_specific),

        "topic_specific_matches":
            sorted(topic_specific)[:12],
    }


def commons_candidates(
    query,
    scene_context,
    topic,
    entities
):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": MAX_CANDIDATES,
        "prop": "imageinfo",
        "iiprop":
            "url|size|mime|mediatype|extmetadata",
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

        categories = mv(
            "Categories"
        )

        text = (
            title
            + " "
            + description
            + " "
            + categories
        )

        context = contextual_scores(
            text,
            scene_context,
            topic,
            entities
        )

        neg = negatives(text)

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
            technical = 100
        elif pixels >= 2_000_000:
            technical = 90
        elif pixels >= 1_000_000:
            technical = 80
        else:
            technical = 60

        license_text = (
            mv("LicenseShortName")
            + " "
            + mv("UsageTerms")
        ).lower()

        if (
            "public domain" in license_text
            or "cc0" in license_text
        ):
            license_score = 100

        elif "cc by" in license_text:
            license_score = 90

        else:
            license_score = 55

        # Generic-document results must prove
        # connection to the real topic.
        specific_evidence = (
            bool(
                context[
                    "matched_entities"
                ]
            )
            or bool(
                context[
                    "topic_specific_matches"
                ]
            )
        )

        final = (
            context[
                "scene_match"
            ] * .30
            + context[
                "topic_match"
            ] * .30
            + technical * .20
            + license_score * .10
            + (
                10
                if specific_evidence
                else 0
            )
        )

        if neg:
            final -= 40

        gates = {
            "scene_context":
                context[
                    "scene_match"
                ] >= MIN_SCENE_MATCH,

            "topic_context":
                context[
                    "topic_match"
                ] >= MIN_TOPIC_MATCH,

            "specific_evidence":
                specific_evidence,

            "negative_filter":
                not bool(neg),

            "final_score":
                final >= MIN_FINAL,
        }

        decision = (
            "TRUE_IMAGE_CANDIDATE"
            if all(gates.values())
            else "REJECT"
        )

        output.append({
            "provider":
                "COMMONS",

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

            "context":
                context,

            "negative_terms":
                neg,

            "technical":
                technical,

            "license":
                mv("LicenseShortName"),

            "license_score":
                license_score,

            "final_score":
                round(final, 2),

            "gates":
                gates,

            "decision":
                decision,
        })

    return output


def archive_search(query):
    params = {
        "q":
            f'({query}) AND mediatype:movies',

        "fl[]":
            "identifier,title,description,"
            "licenseurl,creator,date",

        "rows":
            MAX_CANDIDATES,

        "page":
            1,

        "output":
            "json",
    }

    data = request_json(
        ARCHIVE_SEARCH,
        params
    )

    return (
        data.get("response", {})
        .get("docs", [])
    )


def usable_video_files(metadata):
    files = []

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

        is_video = (
            ext in VIDEO_EXTENSIONS
            or "mpeg4" in fmt
            or "webm" in fmt
            or "h.264" in fmt
        )

        if not is_video:
            continue

        try:
            size = int(
                float(
                    item.get("size")
                    or 0
                )
            )
        except Exception:
            size = 0

        try:
            width = int(
                float(
                    item.get("width")
                    or 0
                )
            )
        except Exception:
            width = 0

        try:
            height = int(
                float(
                    item.get("height")
                    or 0
                )
            )
        except Exception:
            height = 0

        try:
            length = float(
                item.get("length")
                or 0
            )
        except Exception:
            length = 0

        score = 40

        if size >= 10_000_000:
            score += 15

        if width >= 1280:
            score += 20
        elif width >= 720:
            score += 10

        if height >= 720:
            score += 10

        if length >= 5:
            score += 15

        files.append({
            "name":
                name,

            "size":
                size,

            "width":
                width,

            "height":
                height,

            "length":
                length,

            "format":
                item.get("format"),

            "score":
                min(100, score),
        })

    files.sort(
        key=lambda x:
            x["score"],
        reverse=True
    )

    return files


def archive_candidates(
    query,
    scene_context,
    topic,
    entities
):
    output = []

    for doc in archive_search(query):
        identifier = str(
            doc.get("identifier")
            or ""
        )

        if not identifier:
            continue

        metadata = request_json(
            ARCHIVE_META
            + identifier
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

        context = contextual_scores(
            text,
            scene_context,
            topic,
            entities
        )

        neg = negatives(text)

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

        if (
            "publicdomain" in license_text
            or "zero/1.0" in license_text
        ):
            license_score = 100

        elif (
            "creativecommons"
            in license_text
        ):
            license_score = 88

        else:
            license_score = 45

        specific_evidence = (
            bool(
                context[
                    "matched_entities"
                ]
            )
            or len(
                context[
                    "topic_specific_matches"
                ]
            ) >= 1
        )

        final = (
            context[
                "scene_match"
            ] * .30
            + context[
                "topic_match"
            ] * .25
            + file_score * .20
            + license_score * .10
            + (
                15
                if specific_evidence
                else 0
            )
        )

        if neg:
            final -= 40

        gates = {
            "scene_context":
                context[
                    "scene_match"
                ] >= MIN_SCENE_MATCH,

            "topic_context":
                context[
                    "topic_match"
                ] >= MIN_TOPIC_MATCH,

            "specific_evidence":
                specific_evidence,

            "real_video_file":
                best_file is not None,

            "negative_filter":
                not bool(neg),

            "final_score":
                final >= MIN_FINAL,
        }

        decision = (
            "TRUE_VIDEO_CANDIDATE"
            if all(gates.values())
            else "REJECT"
        )

        output.append({
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

            "video_file_count":
                len(files),

            "license":
                license_text,

            "license_score":
                license_score,

            "final_score":
                round(final, 2),

            "gates":
                gates,

            "decision":
                decision,
        })

        time.sleep(.4)

    return output


def evaluate_scene(
    scene_num,
    winner,
    scene,
    topic,
    global_entities
):
    query = str(
        winner.get("query")
        or ""
    )

    provider = str(
        winner.get("provider")
        or ""
    )

    context = scene_text(
        scene
    )

    local_entities = proper_entities(
        context
    )

    entities = []

    for value in (
        local_entities
        + global_entities
    ):
        if value not in entities:
            entities.append(value)

    entities = entities[:12]

    if provider == "COMMONS":
        candidates = commons_candidates(
            query,
            context,
            topic,
            entities
        )

    elif provider == "ARCHIVE":
        candidates = archive_candidates(
            query,
            context,
            topic,
            entities
        )

    else:
        candidates = []

    candidates.sort(
        key=lambda x:
            x["final_score"],
        reverse=True
    )

    approved = [
        x
        for x in candidates
        if x["decision"]
        in {
            "TRUE_IMAGE_CANDIDATE",
            "TRUE_VIDEO_CANDIDATE",
        }
    ]

    best = (
        approved[0]
        if approved
        else None
    )

    return {
        "scene":
            scene_num,

        "provider":
            provider,

        "query":
            query,

        "entities":
            entities,

        "checked":
            len(candidates),

        "approved":
            len(approved),

        "decision":
            (
                "TRUE_DEEP_CANDIDATE_FOUND"
                if best
                else
                "KEEP_CURRENT"
            ),

        "best":
            best,

        "top_checks":
            candidates[:5],
    }


def evaluate():
    vi150 = load_gate(
        VI150
    )

    vi120 = load_gate(
        VI120
    )

    if not vi150:
        raise RuntimeError(
            "vi150_missing"
        )

    short_id = str(
        vi150.get("short_id")
        or ""
    )

    scenes = scene_map(
        short_id
    )

    topic = topic_text(
        short_id
    )

    global_entities = proper_entities(
        topic
    )

    winners = (
        vi150.get("winners")
        or {}
    )

    results = []

    for key, winner in winners.items():
        scene_num = int(key)

        results.append(
            evaluate_scene(
                scene_num,
                winner,
                scenes.get(
                    scene_num,
                    {}
                ),
                topic,
                global_entities
            )
        )

    approved_scenes = [
        x["scene"]
        for x in results
        if x["decision"]
        == "TRUE_DEEP_CANDIDATE_FOUND"
    ]

    rejected_scenes = [
        x["scene"]
        for x in results
        if x["decision"]
        == "KEEP_CURRENT"
    ]

    blockers = []

    warnings = []

    if rejected_scenes:
        warnings.append(
            "query_winners_rejected_by_deep_truth_gate"
        )

    status = (
        "HOLD"
        if blockers
        else
        "VI170_DEEP_WINNER_INSPECTION_CERTIFIED"
    )

    report = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            short_id,

        "global_entities":
            global_entities,

        "evaluated_scenes":
            [
                x["scene"]
                for x in results
            ],

        "approved_scenes":
            approved_scenes,

        "rejected_scenes":
            rejected_scenes,

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
        " VI170 DEEP WINNER INSPECTION"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "GLOBAL ENTITIES:",
        r["global_entities"]
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
        "REJECTED:",
        r["rejected_scenes"]
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
            " ENTITIES:",
            x["entities"]
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
                best.get(
                    "final_score"
                )
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

        for check in x[
            "top_checks"
        ]:
            print(
                "  -",
                check[
                    "decision"
                ],
                "|",
                check.get("title"),
                "| score=",
                check.get(
                    "final_score"
                ),
                "| scene=",
                (
                    check.get(
                        "context"
                    )
                    or {}
                ).get(
                    "scene_match"
                ),
                "| topic=",
                (
                    check.get(
                        "context"
                    )
                    or {}
                ).get(
                    "topic_match"
                ),
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
