#!/usr/bin/env python3

import json
import re
import time
from pathlib import Path

import requests


VERSION = "200.00"

BASE = Path.home() / "ShortAutoPro"

VI190 = (
    BASE / "logs/producao/"
    "vi190_00_scoped_topic_recheck_latest.json"
)

VI150 = (
    BASE / "logs/producao/"
    "vi150_00_query_tournament_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi200_00_entity_first_search_latest.json"
)

COMMONS = "https://commons.wikimedia.org/w/api.php"
ARCHIVE = "https://archive.org/advancedsearch.php"

HEADERS = {
    "User-Agent":
        "ShortAutoPro/200.00 "
        "(entity-first metadata research)"
}

MAX_RESULTS = 15
MAX_QUERIES = 6

MIN_ENTITY_SCORE = 35
MIN_SCENE_SCORE = 20
MIN_FINAL_SCORE = 58


STOP = {
    "the", "and", "for", "with", "from",
    "this", "that", "into", "about",
    "que", "uma", "um", "de", "da",
    "do", "dos", "das", "para", "como",
    "por", "em", "no", "na",
    "nos", "nas", "parece",
    "vintage", "dark", "cinematic",
    "official", "paper", "document",
    "file", "image", "photo",
    "video", "film", "footage",
}


NEGATIVE = {
    "review",
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
        score *= .65

    return round(
        min(100, score),
        2
    )


def proper_entities(text):
    values = re.findall(
        r"\b(?:[A-Z][A-Za-zÀ-ÿ0-9'-]+"
        r"(?:\s+[A-Z][A-Za-zÀ-ÿ0-9'-]+)+)\b",
        str(text or "")
    )

    out = []
    seen = set()

    for value in values:
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
            parts.extend(
                str(x)
                for x in value
            )

        elif value:
            parts.append(str(value))

    return " ".join(parts)


def load_scenes(short_id):
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


def negative_terms(text):
    low = str(text or "").lower()

    return sorted({
        x
        for x in NEGATIVE
        if x in low
    })


def request_json(
    url,
    params=None
):
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
                        min(
                            retry,
                            30
                        )
                    )
                )

                wait = min(
                    wait * 2,
                    30
                )
                continue

            r.raise_for_status()
            return r.json()

        except Exception:
            if attempt == 3:
                raise

            time.sleep(wait)
            wait = min(
                wait * 2,
                20
            )

    return {}


def build_queries(
    scene_num,
    scene,
    fallback_entities
):
    text = scene_text(scene)

    entities = proper_entities(
        text
    )

    for value in fallback_entities:
        if (
            value.lower()
            in text.lower()
            and value not in entities
        ):
            entities.append(value)

    queries = []

    def add(q):
        q = " ".join(
            str(q).split()
        ).strip()

        if (
            q
            and q.lower()
            not in {
                x.lower()
                for x in queries
            }
        ):
            queries.append(q)

    # Strongest route:
    # named entity before visual adjectives.
    for entity in entities:
        add(entity)

    if scene_num == 2:
        # Explicit aliases known from the
        # current scene context only.
        if (
            "hotel cecil"
            in text.lower()
        ):
            add("Hotel Cecil Los Angeles")
            add("Hotel Cecil exterior")
            add("Cecil Hotel Los Angeles")
            add("Hotel Cecil historical")
            add("Stay on Main Los Angeles")

    # Entity + useful scene nouns.
    scene_tokens = [
        x
        for x in words(text)
        if x.lower() not in STOP
    ]

    useful = []

    for token in scene_tokens:
        low = token.lower()

        if low in {
            "hotel",
            "facade",
            "street",
            "hallway",
            "corridor",
            "elevator",
            "rooftop",
            "water",
            "tank",
            "camera",
            "cctv",
        }:
            if low not in {
                x.lower()
                for x in useful
            }:
                useful.append(token)

    for entity in entities[:2]:
        if useful:
            add(
                entity
                + " "
                + " ".join(
                    useful[:3]
                )
            )

    return {
        "entities":
            entities,

        "queries":
            queries[:MAX_QUERIES],
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

    data = request_json(
        COMMONS,
        params
    )

    return (
        data.get("query", {})
        .get("pages", [])
    )


def archive_search(query):
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
        ARCHIVE,
        params
    )

    return (
        data.get("response", {})
        .get("docs", [])
    )


def entity_score(
    entities,
    text
):
    if not entities:
        return 0.0, []

    low = str(text or "").lower()

    hits = [
        entity
        for entity in entities
        if entity.lower() in low
    ]

    if not hits:
        return 0.0, []

    score = (
        len(hits)
        / len(entities)
        * 100
    )

    return (
        round(
            min(100, score),
            2
        ),
        hits
    )


def evaluate_commons(
    query,
    entities,
    scene_context
):
    results = []

    for page in commons_search(
        query
    ):
        infos = (
            page.get("imageinfo")
            or []
        )

        if not infos:
            continue

        info = infos[0]

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

        es, hits = entity_score(
            entities,
            text
        )

        ss = similarity(
            scene_context,
            text
        )

        qs = similarity(
            query,
            text
        )

        neg = negative_terms(text)

        final = (
            es * .45
            + ss * .25
            + qs * .20
            + 10
        )

        if neg:
            final -= 40

        results.append({
            "provider":
                "COMMONS",

            "query":
                query,

            "title":
                title,

            "url":
                info.get("url"),

            "entity_score":
                es,

            "entity_hits":
                hits,

            "scene_score":
                ss,

            "query_score":
                qs,

            "negative_terms":
                neg,

            "final_score":
                round(
                    max(0, final),
                    2
                ),
        })

    return results


def evaluate_archive(
    query,
    entities,
    scene_context
):
    results = []

    for doc in archive_search(
        query
    ):
        description = (
            doc.get("description")
            or ""
        )

        if isinstance(description, list):
            description = " ".join(
                str(x)
                for x in description
            )

        title = str(
            doc.get("title")
            or ""
        )

        text = (
            title
            + " "
            + str(description)
        )

        es, hits = entity_score(
            entities,
            text
        )

        ss = similarity(
            scene_context,
            text
        )

        qs = similarity(
            query,
            text
        )

        neg = negative_terms(text)

        license_text = str(
            doc.get("licenseurl")
            or ""
        )

        license_bonus = (
            10
            if (
                "creativecommons"
                in license_text.lower()
                or "publicdomain"
                in license_text.lower()
            )
            else 0
        )

        final = (
            es * .45
            + ss * .25
            + qs * .20
            + license_bonus
        )

        if neg:
            final -= 40

        results.append({
            "provider":
                "ARCHIVE",

            "query":
                query,

            "identifier":
                doc.get("identifier"),

            "title":
                title,

            "entity_score":
                es,

            "entity_hits":
                hits,

            "scene_score":
                ss,

            "query_score":
                qs,

            "negative_terms":
                neg,

            "license":
                license_text,

            "final_score":
                round(
                    max(0, final),
                    2
                ),
        })

    return results


def evaluate_scene(
    scene_num,
    scene,
    fallback_entities
):
    context = scene_text(
        scene
    )

    plan = build_queries(
        scene_num,
        scene,
        fallback_entities
    )

    entities = plan[
        "entities"
    ]

    queries = plan[
        "queries"
    ]

    candidates = []

    errors = []

    seen = set()

    for query in queries:
        for provider, func in (
            (
                "COMMONS",
                evaluate_commons
            ),
            (
                "ARCHIVE",
                evaluate_archive
            ),
        ):
            try:
                found = func(
                    query,
                    entities,
                    context
                )

            except Exception as exc:
                errors.append(
                    provider
                    + ":"
                    + type(exc).__name__
                    + ":"
                    + str(exc)[:160]
                )
                continue

            for item in found:
                key = (
                    item.get("url")
                    or item.get(
                        "identifier"
                    )
                    or (
                        item["provider"]
                        + "|"
                        + item["title"]
                    )
                )

                if key in seen:
                    continue

                seen.add(key)
                candidates.append(
                    item
                )

        time.sleep(.6)

    candidates.sort(
        key=lambda x: (
            x["final_score"],
            x["entity_score"],
            x["scene_score"],
        ),
        reverse=True
    )

    qualified = [
        x
        for x in candidates
        if (
            x["entity_score"]
            >= MIN_ENTITY_SCORE
            and x["scene_score"]
            >= MIN_SCENE_SCORE
            and x["final_score"]
            >= MIN_FINAL_SCORE
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

    return {
        "scene":
            scene_num,

        "entities":
            entities,

        "queries":
            queries,

        "candidate_count":
            len(candidates),

        "qualified_count":
            len(qualified),

        "decision":
            (
                "ENTITY_CANDIDATE_FOUND"
                if best
                else "KEEP_CURRENT"
            ),

        "best":
            best,

        "top_candidates":
            candidates[:8],

        "errors":
            errors,
    }


def evaluate():
    vi190 = load_gate(
        VI190
    )

    vi150 = load_gate(
        VI150
    )

    if not vi190:
        raise RuntimeError(
            "vi190_missing"
        )

    short_id = str(
        vi190.get("short_id")
        or ""
    )

    scenes = load_scenes(
        short_id
    )

    # Use only entities already observed
    # in the current short context.
    fallback_entities = []

    for result in (
        vi190.get("results")
        or []
    ):
        for entity in (
            result.get(
                "scene_entities"
            )
            or []
        ):
            if (
                entity
                not in fallback_entities
            ):
                fallback_entities.append(
                    entity
                )

    # Focus first on scenes that had
    # winning queries but failed truth.
    targets = [
        int(x)
        for x in (
            vi150.get(
                "winning_scenes"
            )
            or []
        )
    ]

    results = []

    for scene_num in targets:
        results.append(
            evaluate_scene(
                scene_num,
                scenes.get(
                    scene_num,
                    {}
                ),
                fallback_entities
            )
        )

    winners = [
        x["scene"]
        for x in results
        if x["decision"]
        == "ENTITY_CANDIDATE_FOUND"
    ]

    report = {
        "version":
            VERSION,

        "status":
            "VI200_ENTITY_FIRST_SEARCH_CERTIFIED",

        "short_id":
            short_id,

        "fallback_entities":
            fallback_entities,

        "target_scenes":
            targets,

        "candidate_scenes":
            winners,

        "results":
            results,

        "blockers":
            [],

        "warnings":
            (
                []
                if winners
                else [
                    "no_entity_first_candidate_found"
                ]
            ),

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
        " VI200 ENTITY-FIRST SEARCH"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "FALLBACK ENTITIES:",
        r["fallback_entities"]
    )

    print(
        "TARGET SCENES:",
        r["target_scenes"]
    )

    print(
        "CANDIDATE SCENES:",
        r["candidate_scenes"]
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
            " ENTITIES:",
            x["entities"]
        )

        print(
            " QUERIES:",
            x["queries"]
        )

        print(
            " CANDIDATES:",
            x["candidate_count"]
        )

        print(
            " QUALIFIED:",
            x["qualified_count"]
        )

        print(
            " DECISION:",
            x["decision"]
        )

        best = x.get("best")

        if best:
            print(
                " WINNER:",
                best["title"]
            )

            print(
                " PROVIDER:",
                best["provider"]
            )

            print(
                " ENTITY SCORE:",
                best["entity_score"]
            )

            print(
                " ENTITY HITS:",
                best["entity_hits"]
            )

            print(
                " SCENE SCORE:",
                best["scene_score"]
            )

            print(
                " FINAL SCORE:",
                best["final_score"]
            )

        print()

        for item in x[
            "top_candidates"
        ][:5]:
            print(
                "  -",
                item["provider"],
                "|",
                item["title"],
                "| final=",
                item["final_score"],
                "| entity=",
                item["entity_score"],
                "| scene=",
                item["scene_score"],
                "| hits=",
                item["entity_hits"],
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
