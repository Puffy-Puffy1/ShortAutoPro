#!/usr/bin/env python3
from short_id_runtime_v1 import resolve_short_id as _sap_resolve_short_id

import copy
import hashlib
import html
import json
import os
import re
import struct
import time
from pathlib import Path
from collections import Counter
from urllib.parse import quote, urlparse

import requests


VERSION = "600.00"

BASE = Path.home() / "ShortAutoPro"
LOG = BASE / "logs/producao"

VI330 = LOG / "vi330_00_controlled_real_ab_latest.json"
VI420 = LOG / "vi420_00_batch_deep_ab_latest.json"
VI500 = LOG / "vi500_00_global_provenance_identity_latest.json"
VI550 = LOG / "vi550_00_role_provenance_repair_latest.json"

OUT = (
    LOG /
    "vi600_00_provenance_replacement_engine_latest.json"
)

CACHE = (
    BASE /
    "temp/vi400_cache/metadata_cache.json"
)

PROVENANCE_SANDBOX = (
    BASE /
    "temp/vi600_provenance_recovery"
)

REPLACEMENT_SANDBOX = (
    BASE /
    "temp/vi600_replacements"
)

SHADOW = (
    BASE /
    "temp/vi600_shadow/"
    "motion_plan_2026-09-01_1433_vi600_shadow.json"
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
        "ShortAutoPro/600.00 "
        "(provenance recovery and licensed staging)"
}


CACHE_TTL = 86400

MAX_RESULTS = 15

MAX_TOTAL_DOWNLOAD = (
    50 * 1024 * 1024
)

MAX_IMAGE_DOWNLOAD = (
    10 * 1024 * 1024
)

MAX_VIDEO_DOWNLOAD = (
    20 * 1024 * 1024
)

MAX_PROVENANCE_ATTEMPTS = 4


TARGET_RATIO = 9 / 16


ROLE_TERMS = {
    "ELEVATOR": {
        "elevator",
        "lift",
        "elevator interior",
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
    },

    "DOCUMENT": {
        "official document",
        "document",
        "record",
        "report",
        "certificate",
        "police report",
        "autopsy",
        "coroner",
        "court record",
        "newspaper",
    },

    "GENERIC_HUMAN": {
        "person",
        "woman",
        "man",
        "human",
        "silhouette",
        "figure",
    },
}


ANONYMITY_TERMS = {
    "silhouette",
    "back view",
    "rear view",
    "from behind",
    "anonymous",
    "unrecognizable",
    "unrecognisable",
    "shadow",
    "faceless",
    "face hidden",
}


NEGATIVE_TERMS = {
    "advertisement",
    "logo",
    "poster",
    "screenshot",
    "drawing",
    "diagram",
    "gameplay",
    "review",
    "reaction",
    "podcast",
    "trailer",
    "teaser",
    "livestream",
    "live stream",
}


ARCHIVAL_TERMS = {
    "archive",
    "archival",
    "historical",
    "historic",
    "official",
    "record",
    "report",
    "document",
    "scan",
    "scanned",
    "newspaper",
}


def load_gate(path, required=False):
    if not path.exists():
        if required:
            raise RuntimeError(
                f"missing:{path.name}"
            )

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


def normalize(value):
    text = html.unescape(
        str(value or "")
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"^\s*File\s*:\s*",
        "",
        text,
        flags=re.I
    )

    text = (
        text
        .replace("_", " ")
        .replace("-", " ")
        .lower()
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


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


def clamp(value):
    return round(
        max(
            0,
            min(
                100,
                float(value)
            )
        ),
        2
    )


def by_scene(items):
    result = {}

    for item in items or []:
        try:
            result[
                int(item["scene"])
            ] = item

        except Exception:
            continue

    return result


def term_hits(text, terms):
    low = normalize(text)

    return sorted({
        term
        for term in terms
        if term in low
    })


def load_cache():
    if not CACHE.exists():
        return {
            "entries": {}
        }

    try:
        return json.loads(
            CACHE.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return {
            "entries": {}
        }


def save_cache(cache):
    CACHE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    CACHE.write_text(
        json.dumps(
            cache,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def cached_json(
    url,
    params,
    key,
    cache
):
    now = time.time()

    entry = (
        cache.get(
            "entries",
            {}
        ).get(key)
    )

    if entry:
        age = (
            now
            - float(
                entry.get(
                    "time",
                    0
                )
            )
        )

        if age < CACHE_TTL:
            return (
                entry.get(
                    "data",
                    {}
                ),
                "CACHE"
            )

    wait = 4

    for attempt in range(3):
        try:
            r = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=30
            )

            if r.status_code == 429:
                retry = (
                    r.headers.get(
                        "Retry-After"
                    )
                    or wait
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
                    20
                )

                continue

            r.raise_for_status()

            data = r.json()

            cache.setdefault(
                "entries",
                {}
            )[key] = {
                "time":
                    now,

                "data":
                    data,
            }

            return data, "NETWORK"

        except Exception as exc:
            if attempt == 2:
                return (
                    {
                        "_error":
                            type(exc).__name__
                            + ":"
                            + str(exc)[:160]
                    },
                    "ERROR"
                )

            time.sleep(wait)

            wait = min(
                wait * 2,
                20
            )

    return {
        "_error":
            "unknown"
    }, "ERROR"


def license_score(text):
    low = normalize(text)

    if any(
        value in low
        for value in (
            "public domain",
            "publicdomain",
            "cc0",
            "zero/1.0",
        )
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


def technical_score(width, height):
    pixels = (
        int(width or 0)
        * int(height or 0)
    )

    if pixels >= 4_000_000:
        return 100

    if pixels >= 2_000_000:
        return 95

    if pixels >= 1_000_000:
        return 90

    if pixels >= 500_000:
        return 75

    if pixels >= 200_000:
        return 60

    return 40


def geometry(width, height):
    width = int(width or 0)
    height = int(height or 0)

    if (
        width <= 0
        or height <= 0
    ):
        return {
            "aspect_score":
                0,

            "cover_scale":
                None,

            "retained_fraction":
                None,
        }

    ratio = width / height

    error = abs(
        ratio - TARGET_RATIO
    )

    aspect_score = max(
        0,
        min(
            100,
            100
            - error * 150
        )
    )

    scale = max(
        1080 / width,
        1920 / height
    )

    scaled_area = (
        width
        * scale
        * height
        * scale
    )

    retained = min(
        1.0,
        (
            1080 * 1920
        )
        / scaled_area
    )

    return {
        "aspect_score":
            round(
                aspect_score,
                2
            ),

        "cover_scale":
            round(
                scale,
                2
            ),

        "retained_fraction":
            round(
                retained,
                3
            ),
    }


def jpeg_size(path):
    try:
        with open(path, "rb") as f:
            if (
                f.read(2)
                != b"\xff\xd8"
            ):
                return None

            while True:
                byte = f.read(1)

                if not byte:
                    return None

                if byte != b"\xff":
                    continue

                while byte == b"\xff":
                    byte = f.read(1)

                marker = byte[0]

                if marker in {
                    0xD8,
                    0xD9,
                }:
                    continue

                raw = f.read(2)

                if len(raw) != 2:
                    return None

                length = struct.unpack(
                    ">H",
                    raw
                )[0]

                if marker in {
                    0xC0, 0xC1, 0xC2,
                    0xC3, 0xC5, 0xC6,
                    0xC7, 0xC9, 0xCA,
                    0xCB, 0xCD, 0xCE,
                    0xCF,
                }:
                    data = f.read(5)

                    if len(data) != 5:
                        return None

                    height, width = struct.unpack(
                        ">HH",
                        data[1:5]
                    )

                    return width, height

                f.seek(
                    length - 2,
                    1
                )

    except Exception:
        return None


def png_size(path):
    try:
        with open(path, "rb") as f:
            data = f.read(24)

        if (
            len(data) >= 24
            and data[:8]
            == b"\x89PNG\r\n\x1a\n"
        ):
            return struct.unpack(
                ">II",
                data[16:24]
            )

    except Exception:
        pass

    return None


def image_size(path):
    ext = path.suffix.lower()

    if ext in {
        ".jpg",
        ".jpeg",
    }:
        return jpeg_size(path)

    if ext == ".png":
        return png_size(path)

    return None


def file_magic(path):
    with open(path, "rb") as f:
        head = f.read(16)

    return {
        "jpeg":
            head[:2]
            == b"\xff\xd8",

        "png":
            head[:8]
            == b"\x89PNG\r\n\x1a\n",

        "webm":
            head[:4]
            == b"\x1a\x45\xdf\xa3",

        "mp4":
            (
                len(head) >= 8
                and head[4:8]
                == b"ftyp"
            ),

        "first16":
            head.hex(),
    }


def controlled_download(
    url,
    destination,
    budget,
    per_file_limit
):
    if (
        budget["used"]
        >= MAX_TOTAL_DOWNLOAD
    ):
        raise RuntimeError(
            "global_download_budget_exhausted"
        )

    remaining = (
        MAX_TOTAL_DOWNLOAD
        - budget["used"]
    )

    effective_limit = min(
        per_file_limit,
        remaining
    )

    if effective_limit < 10_000:
        raise RuntimeError(
            "download_budget_too_small"
        )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    part = Path(
        str(destination)
        + ".part"
    )

    part.unlink(
        missing_ok=True
    )

    with requests.get(
        url,
        headers=HEADERS,
        timeout=45,
        stream=True
    ) as response:
        response.raise_for_status()

        declared_header = (
            response.headers.get(
                "Content-Length"
            )
        )

        if declared_header:
            try:
                declared = int(
                    declared_header
                )

                if declared > effective_limit:
                    raise RuntimeError(
                        "declared_file_exceeds_limit"
                    )

            except ValueError:
                pass

        total = 0

        with open(
            part,
            "wb"
        ) as f:
            for chunk in (
                response.iter_content(
                    256 * 1024
                )
            ):
                if not chunk:
                    continue

                total += len(chunk)

                if total > effective_limit:
                    raise RuntimeError(
                        "stream_exceeds_limit"
                    )

                f.write(chunk)

    if total < 10_000:
        part.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            "download_too_small"
        )

    os.replace(
        part,
        destination
    )

    budget["used"] += total

    return {
        "bytes":
            total,

        "content_type":
            str(
                response.headers.get(
                    "Content-Type"
                )
                or ""
            ).lower(),
    }


URL_RE = re.compile(
    r'https?://[^\s"\'<>]+'
)


def allowed_direct_source(url):
    low = url.lower()

    return (
        "upload.wikimedia.org/"
        in low
        or "archive.org/download/"
        in low
    )


def trace_source_urls(
    current,
    traces
):
    current_hash = str(
        current.get("sha256")
        or ""
    )

    current_path = str(
        current.get("path")
        or ""
    )

    basename = (
        Path(current_path).name
        if current_path
        else ""
    )

    urls = []

    for trace in traces or []:
        trace_file = trace.get(
            "file"
        )

        if not trace_file:
            continue

        path = Path(
            trace_file
        )

        if not path.exists():
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore"
            )

        except Exception:
            continue

        positions = []

        for term in (
            current_hash,
            basename,
        ):
            if not term:
                continue

            index = text.find(term)

            if index >= 0:
                positions.append(index)

        for index in positions:
            start = max(
                0,
                index - 3000
            )

            end = min(
                len(text),
                index + 3000
            )

            context = text[
                start:end
            ]

            for url in URL_RE.findall(
                context
            ):
                url = url.rstrip(
                    ".,);]}"
                )

                if (
                    allowed_direct_source(
                        url
                    )
                    and url not in urls
                ):
                    urls.append(url)

    return urls[:5]


def verify_exact_source(
    scene,
    current,
    traces,
    budget
):
    urls = trace_source_urls(
        current,
        traces
    )

    attempts = []

    for index, url in enumerate(
        urls[:2],
        start=1
    ):
        suffix = (
            Path(
                urlparse(
                    url
                ).path
            ).suffix
            or ".bin"
        )

        destination = (
            PROVENANCE_SANDBOX /
            f"scene_{scene:02d}_source_{index}{suffix}"
        )

        try:
            result = controlled_download(
                url,
                destination,
                budget,
                MAX_VIDEO_DOWNLOAD
            )

        except Exception as exc:
            attempts.append({
                "url":
                    url,

                "status":
                    "DOWNLOAD_FAILED",

                "error":
                    type(exc).__name__
                    + ":"
                    + str(exc),
            })

            continue

        digest = sha256(
            destination
        )

        exact = (
            digest
            == current.get(
                "sha256"
            )
        )

        attempts.append({
            "url":
                url,

            "status":
                (
                    "EXACT_MATCH"
                    if exact
                    else "HASH_MISMATCH"
                ),

            "sha256":
                digest,

            "bytes":
                result[
                    "bytes"
                ],

            "sandbox_path":
                str(
                    destination
                ),
        })

        if exact:
            return {
                "verified":
                    True,

                "url":
                    url,

                "sha256":
                    digest,

                "sandbox_path":
                    str(
                        destination
                    ),

                "attempts":
                    attempts,
            }

    return {
        "verified":
            False,

        "attempts":
            attempts,
    }


def entity_truth(
    text
):
    low = normalize(text)

    hotel = (
        "hotel cecil" in low
        or "cecil hotel" in low
    )

    los_angeles = (
        "los angeles" in low
        or "hotel cecil la" in low
    )

    elisa = (
        "elisa lam" in low
    )

    return {
        "hotel_cecil":
            hotel,

        "los_angeles":
            los_angeles,

        "elisa_lam":
            elisa,

        "case_truth":
            (
                elisa
                or (
                    hotel
                    and los_angeles
                )
            ),
    }


def commons_search(
    query,
    family,
    cache
):
    params = {
        "action":
            "query",

        "generator":
            "search",

        "gsrsearch":
            query,

        "gsrnamespace":
            6,

        "gsrlimit":
            MAX_RESULTS,

        "prop":
            "imageinfo",

        "iiprop":
            "url|size|mime|mediatype|extmetadata",

        "format":
            "json",

        "formatversion":
            2,
    }

    key = (
        "commons|"
        + family
        + "|"
        + query.lower()
    )

    data, source = cached_json(
        COMMONS,
        params,
        key,
        cache
    )

    pages = (
        data.get(
            "query",
            {}
        ).get(
            "pages",
            []
        )
        if isinstance(
            data,
            dict
        )
        else []
    )

    results = []

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

        actual_family = (
            "VIDEO"
            if (
                mime.startswith(
                    "video/"
                )
                or mediatype
                == "video"
            )
            else
            "IMAGE"
        )

        if (
            actual_family
            != family
        ):
            continue

        metadata = (
            info.get(
                "extmetadata"
            )
            or {}
        )

        def mv(key):
            value = (
                metadata.get(key)
                or {}
            )

            if isinstance(
                value,
                dict
            ):
                return str(
                    value.get(
                        "value"
                    )
                    or ""
                )

            return str(
                value or ""
            )

        title = str(
            page.get(
                "title"
            )
            or ""
        )

        # Search query intentionally excluded.
        evidence = " ".join([
            title,
            mv(
                "ImageDescription"
            ),
            mv(
                "Categories"
            ),
            mv(
                "ObjectName"
            ),
            mv(
                "Credit"
            ),
        ])

        results.append({
            "provider":
                "WIKIMEDIA_COMMONS",

            "key":
                info.get("url")
                or title,

            "title":
                title,

            "url":
                info.get("url"),

            "direct_url":
                info.get("url"),

            "family":
                actual_family,

            "mime":
                mime,

            "evidence":
                evidence,

            "width":
                int(
                    info.get(
                        "width"
                    )
                    or 0
                ),

            "height":
                int(
                    info.get(
                        "height"
                    )
                    or 0
                ),

            "declared_bytes":
                int(
                    info.get(
                        "size"
                    )
                    or 0
                ),

            "license":
                mv(
                    "LicenseShortName"
                ),

            "license_text":
                (
                    mv(
                        "LicenseShortName"
                    )
                    + " "
                    + mv(
                        "UsageTerms"
                    )
                ),
        })

    return results, source


def archive_search(
    query,
    cache
):
    params = {
        "q":
            f"({query}) AND mediatype:movies",

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

    key = (
        "archive-search|"
        + query.lower()
    )

    data, source = cached_json(
        ARCHIVE_SEARCH,
        params,
        key,
        cache
    )

    docs = (
        data.get(
            "response",
            {}
        ).get(
            "docs",
            []
        )
        if isinstance(
            data,
            dict
        )
        else []
    )

    results = []

    for item in docs:
        description = (
            item.get(
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

        identifier = str(
            item.get(
                "identifier"
            )
            or ""
        )

        title = str(
            item.get(
                "title"
            )
            or ""
        )

        results.append({
            "provider":
                "INTERNET_ARCHIVE",

            "key":
                "ia:"
                + identifier,

            "identifier":
                identifier,

            "title":
                title,

            "family":
                "VIDEO",

            "evidence":
                title
                + " "
                + str(
                    description
                ),

            "license":
                str(
                    item.get(
                        "licenseurl"
                    )
                    or ""
                ),

            "license_text":
                str(
                    item.get(
                        "licenseurl"
                    )
                    or ""
                ),
        })

    return results, source


def archive_deep(
    candidate,
    cache
):
    identifier = candidate.get(
        "identifier"
    )

    if not identifier:
        return None, "ERROR"

    key = (
        "archive-meta|"
        + identifier
    )

    data, source = cached_json(
        ARCHIVE_META
        + identifier,
        None,
        key,
        cache
    )

    if (
        not isinstance(
            data,
            dict
        )
        or data.get(
            "_error"
        )
    ):
        return None, source

    metadata = (
        data.get(
            "metadata"
        )
        or {}
    )

    evidence = " ".join(
        str(
            metadata.get(key)
            or ""
        )
        for key in (
            "title",
            "description",
            "subject",
            "collection",
            "creator",
        )
    )

    files = []

    for item in (
        data.get(
            "files"
        )
        or []
    ):
        name = str(
            item.get("name")
            or ""
        )

        fmt = normalize(
            item.get(
                "format"
            )
        )

        ext = (
            Path(name)
            .suffix.lower()
        )

        if not (
            ext in {
                ".mp4",
                ".webm",
                ".ogv",
                ".mpeg",
                ".mpg",
                ".mov",
                ".m4v",
            }
            or "mpeg4"
            in fmt
            or "webm"
            in fmt
            or "h.264"
            in fmt
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

        files.append({
            "name":
                name,

            "size":
                int(
                    number("size")
                ),

            "width":
                int(
                    number("width")
                ),

            "height":
                int(
                    number("height")
                ),

            "length":
                number("length"),

            "format":
                item.get(
                    "format"
                ),
        })

    files.sort(
        key=lambda item: (
            item["width"]
            * item["height"],
            item["size"],
        ),
        reverse=True
    )

    if not files:
        return None, source

    best = files[0]

    result = dict(
        candidate
    )

    result[
        "evidence"
    ] = evidence

    result[
        "best_file"
    ] = best

    result[
        "width"
    ] = best["width"]

    result[
        "height"
    ] = best["height"]

    result[
        "declared_bytes"
    ] = best["size"]

    result[
        "license_text"
    ] = str(
        metadata.get(
            "licenseurl"
        )
        or candidate.get(
            "license_text"
        )
        or ""
    )

    result[
        "license"
    ] = result[
        "license_text"
    ]

    result[
        "direct_url"
    ] = (
        "https://archive.org/download/"
        + quote(
            identifier,
            safe=""
        )
        + "/"
        + quote(
            best["name"]
        )
    )

    return result, source


def evaluate_candidate(
    candidate,
    policy
):
    evidence = candidate.get(
        "evidence"
    ) or ""

    role = policy[
        "role"
    ]

    role_hits = term_hits(
        evidence,
        ROLE_TERMS.get(
            role,
            set()
        )
    )

    negatives = term_hits(
        evidence,
        NEGATIVE_TERMS
    )

    anonymity_hits = term_hits(
        evidence,
        ANONYMITY_TERMS
    )

    archival_hits = term_hits(
        evidence,
        ARCHIVAL_TERMS
    )

    entity = entity_truth(
        evidence
    )

    context_hits = term_hits(
        evidence,
        policy.get(
            "context_terms",
            set()
        )
    )

    lic = license_score(
        candidate.get(
            "license_text"
        )
    )

    tech = technical_score(
        candidate.get(
            "width"
        ),
        candidate.get(
            "height"
        )
    )

    geo = geometry(
        candidate.get(
            "width"
        ),
        candidate.get(
            "height"
        )
    )

    if policy.get(
        "case_specific"
    ):
        entity_gate = (
            entity[
                "case_truth"
            ]
        )

    else:
        entity_gate = True

    if policy.get(
        "anonymous_human"
    ):
        anonymity_gate = bool(
            anonymity_hits
        )

    else:
        anonymity_gate = True

    context_gate = (
        True
        if not policy.get(
            "context_terms"
        )
        else bool(
            context_hits
        )
    )

    archival_gate = (
        True
        if not policy.get(
            "archival_required"
        )
        else bool(
            archival_hits
        )
    )

    gates = {
        "family":
            candidate.get(
                "family"
            )
            == policy[
                "family"
            ],

        "role":
            bool(
                role_hits
            ),

        "entity":
            entity_gate,

        "anonymous_safety":
            anonymity_gate,

        "context":
            context_gate,

        "archival":
            archival_gate,

        "negative_absent":
            not bool(
                negatives
            ),

        "license":
            lic >= 80,

        "technical":
            tech >= 60,
    }

    score = 0

    if role_hits:
        score += 30

    if entity_gate:
        score += 20

    if anonymity_gate:
        score += 10

    if context_gate:
        score += 10

    if archival_gate:
        score += 5

    if lic >= 80:
        score += 10

    score += tech * .10

    score += (
        geo[
            "aspect_score"
        ]
        * .05
    )

    score = clamp(
        score
    )

    return {
        **candidate,

        "role_hits":
            role_hits,

        "context_hits":
            context_hits,

        "anonymity_hits":
            anonymity_hits,

        "archival_hits":
            archival_hits,

        "entity_truth":
            entity,

        "negative_hits":
            negatives,

        "license_score":
            lic,

        "technical_score":
            tech,

        "geometry":
            geo,

        "gates":
            gates,

        "score":
            score,

        "decision":
            (
                "LICENSED_TRUE_CANDIDATE"
                if all(
                    gates.values()
                )
                else "REJECT"
            ),
    }


def build_policies():
    return {
        "ELEVATOR_IMAGE": {
            "scenes":
                [1],

            "role":
                "ELEVATOR",

            "family":
                "IMAGE",

            "case_specific":
                False,

            "anonymous_human":
                False,

            "queries": [
                "old hotel elevator interior doors",
                "vintage elevator interior",
            ],
        },

        "HALLWAY_IMAGE": {
            "scenes":
                [3, 8],

            "role":
                "HALLWAY",

            "family":
                "IMAGE",

            "case_specific":
                False,

            "anonymous_human":
                False,

            "queries": [
                "hotel hallway corridor interior",
                "empty hotel corridor",
            ],
        },

        "HUMAN_ELEVATOR": {
            "scenes":
                [5],

            "role":
                "GENERIC_HUMAN",

            "family":
                "IMAGE",

            "anonymous_human":
                True,

            "case_specific":
                False,

            "context_terms": {
                "elevator",
                "lift",
            },

            "queries": [
                "woman elevator silhouette back view",
                "woman entering elevator from behind",
            ],
        },

        "HUMAN_HALLWAY": {
            "scenes":
                [6],

            "role":
                "GENERIC_HUMAN",

            "family":
                "IMAGE",

            "anonymous_human":
                True,

            "case_specific":
                False,

            "context_terms": {
                "hallway",
                "corridor",
            },

            "queries": [
                "person hallway silhouette back view",
                "person corridor silhouette from behind",
            ],
        },

        "ELEVATOR_VIDEO": {
            "scenes":
                [7],

            "role":
                "ELEVATOR",

            "family":
                "VIDEO",

            "anonymous_human":
                False,

            "case_specific":
                False,

            "queries": [
                "elevator interior doors",
                "hotel elevator interior",
            ],
        },

        "ROOFTOP_IMAGE": {
            "scenes":
                [10, 11],

            "role":
                "ROOFTOP",

            "family":
                "IMAGE",

            "anonymous_human":
                False,

            "case_specific":
                False,

            "queries": [
                "rooftop water tank building",
                "rooftop water tower building",
            ],
        },

        "FACTUAL_DOCUMENT": {
            "scenes":
                [12],

            "role":
                "DOCUMENT",

            "family":
                "IMAGE",

            "anonymous_human":
                False,

            "case_specific":
                True,

            "archival_required":
                True,

            "queries": [
                "Elisa Lam official report document",
                "Hotel Cecil Los Angeles official record",
            ],
        },
    }


def production_hashes(
    current_map
):
    return {
        item.get(
            "sha256"
        ):
            item.get(
                "path"
            )
        for item in (
            current_map.values()
        )
        if item.get(
            "sha256"
        )
    }


def stage_candidate(
    scene,
    candidate,
    budget,
    production
):
    direct_url = candidate.get(
        "direct_url"
    )

    if not direct_url:
        return {
            "staged":
                False,

            "reason":
                "direct_url_missing",
        }

    family = candidate.get(
        "family"
    )

    mime = normalize(
        candidate.get(
            "mime"
        )
    )

    if family == "VIDEO":
        per_limit = (
            MAX_VIDEO_DOWNLOAD
        )

        if "webm" in mime:
            suffix = ".webm"

        else:
            suffix = (
                Path(
                    urlparse(
                        direct_url
                    ).path
                ).suffix
                or ".mp4"
            )

    else:
        per_limit = (
            MAX_IMAGE_DOWNLOAD
        )

        if "png" in mime:
            suffix = ".png"

        else:
            suffix = (
                Path(
                    urlparse(
                        direct_url
                    ).path
                ).suffix
                or ".jpg"
            )

    declared = int(
        candidate.get(
            "declared_bytes"
        )
        or 0
    )

    if (
        declared
        and declared
        > per_limit
    ):
        return {
            "staged":
                False,

            "reason":
                "declared_size_over_limit",
        }

    destination = (
        REPLACEMENT_SANDBOX /
        f"scene_{scene:02d}_candidate{suffix}"
    )

    try:
        download = controlled_download(
            direct_url,
            destination,
            budget,
            per_limit
        )

    except Exception as exc:
        return {
            "staged":
                False,

            "reason":
                type(exc).__name__
                + ":"
                + str(exc),
        }

    digest = sha256(
        destination
    )

    duplicate = production.get(
        digest
    )

    if duplicate:
        return {
            "staged":
                False,

            "reason":
                "duplicate_production_hash",

            "duplicate_path":
                duplicate,

            "sandbox_path":
                str(
                    destination
                ),
        }

    magic = file_magic(
        destination
    )

    if family == "IMAGE":
        magic_ok = (
            magic["jpeg"]
            or magic["png"]
        )

        actual_dimensions = image_size(
            destination
        )

    else:
        magic_ok = (
            magic["webm"]
            or magic["mp4"]
        )

        actual_dimensions = (
            int(
                candidate.get(
                    "width"
                )
                or 0
            ),
            int(
                candidate.get(
                    "height"
                )
                or 0
            ),
        )

    if not magic_ok:
        return {
            "staged":
                False,

            "reason":
                "file_magic_failed",

            "sandbox_path":
                str(
                    destination
                ),
        }

    return {
        "staged":
            True,

        "scene":
            scene,

        "title":
            candidate.get(
                "title"
            ),

        "provider":
            candidate.get(
                "provider"
            ),

        "family":
            family,

        "sandbox_path":
            str(
                destination
            ),

        "sha256":
            digest,

        "bytes":
            download[
                "bytes"
            ],

        "dimensions":
            (
                list(
                    actual_dimensions
                )
                if actual_dimensions
                else None
            ),

        "license":
            candidate.get(
                "license"
            ),

        "license_score":
            candidate.get(
                "license_score"
            ),

        "score":
            candidate.get(
                "score"
            ),

        "role_hits":
            candidate.get(
                "role_hits"
            ),

        "anonymity_hits":
            candidate.get(
                "anonymity_hits"
            ),

        "entity_truth":
            candidate.get(
                "entity_truth"
            ),

        "magic":
            magic,

        "automatic_replace":
            False,
    }


def search_group(
    policy,
    cache,
    cache_stats
):
    raw = []

    for query in policy[
        "queries"
    ]:
        if (
            policy["family"]
            == "VIDEO"
        ):
            commons, source = (
                commons_search(
                    query,
                    "VIDEO",
                    cache
                )
            )

            cache_stats[
                source
            ] = (
                cache_stats.get(
                    source,
                    0
                )
                + 1
            )

            raw.extend(
                commons
            )

            archive, source = (
                archive_search(
                    query,
                    cache
                )
            )

            cache_stats[
                source
            ] = (
                cache_stats.get(
                    source,
                    0
                )
                + 1
            )

            # Cheap prefilter before Archive deep lookup.
            for item in archive:
                evidence = item.get(
                    "evidence"
                ) or ""

                if not term_hits(
                    evidence,
                    ROLE_TERMS[
                        policy["role"]
                    ]
                ):
                    continue

                deep, deep_source = (
                    archive_deep(
                        item,
                        cache
                    )
                )

                cache_stats[
                    deep_source
                ] = (
                    cache_stats.get(
                        deep_source,
                        0
                    )
                    + 1
                )

                if deep:
                    raw.append(
                        deep
                    )

        else:
            found, source = (
                commons_search(
                    query,
                    "IMAGE",
                    cache
                )
            )

            cache_stats[
                source
            ] = (
                cache_stats.get(
                    source,
                    0
                )
                + 1
            )

            raw.extend(
                found
            )

    dedup = {}

    for item in raw:
        key = (
            item.get("key")
            or item.get(
                "direct_url"
            )
            or item.get(
                "title"
            )
        )

        dedup[key] = item

    evaluated = [
        evaluate_candidate(
            item,
            policy
        )
        for item in (
            dedup.values()
        )
    ]

    evaluated.sort(
        key=lambda item: (
            item[
                "decision"
            ]
            == "LICENSED_TRUE_CANDIDATE",
            item["score"],
            item[
                "technical_score"
            ],
        ),
        reverse=True
    )

    return evaluated


def find_shadow_source(
    vi550
):
    value = (
        vi550.get(
            "shadow_plan",
            {}
        ).get(
            "path"
        )
    )

    if not value:
        return None

    path = Path(
        value
    )

    return (
        path
        if path.exists()
        else None
    )


def build_shadow(
    vi550,
    payload
):
    source = find_shadow_source(
        vi550
    )

    if not source:
        return {
            "written":
                False,

            "reason":
                "vi550_shadow_missing",
        }

    before = sha256(
        source
    )

    data = json.loads(
        source.read_text(
            encoding="utf-8"
        )
    )

    if isinstance(
        data,
        dict
    ):
        shadow = copy.deepcopy(
            data
        )

    else:
        shadow = {
            "source_plan":
                data
        }

    shadow[
        "vi600_shadow"
    ] = payload

    SHADOW.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    SHADOW.write_text(
        json.dumps(
            shadow,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return {
        "written":
            True,

        "source":
            str(source),

        "source_sha256":
            before,

        "source_preserved":
            sha256(source)
            == before,

        "path":
            str(SHADOW),
    }


def evaluate():
    vi330 = load_gate(
        VI330,
        required=True
    )

    vi420 = load_gate(
        VI420,
        required=True
    )

    vi500 = load_gate(
        VI500,
        required=True
    )

    vi550 = load_gate(
        VI550,
        required=True
    )

    short_id = str(
        vi550.get(
            "short_id"
        )
        or _sap_resolve_short_id()
    )

    current_map = by_scene(
        vi500.get(
            "current_media"
        )
        or []
    )

    traces = {
        int(scene):
            items
        for scene, items
        in (
            vi550.get(
                "local_traces"
            )
            or {}
        ).items()
    }

    budget = {
        "used":
            0
    }

    provenance_recovered = {}

    provenance_attempts = {}

    provenance_downloads = 0

    # Priority follows VI550.
    for queue_item in (
        vi550.get(
            "next_queue"
        )
        or []
    ):
        if (
            provenance_downloads
            >= MAX_PROVENANCE_ATTEMPTS
        ):
            break

        scene = int(
            queue_item["scene"]
        )

        current = current_map.get(
            scene,
            {}
        )

        if not current.get(
            "sha256"
        ):
            continue

        scene_traces = traces.get(
            scene,
            []
        )

        urls = trace_source_urls(
            current,
            scene_traces
        )

        if not urls:
            continue

        provenance_downloads += 1

        result = verify_exact_source(
            scene,
            current,
            scene_traces,
            budget
        )

        provenance_attempts[
            scene
        ] = result

        if result[
            "verified"
        ]:
            provenance_recovered[
                scene
            ] = result

    cache = load_cache()

    cache_stats = {
        "CACHE": 0,
        "NETWORK": 0,
        "ERROR": 0,
    }

    policies = build_policies()

    search_results = {}

    staged = {}

    used_candidate_keys = set()

    production = production_hashes(
        current_map
    )

    for group_name, policy in (
        policies.items()
    ):
        unresolved_scenes = [
            scene
            for scene in policy[
                "scenes"
            ]
            if scene
            not in provenance_recovered
        ]

        if not unresolved_scenes:
            continue

        evaluated = search_group(
            policy,
            cache,
            cache_stats
        )

        search_results[
            group_name
        ] = {
            "scenes":
                unresolved_scenes,

            "queries":
                policy[
                    "queries"
                ],

            "candidate_count":
                len(
                    evaluated
                ),

            "approved_count":
                sum(
                    item[
                        "decision"
                    ]
                    == "LICENSED_TRUE_CANDIDATE"
                    for item in evaluated
                ),

            "top_candidates":
                evaluated[:8],
        }

        approved = [
            item
            for item in evaluated
            if item[
                "decision"
            ]
            == "LICENSED_TRUE_CANDIDATE"
        ]

        for scene in unresolved_scenes:
            staged_result = None

            for candidate in approved[:6]:
                key = (
                    candidate.get(
                        "key"
                    )
                    or candidate.get(
                        "direct_url"
                    )
                    or candidate.get(
                        "title"
                    )
                )

                if key in used_candidate_keys:
                    continue

                # Do not waste network on known oversized files.
                declared = int(
                    candidate.get(
                        "declared_bytes"
                    )
                    or 0
                )

                max_size = (
                    MAX_VIDEO_DOWNLOAD
                    if candidate[
                        "family"
                    ]
                    == "VIDEO"
                    else
                    MAX_IMAGE_DOWNLOAD
                )

                if (
                    declared
                    and declared
                    > max_size
                ):
                    continue

                attempt = stage_candidate(
                    scene,
                    candidate,
                    budget,
                    production
                )

                if attempt.get(
                    "staged"
                ):
                    staged_result = (
                        attempt
                    )

                    used_candidate_keys.add(
                        key
                    )

                    break

            if staged_result:
                staged[
                    scene
                ] = staged_result

    save_cache(
        cache
    )

    # Scene 4: verified real case source already exists.
    scene4_case_source = None

    candidate330 = (
        vi330.get(
            "candidate"
        )
        or {}
    )

    inherited330 = (
        vi330.get(
            "inherited_truth"
        )
        or {}
    )

    if (
        candidate330.get(
            "normalized_truth_score"
        )
        == 100
        and inherited330.get(
            "direct_case_truth"
        )
        and inherited330.get(
            "scene_role"
        )
    ):
        scene4_case_source = {
            "title":
                candidate330.get(
                    "title"
                ),

            "sandbox_path":
                candidate330.get(
                    "sandbox_path"
                ),

            "sha256":
                candidate330.get(
                    "sha256"
                ),

            "license":
                candidate330.get(
                    "license"
                ),

            "status":
                "VERIFIED_CASE_VIDEO_SOURCE",

            "usage":
                "FUTURE_FRAME_OR_INSERT_ONLY",

            "ffmpeg_executed":
                False,
        }

    decisions = []

    unresolved_next = []

    for scene in range(
        1,
        13
    ):
        recovered = (
            scene in provenance_recovered
        )

        replacement = staged.get(
            scene
        )

        if scene == 2:
            action = (
                "KEEP_CURRENT_VERIFIED"
            )

        elif scene == 9:
            action = (
                "VERIFIED_SHADOW_OBJECT_READY"
            )

        elif recovered:
            action = (
                "KEEP_CURRENT_PROVENANCE_RECOVERED"
            )

        elif scene == 1:
            if replacement:
                action = (
                    "LICENSED_BASE_SHADOW_READY"
                )

            else:
                action = (
                    "HYBRID_INSERT_BASE_PROVENANCE_PENDING"
                )

        elif scene == 4:
            if scene4_case_source:
                action = (
                    "FACTUAL_CASE_SOURCE_AVAILABLE_FRAME_REQUIRED"
                )

            else:
                action = (
                    "FACTUAL_PROVENANCE_UNRESOLVED"
                )

        elif scene == 7:
            if replacement:
                action = (
                    "LICENSED_VIDEO_SHADOW_READY"
                )

            else:
                action = (
                    "KEEP_VISUAL_PROVENANCE_PENDING"
                )

        elif scene in {
            5,
            6,
        }:
            if replacement:
                action = (
                    "ANONYMOUS_REENACTMENT_SHADOW_READY"
                )

            else:
                action = (
                    "LICENSED_ANONYMOUS_HUMAN_PENDING"
                )

        elif scene == 10:
            if replacement:
                action = (
                    "ROLE_REPAIRED_SHADOW_READY"
                )

            else:
                action = (
                    "ROLE_REPAIRED_PROVENANCE_PENDING"
                )

        elif scene == 12:
            if replacement:
                action = (
                    "FACTUAL_DOCUMENT_SHADOW_READY"
                )

            else:
                action = (
                    "FACTUAL_DOCUMENT_UNRESOLVED"
                )

        elif replacement:
            action = (
                "LICENSED_BROLL_SHADOW_READY"
            )

        else:
            action = (
                "PROVENANCE_OR_LICENSE_PENDING"
            )

        decision = {
            "scene":
                scene,

            "provenance_recovered":
                recovered,

            "replacement_staged":
                bool(
                    replacement
                ),

            "action":
                action,
        }

        decisions.append(
            decision
        )

        if (
            "PENDING"
            in action
            or "UNRESOLVED"
            in action
            or "FRAME_REQUIRED"
            in action
        ):
            unresolved_next.append(
                decision
            )

    shadow_payload = {
        "version":
            VERSION,

        "provenance_recovered":
            {
                str(scene):
                    value
                for scene, value
                in provenance_recovered.items()
            },

        "staged_replacements":
            {
                str(scene):
                    value
                for scene, value
                in staged.items()
            },

        "scene_4_factual_source":
            scene4_case_source,

        "global_decisions":
            decisions,

        "production_media_mutated":
            False,

        "production_plan_mutated":
            False,

        "automatic_replace":
            False,

        "renderer_activation":
            False,

        "ffmpeg":
            False,

        "video_generated":
            False,
    }

    shadow = build_shadow(
        vi550,
        shadow_payload
    )


    warnings = []

    if scene4_case_source:
        warnings.append(
            "scene4_verified_video_source_requires_future_frame_or_insert"
        )

    if any(
        item["scene"] == 12
        for item in unresolved_next
    ):
        warnings.append(
            "scene12_factual_document_still_unresolved"
        )

    if budget[
        "used"
    ] >= (
        MAX_TOTAL_DOWNLOAD
        * .90
    ):
        warnings.append(
            "download_budget_near_limit"
        )

    blockers = []

    if not shadow.get(
        "written"
    ):
        blockers.append(
            "vi600_shadow_not_written"
        )

    action_counts = Counter(
        item["action"]
        for item in decisions
    )

    report = {
        "version":
            VERSION,

        "status":
            (
                "VI600_PROVENANCE_RECOVERY_LICENSED_REPLACEMENT_CERTIFIED"
                if not blockers
                else "HOLD"
            ),

        "short_id":
            short_id,

        "provenance_recovery_attempts":
            provenance_attempts,

        "provenance_recovered_scenes":
            sorted(
                provenance_recovered
            ),

        "staged_replacement_scenes":
            sorted(
                staged
            ),

        "staged_replacements":
            staged,

        "scene4_factual_source":
            scene4_case_source,

        "search_groups":
            search_results,

        "cache_stats":
            cache_stats,

        "download_budget": {
            "limit_bytes":
                MAX_TOTAL_DOWNLOAD,

            "used_bytes":
                budget[
                    "used"
                ],

            "remaining_bytes":
                (
                    MAX_TOTAL_DOWNLOAD
                    - budget[
                        "used"
                    ]
                ),
        },

        "action_counts":
            dict(
                action_counts
            ),

        "decisions":
            decisions,

        "next_queue":
            unresolved_next,

        "shadow_plan":
            shadow,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "network_executed":
            (
                cache_stats.get(
                    "NETWORK",
                    0
                ) > 0
                or provenance_downloads > 0
            ),

        "controlled_download_executed":
            bool(
                staged
                or provenance_attempts
            ),

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
        " VI600 PROVENANCE RECOVERY + LICENSED ENGINE"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "PROVENANCE RECOVERED:",
        r[
            "provenance_recovered_scenes"
        ]
    )

    print(
        "STAGED REPLACEMENTS:",
        r[
            "staged_replacement_scenes"
        ]
    )

    print(
        "CACHE STATS:",
        r[
            "cache_stats"
        ]
    )

    print(
        "DOWNLOAD BUDGET:",
        r[
            "download_budget"
        ]
    )

    print()
    print(
        "===== PROVENANCE RECOVERY ====="
    )

    for scene, item in (
        r[
            "provenance_recovery_attempts"
        ].items()
    ):
        print(
            "SCENE",
            scene,
            "| VERIFIED=",
            item[
                "verified"
            ],
        )

        for attempt in (
            item[
                "attempts"
            ]
        ):
            print(
                "  -",
                attempt[
                    "status"
                ],
                "|",
                attempt[
                    "url"
                ],
            )

    print()
    print(
        "===== STAGED LICENSED MEDIA ====="
    )

    for scene, item in (
        r[
            "staged_replacements"
        ].items()
    ):
        print()
        print(
            "SCENE:",
            scene
        )

        print(
            " TITLE:",
            item[
                "title"
            ]
        )

        print(
            " PROVIDER:",
            item[
                "provider"
            ]
        )

        print(
            " FAMILY:",
            item[
                "family"
            ]
        )

        print(
            " DIMENSIONS:",
            item[
                "dimensions"
            ]
        )

        print(
            " BYTES:",
            item[
                "bytes"
            ]
        )

        print(
            " LICENSE:",
            item[
                "license"
            ]
        )

        print(
            " SCORE:",
            item[
                "score"
            ]
        )

        print(
            " SHA256:",
            item[
                "sha256"
            ]
        )

        if item.get(
            "anonymity_hits"
        ):
            print(
                " ANONYMITY:",
                item[
                    "anonymity_hits"
                ]
            )

    print()
    print(
        "===== SEARCH GROUPS ====="
    )

    for name, group in (
        r[
            "search_groups"
        ].items()
    ):
        print(
            name,
            "| scenes=",
            group[
                "scenes"
            ],
            "| candidates=",
            group[
                "candidate_count"
            ],
            "| approved=",
            group[
                "approved_count"
            ],
        )

        print(
            "   QUERIES:",
            group[
                "queries"
            ]
        )

        for item in (
            group[
                "top_candidates"
            ][:3]
        ):
            print(
                "   -",
                item[
                    "decision"
                ],
                "|",
                item[
                    "title"
                ],
                "| score=",
                item[
                    "score"
                ],
                "| role=",
                item[
                    "role_hits"
                ],
                "| license=",
                item[
                    "license"
                ],
            )

    print()
    print(
        "===== GLOBAL DECISIONS ====="
    )

    for item in (
        r["decisions"]
    ):
        print(
            "SCENE",
            item[
                "scene"
            ],
            "| recovered=",
            item[
                "provenance_recovered"
            ],
            "| staged=",
            item[
                "replacement_staged"
            ],
            "|",
            item[
                "action"
            ],
        )

    print()
    print(
        "===== NEXT QUEUE ====="
    )

    for item in (
        r[
            "next_queue"
        ]
    ):
        print(
            "SCENE",
            item["scene"],
            "|",
            item["action"],
        )

    print()
    print(
        "SCENE 4 FACTUAL SOURCE:",
        r[
            "scene4_factual_source"
        ]
    )

    print(
        "SHADOW PLAN:",
        r[
            "shadow_plan"
        ]
    )

    print(
        "BLOCKERS:",
        r[
            "blockers"
        ]
    )

    print(
        "WARNINGS:",
        r[
            "warnings"
        ]
    )

    print()
    print(
        "NETWORK EXECUTED:",
        r[
            "network_executed"
        ]
    )

    print(
        "CONTROLLED DOWNLOAD:",
        r[
            "controlled_download_executed"
        ]
    )

    print(
        "PRODUCTION MEDIA MUTATED:",
        r[
            "production_media_mutated"
        ]
    )

    print(
        "PRODUCTION PLAN MUTATED:",
        r[
            "production_plan_mutated"
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
