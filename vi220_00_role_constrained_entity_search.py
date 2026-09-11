#!/usr/bin/env python3

import json
import re
import time
from pathlib import Path

import requests


VERSION = "220.00"

BASE = Path.home() / "ShortAutoPro"

VI210 = (
    BASE / "logs/producao/"
    "vi210_00_scene_role_family_gate_latest.json"
)

VI200 = (
    BASE / "logs/producao/"
    "vi200_00_entity_first_search_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi220_00_role_constrained_entity_search_latest.json"
)

COMMONS = "https://commons.wikimedia.org/w/api.php"

ARCHIVE = (
    "https://archive.org/advancedsearch.php"
)

HEADERS = {
    "User-Agent":
        "ShortAutoPro/220.00 "
        "(role-constrained entity metadata search)"
}

MAX_RESULTS = 20

MIN_PRIMARY_ENTITY = 100
MIN_ROLE = 70
MIN_FINAL = 68


NEGATIVE = {
    "live stream",
    "livestream",
    "stream",
    "podcast",
    "review",
    "reaction",
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


ROLE_TERMS = {
    "FACADE": {
        "facade",
        "façade",
        "exterior",
        "street",
        "street scene",
        "building exterior",
        "hotel exterior",
        "front entrance",
        "front of",
    },

    "ELEVATOR": {
        "elevator",
        "lift",
        "elevador",
    },

    "HALLWAY": {
        "hallway",
        "corridor",
    },

    "ROOFTOP": {
        "rooftop",
        "roof",
        "water tank",
    },

    "SIGN": {
        "room rate",
        "rate sign",
        "sign",
        "plaque",
    },
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


def normalize(text):
    text = str(text or "")

    # Commons namespace markers are metadata,
    # not visual meaning.
    text = re.sub(
        r"^\s*File\s*:\s*",
        "",
        text,
        flags=re.I
    )

    text = re.sub(
        r"^\s*Category\s*:\s*",
        "",
        text,
        flags=re.I
    )

    text = text.lower()

    text = text.replace(
        "_",
        " "
    )

    text = text.replace(
        "-",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def negative_terms(text):
    low = normalize(text)

    found = []

    for term in NEGATIVE:
        if re.search(
            r"\b"
            + re.escape(term)
            + r"\b",
            low
        ):
            found.append(term)

    return sorted(
        set(found)
    )


def role_hits(text):
    low = normalize(text)

    result = {}

    for role, terms in ROLE_TERMS.items():
        found = []

        for term in terms:
            if term in low:
                found.append(term)

        if found:
            result[role] = sorted(
                set(found)
            )

    return result


def role_score(required, text):
    hits = role_hits(text)

    if required in hits:
        score = 100

    elif required == "FACADE":
        # A named building combined with
        # street/exterior language is useful.
        low = normalize(text)

        if (
            "street" in low
            or "exterior" in low
            or "building" in low
        ):
            score = 75
        else:
            score = 0

    else:
        score = 0

    # Explicit conflicting role.
    if (
        required == "FACADE"
        and (
            "ELEVATOR" in hits
            or "SIGN" in hits
        )
    ):
        score = 0

    return score, hits


def primary_entity_score(
    entity,
    text
):
    if not entity:
        return 0

    low = normalize(text)
    wanted = normalize(entity)

    if wanted in low:
        return 100

    # Hotel Cecil alias order.
    if wanted == "hotel cecil":
        if "cecil hotel" in low:
            return 100

    return 0


def secondary_entity_score(
    entities,
    text
):
    if not entities:
        return 0

    low = normalize(text)

    hits = [
        x
        for x in entities
        if normalize(x) in low
    ]

    return round(
        len(hits)
        / len(entities)
        * 100,
        2
    )


def request_json(
    url,
    params
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
                        min(retry, 30)
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


def commons_video_search(query):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": MAX_RESULTS,
        "prop": "imageinfo",
        "iiprop":
            "url|mime|mediatype|extmetadata",
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


def archive_candidates(
    query,
    primary,
    secondary,
    required_role
):
    result = []

    for doc in archive_search(query):
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

        primary_score = (
            primary_entity_score(
                primary,
                text
            )
        )

        secondary_score = (
            secondary_entity_score(
                secondary,
                text
            )
        )

        rscore, rhits = role_score(
            required_role,
            text
        )

        neg = negative_terms(
            text
        )

        license_text = str(
            doc.get("licenseurl")
            or ""
        ).lower()

        license_score = (
            100
            if (
                "publicdomain"
                in license_text
                or "zero/1.0"
                in license_text
            )
            else (
                90
                if "creativecommons"
                in license_text
                else 45
            )
        )

        final = (
            primary_score * .45
            + rscore * .30
            + secondary_score * .10
            + license_score * .15
        )

        if neg:
            final -= 50

        gates = {
            "family_video":
                True,

            "primary_entity":
                primary_score
                >= MIN_PRIMARY_ENTITY,

            "role":
                rscore >= MIN_ROLE,

            "negative_filter":
                not bool(neg),

            "final_score":
                final >= MIN_FINAL,
        }

        result.append({
            "provider":
                "INTERNET_ARCHIVE",

            "identifier":
                doc.get("identifier"),

            "title":
                title,

            "query":
                query,

            "family":
                "VIDEO",

            "primary_entity":
                primary,

            "primary_score":
                primary_score,

            "secondary_score":
                secondary_score,

            "role_score":
                rscore,

            "role_hits":
                rhits,

            "negative_terms":
                neg,

            "license":
                license_text,

            "final_score":
                round(
                    max(0, final),
                    2
                ),

            "gates":
                gates,

            "decision":
                (
                    "TRUE_ROLE_CONSTRAINED_VIDEO"
                    if all(
                        gates.values()
                    )
                    else "REJECT"
                ),
        })

    return result


def commons_candidates(
    query,
    primary,
    secondary,
    required_role
):
    result = []

    for page in commons_video_search(
        query
    ):
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

        # Family is enforced at retrieval.
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
                return value.get(
                    "value"
                ) or ""

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
            normalize(title)
            + " "
            + description
            + " "
            + mv("Categories")
        )

        primary_score = (
            primary_entity_score(
                primary,
                text
            )
        )

        secondary_score = (
            secondary_entity_score(
                secondary,
                text
            )
        )

        rscore, rhits = role_score(
            required_role,
            text
        )

        neg = negative_terms(
            text
        )

        license_text = (
            mv("LicenseShortName")
            + " "
            + mv("UsageTerms")
        ).lower()

        license_score = (
            100
            if (
                "public domain"
                in license_text
                or "cc0"
                in license_text
            )
            else (
                90
                if "cc by"
                in license_text
                else 55
            )
        )

        final = (
            primary_score * .45
            + rscore * .30
            + secondary_score * .10
            + license_score * .15
        )

        if neg:
            final -= 50

        gates = {
            "family_video":
                True,

            "primary_entity":
                primary_score
                >= MIN_PRIMARY_ENTITY,

            "role":
                rscore >= MIN_ROLE,

            "negative_filter":
                not bool(neg),

            "final_score":
                final >= MIN_FINAL,
        }

        result.append({
            "provider":
                "WIKIMEDIA_COMMONS",

            "title":
                title,

            "url":
                info.get("url"),

            "mime":
                mime,

            "query":
                query,

            "family":
                "VIDEO",

            "primary_entity":
                primary,

            "primary_score":
                primary_score,

            "secondary_score":
                secondary_score,

            "role_score":
                rscore,

            "role_hits":
                rhits,

            "negative_terms":
                neg,

            "license":
                mv("LicenseShortName"),

            "final_score":
                round(
                    max(0, final),
                    2
                ),

            "gates":
                gates,

            "decision":
                (
                    "TRUE_ROLE_CONSTRAINED_VIDEO"
                    if all(
                        gates.values()
                    )
                    else "REJECT"
                ),
        })

    return result


def evaluate():
    vi210 = load_gate(
        VI210
    )

    vi200 = load_gate(
        VI200
    )

    if not vi210:
        raise RuntimeError(
            "vi210_missing"
        )

    # Scene 2 is the first validated target:
    # entity known, desired family VIDEO,
    # required visual role FACADE.
    target_scene = 2

    primary = "Hotel Cecil"

    secondary = [
        "Los Angeles"
    ]

    required_role = "FACADE"

    queries = [
        "Hotel Cecil exterior Los Angeles",
        "Hotel Cecil facade Los Angeles",
        "Cecil Hotel exterior Los Angeles",
        "Hotel Cecil street Los Angeles",
        "Hotel Cecil building Los Angeles",
        "Stay on Main exterior Los Angeles",
    ]

    candidates = []

    errors = []

    seen = set()

    for query in queries:
        for provider, func in (
            (
                "ARCHIVE",
                archive_candidates
            ),
            (
                "COMMONS",
                commons_candidates
            ),
        ):
            try:
                found = func(
                    query,
                    primary,
                    secondary,
                    required_role
                )

            except Exception as exc:
                errors.append(
                    provider
                    + ":"
                    + type(exc).__name__
                    + ":"
                    + str(exc)[:180]
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

        time.sleep(.7)

    candidates.sort(
        key=lambda x: (
            x["final_score"],
            x["primary_score"],
            x["role_score"],
        ),
        reverse=True
    )

    approved = [
        x
        for x in candidates
        if x["decision"]
        == "TRUE_ROLE_CONSTRAINED_VIDEO"
    ]

    best = (
        approved[0]
        if approved
        else None
    )

    report = {
        "version":
            VERSION,

        "status":
            "VI220_ROLE_CONSTRAINED_ENTITY_SEARCH_CERTIFIED",

        "short_id":
            vi200.get(
                "short_id"
            ),

        "scene":
            target_scene,

        "primary_entity":
            primary,

        "secondary_entities":
            secondary,

        "required_family":
            "VIDEO",

        "required_role":
            required_role,

        "queries":
            queries,

        "candidate_count":
            len(candidates),

        "approved_count":
            len(approved),

        "decision":
            (
                "TRUE_VIDEO_CANDIDATE_FOUND"
                if best
                else "KEEP_CURRENT"
            ),

        "best":
            best,

        "top_candidates":
            candidates[:10],

        "errors":
            errors,

        "blockers":
            [],

        "warnings":
            (
                ["provider_errors_present"]
                if errors
                else []
            ),

        "network_executed":
            True,

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
        " VI220 ROLE-CONSTRAINED ENTITY SEARCH"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "SCENE:",
        r["scene"]
    )

    print(
        "PRIMARY ENTITY:",
        r["primary_entity"]
    )

    print(
        "REQUIRED FAMILY:",
        r["required_family"]
    )

    print(
        "REQUIRED ROLE:",
        r["required_role"]
    )

    print(
        "CANDIDATES:",
        r["candidate_count"]
    )

    print(
        "APPROVED:",
        r["approved_count"]
    )

    print(
        "DECISION:",
        r["decision"]
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

    best = r.get("best")

    if best:
        print(
            "WINNER:",
            best["title"]
        )

        print(
            "PROVIDER:",
            best["provider"]
        )

        print(
            "PRIMARY:",
            best["primary_score"]
        )

        print(
            "ROLE:",
            best["role_score"]
        )

        print(
            "SECONDARY:",
            best["secondary_score"]
        )

        print(
            "FINAL:",
            best["final_score"]
        )

        print(
            "GATES:",
            best["gates"]
        )

        print()

    print(
        "===== TOP CANDIDATES ====="
    )

    for item in r[
        "top_candidates"
    ]:
        print(
            "-",
            item["decision"],
            "|",
            item["provider"],
            "|",
            item["title"],
            "| primary=",
            item["primary_score"],
            "| role=",
            item["role_score"],
            "| secondary=",
            item["secondary_score"],
            "| final=",
            item["final_score"],
            "| negatives=",
            item["negative_terms"],
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
