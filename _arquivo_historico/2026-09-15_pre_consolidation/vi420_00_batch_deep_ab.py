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

import requests


VERSION = "420.00"

BASE = Path.home() / "ShortAutoPro"
LOG = BASE / "logs/producao"

VI400 = (
    LOG /
    "vi400_00_speed_quality_accelerator_latest.json"
)

CACHE = (
    BASE /
    "temp/vi400_cache/metadata_cache.json"
)

OUT = (
    LOG /
    "vi420_00_batch_deep_ab_latest.json"
)

SANDBOX = (
    BASE /
    "temp/vi420_scene9_ab"
)

SHADOW = (
    BASE /
    "temp/vi420_shadow/"
    "motion_plan_2026-09-01_1433_vi420_shadow.json"
)

COMMONS = (
    "https://commons.wikimedia.org/w/api.php"
)

HEADERS = {
    "User-Agent":
        "ShortAutoPro/420.00 "
        "(strict-object controlled AB)"
}

CACHE_TTL = 86400
MAX_RESULTS = 18
MAX_DOWNLOAD = 30 * 1024 * 1024

TARGET_RATIO = 9 / 16


QUERIES = [
    "prescription medicine bottles",
    "prescription medication bottles",
    "prescription pill bottles",
    "medication bottles pharmacy",
]


OBJECT_TERMS = {
    "bottle",
    "bottles",
    "pill bottle",
    "pill bottles",
    "medicine bottle",
    "medicine bottles",
    "medication bottle",
    "medication bottles",
    "prescription bottle",
    "prescription bottles",
    "vial",
    "vials",
    "pills",
    "capsules",
    "tablets",
}


MEDICINE_TERMS = {
    "prescription",
    "medicine",
    "medication",
    "pharmacy",
    "pharmaceutical",
    "drug",
    "pills",
    "capsules",
    "tablets",
}


DOCUMENT_TERMS = {
    "prescription form",
    "prescription paper",
    "prescription document",
    "document",
    "paper form",
    "medical form",
    "receipt",
    "letter",
    "scanned page",
    "scan of",
}


NEGATIVE_TERMS = {
    "advertisement",
    "poster",
    "logo",
    "screenshot",
    "book cover",
    "album cover",
    "drawing",
    "diagram",
}


def load_gate(path):
    if not path.exists():
        raise RuntimeError(
            f"missing:{path.name}"
        )

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

    # Commons namespace is metadata,
    # never visual evidence.
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
        cache
        .get("entries", {})
        .get(key)
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
                    retry = int(
                        retry
                    )
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
                            + str(exc)[:180]
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


def phrase_hits(
    text,
    terms
):
    low = normalize(text)

    return sorted({
        term
        for term in terms
        if term in low
    })


def license_score(text):
    low = normalize(text)

    if any(
        x in low
        for x in (
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
        return 95

    if pixels >= 1_000_000:
        return 90

    if pixels >= 500_000:
        return 75

    if pixels >= 200_000:
        return 60

    return 40


def geometry(
    width,
    height
):
    width = int(
        width or 0
    )

    height = int(
        height or 0
    )

    if (
        width <= 0
        or height <= 0
    ):
        return {
            "aspect_ratio":
                None,

            "aspect_score":
                0,

            "cover_scale":
                None,

            "retained_fraction":
                None,
        }

    ratio = (
        width / height
    )

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

    cover_scale = max(
        1080 / width,
        1920 / height
    )

    scaled_area = (
        width
        * cover_scale
        * height
        * cover_scale
    )

    retained = min(
        1.0,
        (
            1080 * 1920
        )
        / scaled_area
    )

    return {
        "aspect_ratio":
            round(
                ratio,
                4
            ),

        "aspect_score":
            round(
                aspect_score,
                2
            ),

        "cover_scale":
            round(
                cover_scale,
                2
            ),

        "retained_fraction":
            round(
                retained,
                3
            ),
    }


def strict_object_truth(
    evidence
):
    objects = phrase_hits(
        evidence,
        OBJECT_TERMS
    )

    medicine = phrase_hits(
        evidence,
        MEDICINE_TERMS
    )

    documents = phrase_hits(
        evidence,
        DOCUMENT_TERMS
    )

    negatives = phrase_hits(
        evidence,
        NEGATIVE_TERMS
    )

    # "prescription" sozinho NÃO prova
    # que estamos vendo um frasco.
    physical_object = bool(
        objects
    )

    medicine_context = bool(
        medicine
    )

    document_only = (
        bool(
            documents
        )
        and not physical_object
    )

    strong_truth = (
        physical_object
        and medicine_context
        and not document_only
        and not negatives
    )

    return {
        "physical_object":
            physical_object,

        "medicine_context":
            medicine_context,

        "object_hits":
            objects,

        "medicine_hits":
            medicine,

        "document_hits":
            documents,

        "negative_hits":
            negatives,

        "document_only":
            document_only,

        "strong_truth":
            strong_truth,
    }


def commons_search(
    query,
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

    # Same key used by VI400.
    key = (
        "commons|IMAGE|"
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

    out = []

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

        if (
            not mime.startswith(
                "image/"
            )
            and mediatype
            != "bitmap"
        ):
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

        description = mv(
            "ImageDescription"
        )

        categories = mv(
            "Categories"
        )

        object_name = mv(
            "ObjectName"
        )

        # Query deliberately excluded.
        evidence = " ".join([
            title,
            description,
            categories,
            object_name,
        ])

        try:
            width = int(
                info.get(
                    "width"
                )
                or 0
            )

            height = int(
                info.get(
                    "height"
                )
                or 0
            )

            size = int(
                info.get(
                    "size"
                )
                or 0
            )

        except Exception:
            width = 0
            height = 0
            size = 0

        out.append({
            "provider":
                "WIKIMEDIA_COMMONS",

            "title":
                title,

            "url":
                info.get("url"),

            "mime":
                mime,

            "family":
                "IMAGE",

            "width":
                width,

            "height":
                height,

            "declared_bytes":
                size,

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

            "evidence":
                evidence,
        })

    return out, source


def evaluate_candidate(
    candidate
):
    truth = strict_object_truth(
        candidate.get(
            "evidence"
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

    gates = {
        "image_family":
            candidate.get(
                "family"
            )
            == "IMAGE",

        "physical_medicine_object":
            truth[
                "strong_truth"
            ],

        "not_document_only":
            not truth[
                "document_only"
            ],

        "negative_absent":
            not bool(
                truth[
                    "negative_hits"
                ]
            ),

        "license":
            lic >= 80,

        "technical":
            tech >= 60,
    }

    score = 0

    if truth[
        "strong_truth"
    ]:
        score += 45

    if lic >= 80:
        score += 15

    score += (
        tech * .20
    )

    score += (
        geo[
            "aspect_score"
        ] * .10
    )

    if (
        not truth[
            "document_only"
        ]
        and not truth[
            "negative_hits"
        ]
    ):
        score += 10

    score = round(
        max(
            0,
            min(
                100,
                score
            )
        ),
        2
    )

    return {
        **candidate,

        "truth":
            truth,

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
                "STRICT_OBJECT_CANDIDATE"
                if all(
                    gates.values()
                )
                else "REJECT"
            ),
    }


def commons_exact(
    title,
    cache
):
    params = {
        "action":
            "query",

        "titles":
            title,

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
        "vi420-title|"
        + title.lower()
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

    if not pages:
        return None, source

    page = pages[0]

    infos = (
        page.get(
            "imageinfo"
        )
        or []
    )

    if not infos:
        return None, source

    info = infos[0]

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
            return str(
                value.get(
                    "value"
                )
                or ""
            )

        return str(
            value or ""
        )

    title_real = str(
        page.get("title")
        or title
    )

    evidence = " ".join([
        title_real,
        mv(
            "ImageDescription"
        ),
        mv(
            "Categories"
        ),
        mv(
            "ObjectName"
        ),
    ])

    return {
        "provider":
            "WIKIMEDIA_COMMONS",

        "title":
            title_real,

        "url":
            info.get("url"),

        "mime":
            normalize(
                info.get(
                    "mime"
                )
            ),

        "family":
            "IMAGE",

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

        "evidence":
            evidence,
    }, source


def controlled_download(
    url,
    destination
):
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
    ) as r:
        r.raise_for_status()

        content_type = normalize(
            r.headers.get(
                "Content-Type"
            )
        )

        total = 0

        with open(
            part,
            "wb"
        ) as f:
            for chunk in (
                r.iter_content(
                    256 * 1024
                )
            ):
                if not chunk:
                    continue

                total += len(chunk)

                if total > MAX_DOWNLOAD:
                    raise RuntimeError(
                        "download_limit_exceeded"
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

    return {
        "bytes":
            total,

        "content_type":
            content_type,
    }


def jpeg_size(path):
    try:
        with open(
            path,
            "rb"
        ) as f:
            if (
                f.read(2)
                != b"\xff\xd8"
            ):
                return None

            while True:
                b = f.read(1)

                if not b:
                    return None

                if b != b"\xff":
                    continue

                while b == b"\xff":
                    b = f.read(1)

                marker = b[0]

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

                    h, w = struct.unpack(
                        ">HH",
                        data[1:5]
                    )

                    return w, h

                f.seek(
                    length - 2,
                    1
                )

    except Exception:
        return None


def png_size(path):
    try:
        with open(
            path,
            "rb"
        ) as f:
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
        return jpeg_size(
            path
        )

    if ext == ".png":
        return png_size(
            path
        )

    return None


def find_scene9(
    short_id
):
    folder = (
        BASE /
        "imagens" /
        f"short_{short_id}"
    )

    matches = sorted(
        folder.glob(
            "scene_09.*"
        )
    )

    if not matches:
        raise RuntimeError(
            "scene_09_missing"
        )

    return matches[0]


def production_hashes(
    short_id
):
    folder = (
        BASE /
        "imagens" /
        f"short_{short_id}"
    )

    result = {}

    for path in sorted(
        folder.glob(
            "scene_*.*"
        )
    ):
        if not path.is_file():
            continue

        try:
            result[
                sha256(path)
            ] = str(path)

        except Exception:
            continue

    return result


def file_magic(
    path
):
    with open(
        path,
        "rb"
    ) as f:
        head = f.read(12)

    jpeg = (
        head[:2]
        == b"\xff\xd8"
    )

    png = (
        head[:8]
        == b"\x89PNG\r\n\x1a\n"
    )

    return {
        "jpeg":
            jpeg,

        "png":
            png,

        "first12":
            head.hex(),
    }


def build_shadow(
    vi400,
    scene9_payload
):
    source_path = (
        vi400
        .get(
            "scene1",
            {}
        )
        .get(
            "shadow_plan_path"
        )
    )

    if not source_path:
        return {
            "written":
                False,

            "reason":
                "vi400_shadow_missing",
        }

    source = Path(
        source_path
    )

    if not source.exists():
        return {
            "written":
                False,

            "reason":
                "vi400_shadow_not_found",
        }

    original_hash = sha256(
        source
    )

    data = json.loads(
        source.read_text(
            encoding="utf-8"
        )
    )

    shadow = copy.deepcopy(
        data
    )

    if not isinstance(
        shadow,
        dict
    ):
        shadow = {
            "source_plan":
                shadow
        }

    shadow[
        "vi420_shadow"
    ] = {
        "scene_9":
            scene9_payload,

        "renderer_activation":
            False,

        "production_media_mutated":
            False,

        "automatic_replace":
            False,

        "ffmpeg":
            False,

        "video_generated":
            False,
    }

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
            str(
                source
            ),

        "source_sha256":
            original_hash,

        "path":
            str(
                SHADOW
            ),

        "source_preserved":
            sha256(
                source
            )
            == original_hash,
    }


def evaluate():
    vi400 = load_gate(
        VI400
    )

    short_id = str(
        vi400.get(
            "short_id"
        )
        or _sap_resolve_short_id()
    )

    cache = load_cache()

    cache_stats = {
        "CACHE": 0,
        "NETWORK": 0,
        "ERROR": 0,
    }

    raw = []

    for query in QUERIES:
        found, source = (
            commons_search(
                query,
                cache
            )
        )

        raw.extend(
            found
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

    # URL/title dedupe.
    dedup = {}

    for item in raw:
        key = (
            item.get("url")
            or item.get(
                "title"
            )
        )

        dedup[key] = item

    raw = list(
        dedup.values()
    )

    evaluated = [
        evaluate_candidate(
            item
        )
        for item in raw
    ]

    evaluated.sort(
        key=lambda x: (
            x["decision"]
            == "STRICT_OBJECT_CANDIDATE",
            x["score"],
            x["technical_score"],
        ),
        reverse=True
    )

    strict = [
        item
        for item in evaluated
        if item[
            "decision"
        ]
        == "STRICT_OBJECT_CANDIDATE"
    ]

    # Explicitly check what happened to
    # the VI400 winner.
    vi400_winner_title = None

    for item in (
        vi400.get(
            "scene_search_results"
        )
        or []
    ):
        if int(
            item.get(
                "scene",
                -1
            )
        ) == 9:
            winner = (
                item.get(
                    "winner"
                )
                or {}
            )

            vi400_winner_title = (
                winner.get(
                    "title"
                )
            )
            break

    vi400_winner_recheck = None

    if vi400_winner_title:
        for item in evaluated:
            if (
                item.get("title")
                == vi400_winner_title
            ):
                vi400_winner_recheck = (
                    item
                )
                break

    best = (
        strict[0]
        if strict
        else None
    )

    deep = None

    if best:
        exact, source = (
            commons_exact(
                best["title"],
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

        if exact:
            deep = evaluate_candidate(
                exact
            )

            if (
                deep["decision"]
                != "STRICT_OBJECT_CANDIDATE"
            ):
                best = None
                deep = None

    save_cache(
        cache
    )

    current = find_scene9(
        short_id
    )

    current_dims = image_size(
        current
    )

    if current_dims:
        cw, ch = current_dims
    else:
        cw = 0
        ch = 0

    current_pixels = (
        cw * ch
    )

    current_geo = geometry(
        cw,
        ch
    )

    production = (
        production_hashes(
            short_id
        )
    )

    controlled_download = False

    candidate_payload = None

    decision = "KEEP_CURRENT"

    blockers = []

    warnings = []

    if deep:
        SANDBOX.mkdir(
            parents=True,
            exist_ok=True
        )

        ext = (
            ".png"
            if "png"
            in deep[
                "mime"
            ]
            else ".jpg"
        )

        destination = (
            SANDBOX /
            (
                "scene_09_candidate"
                + ext
            )
        )

        dl = controlled_download_file = (
            controlled_download_media(
                deep["url"],
                destination
            )
        )

        controlled_download = True

        actual_hash = sha256(
            destination
        )

        magic = file_magic(
            destination
        )

        actual_dims = image_size(
            destination
        )

        if actual_dims:
            aw, ah = actual_dims

        else:
            aw = deep["width"]
            ah = deep["height"]

        actual_pixels = (
            aw * ah
        )

        candidate_geo = geometry(
            aw,
            ah
        )

        duplicate_path = (
            production.get(
                actual_hash
            )
        )

        unique = (
            duplicate_path
            is None
        )

        size_consistent = (
            deep[
                "declared_bytes"
            ] <= 0
            or abs(
                dl["bytes"]
                - deep[
                    "declared_bytes"
                ]
            )
            <= max(
                4096,
                int(
                    deep[
                        "declared_bytes"
                    ]
                    * .01
                )
            )
        )

        mime_magic = (
            (
                "jpeg"
                in deep["mime"]
                and magic["jpeg"]
            )
            or (
                "png"
                in deep["mime"]
                and magic["png"]
            )
        )

        if current_pixels:
            pixel_ratio = (
                actual_pixels
                / current_pixels
            )
        else:
            pixel_ratio = None

        relative_technical_ok = (
            not current_pixels
            or actual_pixels
            >= current_pixels * .50
        )

        final_gates = {
            "strict_object_truth":
                deep[
                    "truth"
                ][
                    "strong_truth"
                ],

            "metadata_family":
                deep[
                    "family"
                ]
                == "IMAGE",

            "license":
                deep[
                    "license_score"
                ] >= 80,

            "real_file_magic":
                mime_magic,

            "size_consistent":
                size_consistent,

            "unique_production_hash":
                unique,

            "relative_technical":
                relative_technical_ok,

            "actual_dimensions":
                aw > 0
                and ah > 0,
        }

        ready = all(
            final_gates.values()
        )

        if ready:
            decision = (
                "READY_FOR_SHADOW_OBJECT_AB"
            )

        else:
            decision = (
                "KEEP_CURRENT"
            )

            blockers.extend(
                key
                for key, value
                in final_gates.items()
                if not value
            )

        if pixel_ratio is not None:
            if pixel_ratio < 1:
                warnings.append(
                    "candidate_lower_pixel_count_than_current"
                )

        if (
            candidate_geo[
                "aspect_score"
            ]
            < current_geo[
                "aspect_score"
            ]
        ):
            warnings.append(
                "candidate_lower_vertical_fit_than_current"
            )

        candidate_payload = {
            "title":
                deep["title"],

            "url":
                deep["url"],

            "sandbox_path":
                str(
                    destination
                ),

            "sha256":
                actual_hash,

            "mime":
                deep["mime"],

            "width":
                aw,

            "height":
                ah,

            "pixels":
                actual_pixels,

            "bytes":
                dl["bytes"],

            "license":
                deep[
                    "license"
                ],

            "license_score":
                deep[
                    "license_score"
                ],

            "truth":
                deep[
                    "truth"
                ],

            "geometry":
                candidate_geo,

            "pixel_ratio_vs_current":
                (
                    round(
                        pixel_ratio,
                        4
                    )
                    if pixel_ratio
                    is not None
                    else None
                ),

            "duplicate_production_path":
                duplicate_path,

            "final_gates":
                final_gates,

            "automatic_replace":
                False,
        }

    scene9_shadow = {
        "strategy":
            (
                "SHADOW_OBJECT_CANDIDATE"
                if decision
                == "READY_FOR_SHADOW_OBJECT_AB"
                else
                "KEEP_CURRENT"
            ),

        "current_path":
            str(
                current
            ),

        "current_sha256":
            sha256(
                current
            ),

        "candidate":
            candidate_payload,

        "renderer_activation":
            False,
    }

    shadow = build_shadow(
        vi400,
        scene9_shadow
    )

    global_plan = []

    for scene in range(
        1,
        13
    ):
        if scene == 1:
            action = (
                "HYBRID_ARCHIVAL_INSERT_ONLY"
            )

        elif scene == 2:
            action = (
                "KEEP_CURRENT_VERIFIED"
            )

        elif scene in {
            5,
            6,
            10,
        }:
            action = (
                "IDENTITY_QUARANTINE"
            )

        elif scene == 7:
            action = (
                "KEEP_CURRENT_SEARCH_EXHAUSTED"
            )

        elif scene == 9:
            action = decision

        else:
            action = (
                "KEEP_CURRENT"
            )

        global_plan.append({
            "scene":
                scene,

            "action":
                action,
        })

    if (
        vi400_winner_recheck
        and vi400_winner_recheck[
            "decision"
        ]
        == "REJECT"
    ):
        warnings.append(
            "vi400_scene9_winner_invalidated_by_strict_object_gate"
        )

    if not strict:
        warnings.append(
            "no_strict_scene9_object_candidate_found"
        )

    report = {
        "version":
            VERSION,

        "status":
            "VI420_BATCH_DEEP_AB_CERTIFIED",

        "short_id":
            short_id,

        "speed": {
            "queries":
                len(
                    QUERIES
                ),

            "raw_after_dedup":
                len(
                    raw
                ),

            "strict_candidates":
                len(
                    strict
                ),

            "cache_stats":
                cache_stats,

            "network_requests_saved_by_cache":
                cache_stats.get(
                    "CACHE",
                    0
                ),
        },

        "scene9": {
            "vi400_winner":
                vi400_winner_title,

            "vi400_winner_recheck":
                (
                    {
                        "decision":
                            vi400_winner_recheck[
                                "decision"
                            ],

                        "truth":
                            vi400_winner_recheck[
                                "truth"
                            ],

                        "score":
                            vi400_winner_recheck[
                                "score"
                            ],
                    }
                    if vi400_winner_recheck
                    else None
                ),

            "current": {
                "path":
                    str(
                        current
                    ),

                "sha256":
                    sha256(
                        current
                    ),

                "width":
                    cw,

                "height":
                    ch,

                "pixels":
                    current_pixels,

                "geometry":
                    current_geo,
            },

            "top_candidates": [
                {
                    "title":
                        x["title"],

                    "decision":
                        x[
                            "decision"
                        ],

                    "score":
                        x["score"],

                    "width":
                        x["width"],

                    "height":
                        x["height"],

                    "truth":
                        x["truth"],

                    "license":
                        x["license"],
                }
                for x in evaluated[:8]
            ],

            "candidate":
                candidate_payload,

            "decision":
                decision,
        },

        "shadow_plan":
            shadow,

        "global_plan":
            global_plan,

        "blockers":
            sorted(
                set(
                    blockers
                )
            ),

        "warnings":
            sorted(
                set(
                    warnings
                )
            ),

        "network_executed":
            cache_stats.get(
                "NETWORK",
                0
            ) > 0,

        "controlled_download_executed":
            controlled_download,

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


# Separate name prevents collision with
# the controlled_download boolean.
def controlled_download_media(
    url,
    destination
):
    return controlled_download(
        url,
        destination
    )


if __name__ == "__main__":
    r = evaluate()

    print()
    print(
        "=============================================="
    )
    print(
        " VI420 BATCH DEEP A/B + OBJECT TRUTH"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print()
    print(
        "CACHE STATS:",
        r["speed"][
            "cache_stats"
        ]
    )

    print(
        "NETWORK SAVED:",
        r["speed"][
            "network_requests_saved_by_cache"
        ]
    )

    print(
        "RAW DEDUP:",
        r["speed"][
            "raw_after_dedup"
        ]
    )

    print(
        "STRICT CANDIDATES:",
        r["speed"][
            "strict_candidates"
        ]
    )

    s = r["scene9"]

    print()
    print(
        "===== SCENE 9 ====="
    )

    print(
        "VI400 WINNER:",
        s[
            "vi400_winner"
        ]
    )

    print(
        "VI400 WINNER RECHECK:",
        s[
            "vi400_winner_recheck"
        ]
    )

    print()
    print(
        "CURRENT:",
        s["current"]
    )

    print()
    print(
        "TOP STRICT TOURNAMENT:"
    )

    for x in s[
        "top_candidates"
    ]:
        print(
            "-",
            x["decision"],
            "|",
            x["title"],
            "| score=",
            x["score"],
            "| size=",
            str(
                x["width"]
            )
            + "x"
            + str(
                x["height"]
            ),
            "| object=",
            x["truth"][
                "object_hits"
            ],
            "| document=",
            x["truth"][
                "document_hits"
            ],
            "| license=",
            x["license"],
        )

    print()
    print(
        "FINAL CANDIDATE:",
        (
            s["candidate"][
                "title"
            ]
            if s["candidate"]
            else None
        )
    )

    if s[
        "candidate"
    ]:
        print(
            "CANDIDATE DETAILS:",
            s["candidate"]
        )

    print(
        "SCENE 9 DECISION:",
        s["decision"]
    )

    print()
    print(
        "===== GLOBAL PLAN ====="
    )

    for x in r[
        "global_plan"
    ]:
        print(
            "SCENE",
            x["scene"],
            "|",
            x["action"],
        )

    print()
    print(
        "SHADOW PLAN:",
        r[
            "shadow_plan"
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
        "NETWORK EXECUTED:",
        r["network_executed"]
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
