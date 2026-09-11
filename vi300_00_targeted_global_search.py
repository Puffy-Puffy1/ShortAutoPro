#!/usr/bin/env python3

import json
import re
import time
import hashlib
from pathlib import Path

import requests


VERSION = "300.00"

BASE = Path.home() / "ShortAutoPro"
LOG = BASE / "logs/producao"

VI260 = (
    LOG /
    "vi260_00_global_provenance_director_latest.json"
)

VI200 = (
    LOG /
    "vi200_00_entity_first_search_latest.json"
)

VI235 = (
    LOG /
    "vi235_00_media_provenance_check_latest.json"
)

OUT = (
    LOG /
    "vi300_00_targeted_global_search_latest.json"
)

COMMONS = "https://commons.wikimedia.org/w/api.php"

ARCHIVE_SEARCH = (
    "https://archive.org/advancedsearch.php"
)

ARCHIVE_META = (
    "https://archive.org/metadata/"
)

HEADERS = {
    "User-Agent":
        "ShortAutoPro/300.00 "
        "(targeted metadata-only visual research)"
}

MAX_NETWORK_SCENES = 6
MAX_RESULTS = 15
MAX_QUERIES = 2

VIDEO_EXT = {
    ".mp4", ".webm", ".ogv",
    ".mpeg", ".mpg", ".mov", ".m4v"
}

NEGATIVE = {
    "live stream",
    "livestream",
    "stream",
    "podcast",
    "review",
    "reviews",
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
    "ELEVATOR": {
        "elevator",
        "lift",
        "elevador",
        "elevator doors",
    },

    "HALLWAY": {
        "hallway",
        "corridor",
        "hotel hallway",
        "hotel corridor",
    },

    "ROOFTOP": {
        "rooftop",
        "roof",
        "water tank",
        "water tower",
        "tank",
    },

    "FACADE": {
        "facade",
        "façade",
        "exterior",
        "street",
        "building exterior",
    },

    "SURVEILLANCE": {
        "cctv",
        "security camera",
        "surveillance",
        "camera",
    },

    "DOCUMENT": {
        "document",
        "report",
        "record",
        "paper",
        "file",
    },

    "MEDICINE": {
        "medicine",
        "medication",
        "prescription",
        "bottle",
        "pill",
    },

    "FACE": {
        "portrait",
        "face",
        "woman",
        "man",
        "person",
    },
}


ROLE_QUERY_CORE = {
    "ELEVATOR":
        "elevator interior doors",

    "HALLWAY":
        "hotel hallway corridor",

    "ROOFTOP":
        "rooftop water tank",

    "FACADE":
        "hotel exterior facade",

    "SURVEILLANCE":
        "CCTV security camera",

    "DOCUMENT":
        "official document record",

    "MEDICINE":
        "prescription medicine bottles",

    "FACE":
        "portrait",
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


def normalize(text):
    text = str(text or "")

    text = re.sub(
        r"^\s*File\s*:\s*",
        "",
        text,
        flags=re.I
    )

    text = text.replace(
        "_",
        " "
    )

    text = text.replace(
        "-",
        " "
    )

    text = text.lower()

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


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


def negative_terms(text):
    low = normalize(text)

    found = []

    for term in NEGATIVE:
        if term in low:
            found.append(term)

    return sorted(
        set(found)
    )


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def load_scene_map(short_id):
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
        data.get("scenes")
        or []
    )


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


def detect_role(
    category,
    text
):
    low = normalize(text)

    category = str(
        category or ""
    ).upper()

    if category == "FACE":
        return "FACE"

    if category == "DOCUMENT":
        return "DOCUMENT"

    if category == "EVIDENCE":
        return "SURVEILLANCE"

    if category == "OBJECT":
        if any(
            x in low
            for x in (
                "medicine",
                "prescription",
                "pill",
                "bottle",
            )
        ):
            return "MEDICINE"

    if any(
        x in low
        for x in (
            "elevator",
            "elevador",
            "lift",
        )
    ):
        return "ELEVATOR"

    if any(
        x in low
        for x in (
            "hallway",
            "corridor",
        )
    ):
        return "HALLWAY"

    if any(
        x in low
        for x in (
            "rooftop",
            "water tank",
            "water tower",
            "roof",
        )
    ):
        return "ROOFTOP"

    if any(
        x in low
        for x in (
            "facade",
            "façade",
            "street",
            "exterior",
        )
    ):
        return "FACADE"

    if category == "LOCATION":
        return "LOCATION"

    return category or "GENERAL"


def role_score(
    required,
    text
):
    low = normalize(text)

    if required == "LOCATION":
        return 70.0, []

    terms = (
        ROLE_TERMS.get(
            required
        )
        or set()
    )

    hits = [
        term
        for term in terms
        if term in low
    ]

    if hits:
        return 100.0, hits

    return 0.0, []


def entity_score(
    entity,
    text
):
    if not entity:
        return 0.0

    low = normalize(text)
    wanted = normalize(entity)

    if wanted in low:
        return 100.0

    if (
        wanted == "hotel cecil"
        and "cecil hotel"
        in low
    ):
        return 100.0

    return 0.0


def request_json(
    url,
    params=None,
    timeout=25
):
    wait = 5

    for attempt in range(1, 4):
        try:
            r = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=timeout
            )

            if r.status_code == 429:
                if attempt == 3:
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

                wait = min(
                    wait * 2,
                    30
                )

                continue

            r.raise_for_status()

            data = r.json()
            data["_status"] = "OK"

            return data

        except Exception as exc:
            if attempt == 3:
                return {
                    "_status":
                        "ERROR",

                    "_error":
                        type(exc).__name__
                        + ":"
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

    if data.get(
        "_status"
    ) != "OK":
        return (
            [],
            data.get(
                "_status"
            ),
            data.get(
                "_error"
            ),
        )

    return (
        data.get(
            "query",
            {}
        ).get(
            "pages",
            []
        ),
        "OK",
        None,
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
        ARCHIVE_SEARCH,
        params
    )

    if data.get(
        "_status"
    ) != "OK":
        return (
            [],
            data.get(
                "_status"
            ),
            data.get(
                "_error"
            ),
        )

    docs = (
        data.get(
            "response",
            {}
        ).get(
            "docs",
            []
        )
    )

    return docs, "OK", None


def license_score(text):
    low = normalize(text)

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
        return 82

    return 45


def technical_score(
    width,
    height
):
    pixels = (
        int(width or 0)
        * int(height or 0)
    )

    if pixels >= 4_000_000:
        return 100

    if pixels >= 2_000_000:
        return 90

    if pixels >= 1_000_000:
        return 80

    if pixels >= 500_000:
        return 65

    return 45


def video_files(metadata):
    result = []

    for item in (
        metadata.get("files")
        or []
    ):
        name = str(
            item.get("name")
            or ""
        )

        ext = (
            Path(name)
            .suffix.lower()
        )

        fmt = normalize(
            item.get("format")
        )

        if not (
            ext in VIDEO_EXT
            or "mpeg4" in fmt
            or "h.264" in fmt
            or "webm" in fmt
        ):
            continue

        def num(key):
            try:
                return float(
                    item.get(key)
                    or 0
                )
            except Exception:
                return 0

        size = int(
            num("size")
        )

        width = int(
            num("width")
        )

        height = int(
            num("height")
        )

        length = num(
            "length"
        )

        score = 40

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
            score += 10

        result.append({
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
                item.get(
                    "format"
                ),

            "score":
                min(
                    100,
                    score
                ),
        })

    result.sort(
        key=lambda x:
            x["score"],
        reverse=True
    )

    return result


def local_provenance_audit(
    media_path
):
    if not media_path:
        return {
            "hash_hits": [],
            "name_hits": [],
        }

    path = Path(
        media_path
    )

    if not path.exists():
        return {
            "hash_hits": [],
            "name_hits": [],
        }

    digest = sha256(path)
    basename = path.name

    hash_hits = []
    name_hits = []

    roots = [
        BASE / "manifests",
        BASE / "credits",
    ]

    for root in roots:
        if not root.exists():
            continue

        for source in root.rglob("*"):
            if (
                not source.is_file()
                or source.stat().st_size
                > 2_000_000
            ):
                continue

            if source.suffix.lower() not in {
                ".json",
                ".txt",
                ".log",
                ".csv",
            }:
                continue

            try:
                text = source.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )
            except Exception:
                continue

            if digest in text:
                hash_hits.append(
                    str(source)
                )

            elif basename in text:
                name_hits.append(
                    str(source)
                )

    return {
        "hash_hits":
            hash_hits[:10],

        "name_hits":
            name_hits[:10],
    }


def build_anchors(
    vi200,
    scenes
):
    known = []

    for entity in (
        vi200.get(
            "fallback_entities"
        )
        or []
    ):
        if entity not in known:
            known.append(entity)

    for scene in scenes.values():
        for entity in proper_entities(
            scene_text(scene)
        ):
            if entity not in known:
                known.append(entity)

    primary = None

    for entity in known:
        if normalize(
            entity
        ) in {
            "hotel cecil",
            "cecil hotel",
        }:
            primary = "Hotel Cecil"
            break

    if not primary:
        for entity in known:
            if normalize(
                entity
            ).startswith(
                "hotel "
            ):
                primary = entity
                break

    persons = [
        x
        for x in known
        if (
            normalize(x)
            not in {
                "hotel cecil",
                "los angeles",
            }
            and not normalize(
                x
            ).startswith(
                "hotel "
            )
        )
    ]

    return {
        "primary":
            primary,

        "known_entities":
            known[:20],

        "person_candidates":
            persons[:10],
    }


def build_queries(
    scene,
    category,
    role,
    global_primary
):
    text = scene_text(scene)

    local_entities = proper_entities(
        text
    )

    visual_source = " ".join([
        str(
            scene.get(
                "query"
            )
            or ""
        ),
        " ".join(
            str(x)
            for x in (
                scene.get(
                    "must_have"
                )
                or []
            )
        )
        if isinstance(
            scene.get(
                "must_have"
            ),
            list
        )
        else str(
            scene.get(
                "must_have"
            )
            or ""
        ),
    ])

    explicit_visual_entities = (
        proper_entities(
            visual_source
        )
    )

    category = str(
        category
    ).upper()

    identity_entity = None

    if category == "FACE":
        for entity in (
            explicit_visual_entities
        ):
            if normalize(
                entity
            ) not in {
                "los angeles",
                "hotel cecil",
            }:
                identity_entity = entity
                break

        if not identity_entity:
            return {
                "queries": [],
                "anchor": None,
                "identity_entity": None,
                "quarantined": True,
                "reason":
                    "face_without_explicit_visual_identity",
            }

    core = (
        ROLE_QUERY_CORE.get(
            role
        )
        or normalize(
            scene.get(
                "query"
            )
            or ""
        )
    )

    if category == "FACE":
        anchor = identity_entity

    else:
        anchor = (
            global_primary
            or (
                local_entities[0]
                if local_entities
                else None
            )
        )

    queries = []

    def add(value):
        value = " ".join(
            str(value or "")
            .split()
        ).strip()

        if (
            value
            and value.lower()
            not in {
                x.lower()
                for x in queries
            }
        ):
            queries.append(
                value
            )

    if anchor:
        add(
            f"{anchor} {core}"
        )

        if role == "ROOFTOP":
            add(
                f"{anchor} rooftop water tank"
            )

        elif role == "ELEVATOR":
            add(
                f"{anchor} elevator"
            )

        elif role == "HALLWAY":
            add(
                f"{anchor} hallway"
            )

        elif role == "SURVEILLANCE":
            add(
                f"{anchor} CCTV"
            )

        elif role == "DOCUMENT":
            add(
                f"{anchor} document"
            )

    else:
        add(core)

    return {
        "queries":
            queries[
                :MAX_QUERIES
            ],

        "anchor":
            anchor,

        "identity_entity":
            identity_entity,

        "quarantined":
            False,

        "reason":
            None,
    }


def commons_candidates(
    query,
    anchor,
    role,
    desired_family
):
    pages, status, error = (
        commons_search(
            query
        )
    )

    if status != "OK":
        return [], {
            "provider":
                "COMMONS",

            "status":
                status,

            "error":
                error,
        }

    results = []

    wanted = (
        "IMAGE"
        if desired_family
        == "ARCHIVAL_IMAGE"
        else desired_family
    )

    for page in pages:
        infos = (
            page.get(
                "imageinfo"
            )
            or []
        )

        if not infos:
            continue

        info = infos[0]

        mime = normalize(
            info.get("mime")
        )

        mediatype = normalize(
            info.get(
                "mediatype"
            )
        )

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

        title = str(
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

        text = " ".join([
            title,
            description,
            mv("Categories"),
        ])

        entity = (
            entity_score(
                anchor,
                text
            )
            if anchor
            else 70
        )

        rscore, rhits = (
            role_score(
                role,
                text
            )
        )

        neg = negative_terms(
            text
        )

        tech = technical_score(
            info.get(
                "width"
            ),
            info.get(
                "height"
            )
        )

        lic = license_score(
            mv("LicenseShortName")
            + " "
            + mv("UsageTerms")
        )

        score = (
            entity * .35
            + rscore * .30
            + tech * .15
            + lic * .10
            + 10
        )

        if neg:
            score -= 50

        gates = {
            "family":
                family
                == wanted,

            "entity":
                entity >= 100
                if anchor
                else True,

            "role":
                rscore >= 70,

            "negative":
                not bool(neg),

            "license":
                lic >= 80,

            "score":
                score >= 68,
        }

        results.append({
            "provider":
                "WIKIMEDIA_COMMONS",

            "title":
                title,

            "url":
                info.get("url"),

            "family":
                family,

            "entity_score":
                entity,

            "role_score":
                rscore,

            "role_hits":
                rhits,

            "technical":
                tech,

            "license":
                mv(
                    "LicenseShortName"
                ),

            "license_score":
                lic,

            "negative_terms":
                neg,

            "final_score":
                round(
                    max(
                        0,
                        score
                    ),
                    2
                ),

            "gates":
                gates,

            "decision":
                (
                    "TRUE_TARGETED_CANDIDATE"
                    if all(
                        gates.values()
                    )
                    else "REJECT"
                ),
        })

    return results, {
        "provider":
            "COMMONS",

        "status":
            "OK",

        "error":
            None,
    }


def archive_candidates(
    query,
    anchor,
    role
):
    docs, status, error = (
        archive_search(
            query
        )
    )

    if status != "OK":
        return [], {
            "provider":
                "ARCHIVE",

            "status":
                status,

            "error":
                error,
        }

    preliminary = []

    for doc in docs:
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

        title = str(
            doc.get("title")
            or ""
        )

        text = (
            title
            + " "
            + str(
                description
            )
        )

        entity = (
            entity_score(
                anchor,
                text
            )
            if anchor
            else 70
        )

        rscore, rhits = (
            role_score(
                role,
                text
            )
        )

        neg = negative_terms(
            text
        )

        preliminary.append({
            "identifier":
                str(
                    doc.get(
                        "identifier"
                    )
                    or ""
                ),

            "title":
                title,

            "entity_score":
                entity,

            "role_score":
                rscore,

            "role_hits":
                rhits,

            "negative_terms":
                neg,

            "license":
                str(
                    doc.get(
                        "licenseurl"
                    )
                    or ""
                ),
        })

    preliminary.sort(
        key=lambda x: (
            x["entity_score"],
            x["role_score"],
        ),
        reverse=True
    )

    results = []

    # Deep metadata only for the best
    # plausible Archive records.
    deep_targets = [
        x
        for x in preliminary
        if (
            x["entity_score"]
            >= (
                100
                if anchor
                else 0
            )
            and x[
                "role_score"
            ] >= 70
            and not x[
                "negative_terms"
            ]
            and x[
                "identifier"
            ]
        )
    ][:3]

    for item in deep_targets:
        data = request_json(
            ARCHIVE_META
            + item[
                "identifier"
            ]
        )

        if data.get(
            "_status"
        ) != "OK":
            continue

        files = video_files(
            data
        )

        best_file = (
            files[0]
            if files
            else None
        )

        file_score = (
            best_file[
                "score"
            ]
            if best_file
            else 0
        )

        meta = (
            data.get(
                "metadata"
            )
            or {}
        )

        license_text = str(
            meta.get(
                "licenseurl"
            )
            or item[
                "license"
            ]
            or ""
        )

        lic = license_score(
            license_text
        )

        score = (
            item[
                "entity_score"
            ] * .35
            + item[
                "role_score"
            ] * .30
            + file_score * .20
            + lic * .15
        )

        gates = {
            "family":
                True,

            "entity":
                item[
                    "entity_score"
                ] >= (
                    100
                    if anchor
                    else 0
                ),

            "role":
                item[
                    "role_score"
                ] >= 70,

            "real_video_file":
                best_file
                is not None,

            "negative":
                not bool(
                    item[
                        "negative_terms"
                    ]
                ),

            "license":
                lic >= 80,

            "score":
                score >= 68,
        }

        results.append({
            "provider":
                "INTERNET_ARCHIVE",

            "identifier":
                item[
                    "identifier"
                ],

            "title":
                item["title"],

            "family":
                "VIDEO",

            "entity_score":
                item[
                    "entity_score"
                ],

            "role_score":
                item[
                    "role_score"
                ],

            "role_hits":
                item[
                    "role_hits"
                ],

            "best_file":
                best_file,

            "video_file_count":
                len(files),

            "license":
                license_text,

            "license_score":
                lic,

            "negative_terms":
                item[
                    "negative_terms"
                ],

            "final_score":
                round(
                    max(
                        0,
                        score
                    ),
                    2
                ),

            "gates":
                gates,

            "decision":
                (
                    "TRUE_TARGETED_CANDIDATE"
                    if all(
                        gates.values()
                    )
                    else "REJECT"
                ),
        })

        time.sleep(.3)

    return results, {
        "provider":
            "ARCHIVE",

        "status":
            "OK",

        "error":
            None,
    }


def evaluate_scene(
    queue_item,
    scene,
    global_primary
):
    scene_num = int(
        queue_item[
            "scene"
        ]
    )

    category = str(
        queue_item.get(
            "category"
        )
        or "GENERAL"
    ).upper()

    desired = str(
        queue_item.get(
            "desired_family"
        )
        or "IMAGE"
    )

    text = scene_text(
        scene
    )

    role = detect_role(
        category,
        text
    )

    plan = build_queries(
        scene,
        category,
        role,
        global_primary
    )

    if plan[
        "quarantined"
    ]:
        return {
            "scene":
                scene_num,

            "category":
                category,

            "desired_family":
                desired,

            "role":
                role,

            "anchor":
                None,

            "original_query":
                queue_item.get(
                    "query"
                ),

            "repaired_queries":
                [],

            "decision":
                "IDENTITY_QUARANTINED",

            "reason":
                plan["reason"],

            "candidate_count":
                0,

            "approved_count":
                0,

            "best":
                None,

            "top_candidates":
                [],

            "provider_events":
                [],
        }

    candidates = []
    provider_events = []

    seen = set()

    for query in (
        plan["queries"]
    ):
        if desired == "VIDEO":
            for func in (
                archive_candidates,
                commons_candidates,
            ):
                if func is archive_candidates:
                    found, event = func(
                        query,
                        plan["anchor"],
                        role
                    )
                else:
                    found, event = func(
                        query,
                        plan["anchor"],
                        role,
                        desired
                    )

                provider_events.append(
                    {
                        **event,
                        "query":
                            query,
                    }
                )

                for item in found:
                    key = (
                        item.get(
                            "url"
                        )
                        or item.get(
                            "identifier"
                        )
                        or (
                            item[
                                "provider"
                            ]
                            + "|"
                            + item[
                                "title"
                            ]
                        )
                    )

                    if key in seen:
                        continue

                    seen.add(key)
                    candidates.append(
                        item
                    )

                time.sleep(.5)

        else:
            found, event = (
                commons_candidates(
                    query,
                    plan["anchor"],
                    role,
                    desired
                )
            )

            provider_events.append({
                **event,
                "query":
                    query,
            })

            for item in found:
                key = (
                    item.get("url")
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

            time.sleep(.5)

    candidates.sort(
        key=lambda x: (
            x["decision"]
            == "TRUE_TARGETED_CANDIDATE",
            x["final_score"],
            x["entity_score"],
            x["role_score"],
        ),
        reverse=True
    )

    approved = [
        x
        for x in candidates
        if x[
            "decision"
        ]
        == "TRUE_TARGETED_CANDIDATE"
    ]

    best = (
        approved[0]
        if approved
        else None
    )

    return {
        "scene":
            scene_num,

        "category":
            category,

        "desired_family":
            desired,

        "role":
            role,

        "anchor":
            plan["anchor"],

        "identity_entity":
            plan[
                "identity_entity"
            ],

        "original_query":
            queue_item.get(
                "query"
            ),

        "repaired_queries":
            plan["queries"],

        "candidate_count":
            len(candidates),

        "approved_count":
            len(approved),

        "decision":
            (
                "TRUE_TARGETED_CANDIDATE_FOUND"
                if best
                else "KEEP_CURRENT"
            ),

        "best":
            best,

        "top_candidates":
            candidates[:6],

        "provider_events":
            provider_events,
    }


def evaluate():
    vi260 = load_gate(
        VI260
    )

    vi200 = load_gate(
        VI200
    )

    vi235 = load_gate(
        VI235
    )

    if not vi260:
        raise RuntimeError(
            "vi260_missing"
        )

    short_id = str(
        vi260.get(
            "short_id"
        )
        or ""
    )

    scenes = load_scene_map(
        short_id
    )

    anchors = build_anchors(
        vi200,
        scenes
    )

    global_primary = (
        anchors[
            "primary"
        ]
    )

    queue = (
        vi260.get(
            "search_queue"
        )
        or []
    )

    local_audit = []

    for decision in (
        vi260.get(
            "decisions"
        )
        or []
    ):
        if (
            decision.get(
                "provenance_status"
            )
            != "UNVERIFIED_PROVENANCE"
        ):
            continue

        local_audit.append({
            "scene":
                decision[
                    "scene"
                ],

            **local_provenance_audit(
                decision.get(
                    "current_path"
                )
            ),
        })

    identity_quarantined = []

    searchable = []

    # First repair/quarantine all queue entries.
    for item in queue:
        scene_num = int(
            item["scene"]
        )

        category = str(
            item.get(
                "category"
            )
            or ""
        ).upper()

        scene = scenes.get(
            scene_num,
            {}
        )

        role = detect_role(
            category,
            scene_text(scene)
        )

        plan = build_queries(
            scene,
            category,
            role,
            global_primary
        )

        if plan[
            "quarantined"
        ]:
            identity_quarantined.append(
                scene_num
            )

            continue

        searchable.append(
            item
        )

    targets = searchable[
        :MAX_NETWORK_SCENES
    ]

    results = []

    for item in targets:
        results.append(
            evaluate_scene(
                item,
                scenes.get(
                    int(
                        item[
                            "scene"
                        ]
                    ),
                    {}
                ),
                global_primary
            )
        )

    approved_scenes = [
        x["scene"]
        for x in results
        if x[
            "decision"
        ]
        == "TRUE_TARGETED_CANDIDATE_FOUND"
    ]

    keep_current = [
        x["scene"]
        for x in results
        if x[
            "decision"
        ]
        == "KEEP_CURRENT"
    ]

    provider_errors = [
        {
            "scene":
                result[
                    "scene"
                ],

            **event,
        }
        for result in results
        for event in result[
            "provider_events"
        ]
        if event[
            "status"
        ] not in {
            "OK"
        }
    ]

    corrections = {
        "blind_exterior_suffix":
            "REMOVED",

        "scene_role_query_repair":
            True,

        "file_namespace_role_bug":
            "REMOVED",

        "identity_generic_face_search":
            "QUARANTINED",

        "secondary_location_entity_as_primary":
            "DISALLOWED",

        "video_candidate":
            "REAL_FILE_METADATA_REQUIRED",

        "automatic_replace":
            False,
    }

    warnings = []

    if identity_quarantined:
        warnings.append(
            "identity_scenes_quarantined"
        )

    if provider_errors:
        warnings.append(
            "provider_errors_present"
        )

    if not approved_scenes:
        warnings.append(
            "no_targeted_candidate_approved"
        )

    report = {
        "version":
            VERSION,

        "status":
            "VI300_TARGETED_GLOBAL_SEARCH_CERTIFIED",

        "short_id":
            short_id,

        "anchors":
            anchors,

        "corrections":
            corrections,

        "network_target_scenes":
            [
                int(
                    x["scene"]
                )
                for x in targets
            ],

        "identity_quarantined_scenes":
            identity_quarantined,

        "approved_scenes":
            approved_scenes,

        "keep_current_scenes":
            keep_current,

        "local_provenance_audit":
            local_audit,

        "results":
            results,

        "provider_errors":
            provider_errors,

        "blockers":
            [],

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
        " VI300 TARGETED GLOBAL SEARCH"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "PRIMARY ANCHOR:",
        r["anchors"][
            "primary"
        ]
    )

    print(
        "KNOWN ENTITIES:",
        r["anchors"][
            "known_entities"
        ]
    )

    print(
        "NETWORK TARGETS:",
        r[
            "network_target_scenes"
        ]
    )

    print(
        "IDENTITY QUARANTINED:",
        r[
            "identity_quarantined_scenes"
        ]
    )

    print(
        "APPROVED:",
        r[
            "approved_scenes"
        ]
    )

    print(
        "KEEP CURRENT:",
        r[
            "keep_current_scenes"
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
    print(
        "===== QUERY REPAIR / SEARCH RESULTS ====="
    )

    for x in r[
        "results"
    ]:
        print()
        print(
            "SCENE:",
            x["scene"]
        )

        print(
            " CATEGORY:",
            x["category"]
        )

        print(
            " ROLE:",
            x["role"]
        )

        print(
            " DESIRED:",
            x[
                "desired_family"
            ]
        )

        print(
            " ANCHOR:",
            x["anchor"]
        )

        print(
            " OLD QUERY:",
            x[
                "original_query"
            ]
        )

        print(
            " NEW QUERIES:",
            x[
                "repaired_queries"
            ]
        )

        print(
            " CANDIDATES:",
            x[
                "candidate_count"
            ]
        )

        print(
            " APPROVED:",
            x[
                "approved_count"
            ]
        )

        print(
            " DECISION:",
            x["decision"]
        )

        best = x.get(
            "best"
        )

        if best:
            print(
                " WINNER:",
                best[
                    "title"
                ]
            )

            print(
                " PROVIDER:",
                best[
                    "provider"
                ]
            )

            print(
                " FAMILY:",
                best[
                    "family"
                ]
            )

            print(
                " ENTITY:",
                best[
                    "entity_score"
                ]
            )

            print(
                " ROLE:",
                best[
                    "role_score"
                ]
            )

            print(
                " LICENSE:",
                best[
                    "license"
                ]
            )

            print(
                " FINAL:",
                best[
                    "final_score"
                ]
            )

            print(
                " GATES:",
                best[
                    "gates"
                ]
            )

            if best.get(
                "best_file"
            ):
                print(
                    " BEST FILE:",
                    best[
                        "best_file"
                    ]
                )

        for item in (
            x[
                "top_candidates"
            ][:4]
        ):
            print(
                "  -",
                item[
                    "decision"
                ],
                "|",
                item[
                    "provider"
                ],
                "|",
                item[
                    "title"
                ],
                "| entity=",
                item[
                    "entity_score"
                ],
                "| role=",
                item[
                    "role_score"
                ],
                "| final=",
                item[
                    "final_score"
                ],
            )

    print()
    print(
        "===== LOCAL PROVENANCE HINTS ====="
    )

    for x in r[
        "local_provenance_audit"
    ]:
        if (
            x["hash_hits"]
            or x["name_hits"]
        ):
            print(
                "SCENE",
                x["scene"],
                "| HASH HITS:",
                x["hash_hits"],
                "| NAME HITS:",
                x["name_hits"],
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
