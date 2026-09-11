#!/usr/bin/env python3

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


VERSION = "650.00"

BASE = Path.home() / "ShortAutoPro"
LOG = BASE / "logs/producao"

VI330 = LOG / "vi330_00_controlled_real_ab_latest.json"
VI420 = LOG / "vi420_00_batch_deep_ab_latest.json"
VI550 = LOG / "vi550_00_role_provenance_repair_latest.json"
VI600 = LOG / "vi600_00_provenance_replacement_engine_latest.json"

OUT = (
    LOG /
    "vi650_00_shadow_portfolio_optimizer_latest.json"
)

CACHE = (
    BASE /
    "temp/vi650_cache/exact_metadata.json"
)

SANDBOX = (
    BASE /
    "temp/vi650_portfolio"
)

SHADOW = (
    BASE /
    "temp/vi650_shadow/"
    "motion_plan_2026-09-01_1433_vi650_shadow.json"
)


COMMONS = (
    "https://commons.wikimedia.org/w/api.php"
)

HEADERS = {
    "User-Agent":
        "ShortAutoPro/650.00 "
        "(shadow portfolio optimizer)"
}


THUMB_WIDTH = 1600

CACHE_TTL = 86400

MAX_TOTAL_DOWNLOAD = (
    20 * 1024 * 1024
)

MAX_SINGLE_DOWNLOAD = (
    6 * 1024 * 1024
)


TARGET_RATIO = 9 / 16


RASTER_MIMES = {
    "image/jpeg",
    "image/png",
}


DOCUMENT_EXT = {
    ".pdf",
    ".djvu",
    ".svg",
    ".tif",
    ".tiff",
}


ELEVATOR_FALSE_CONTEXT = {
    "grain elevator",
    "grain trade",
    "grain storage",
    "agricultural",
    "agriculture",
    "silo",
    "wheat",
    "corn",
    "vaporwave",
    "world trade center",
    "wtc",
    "twin towers",
}


VIDEO_FALSE_CONTEXT = {
    "vaporwave",
    "world trade center",
    "wtc",
    "twin towers",
    "gameplay",
    "reaction",
    "review",
    "trailer",
    "livestream",
    "live stream",
}


HUMAN_TERMS = {
    "person",
    "woman",
    "man",
    "human",
    "figure",
    "girl",
    "boy",
}


ANONYMITY_TERMS = {
    "silhouette",
    "back view",
    "rear view",
    "from behind",
    "anonymous",
    "faceless",
    "face hidden",
    "unrecognizable",
    "unrecognisable",
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


def cached_exact_commons(
    title,
    cache
):
    now = time.time()

    key = (
        "exact|1600|"
        + str(title).lower()
    )

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
                    "data"
                ),
                "CACHE"
            )

    params = {
        "action":
            "query",

        "titles":
            title,

        "prop":
            "imageinfo",

        "iiprop":
            "url|size|mime|mediatype|extmetadata",

        "iiurlwidth":
            THUMB_WIDTH,

        "format":
            "json",

        "formatversion":
            2,
    }

    wait = 4

    for attempt in range(3):
        try:
            r = requests.get(
                COMMONS,
                params=params,
                headers=HEADERS,
                timeout=30
            )

            if r.status_code == 429:
                time.sleep(wait)

                wait = min(
                    wait * 2,
                    20
                )

                continue

            r.raise_for_status()

            raw = r.json()

            pages = (
                raw.get(
                    "query",
                    {}
                ).get(
                    "pages",
                    []
                )
            )

            if not pages:
                return None, "NETWORK"

            infos = (
                pages[0].get(
                    "imageinfo"
                )
                or []
            )

            if not infos:
                return None, "NETWORK"

            info = infos[0]

            data = {
                "title":
                    pages[0].get(
                        "title"
                    )
                    or title,

                "mime":
                    normalize(
                        info.get(
                            "mime"
                        )
                    ),

                "original_url":
                    info.get(
                        "url"
                    ),

                "thumb_url":
                    info.get(
                        "thumburl"
                    ),

                "thumb_width":
                    int(
                        info.get(
                            "thumbwidth"
                        )
                        or 0
                    ),

                "thumb_height":
                    int(
                        info.get(
                            "thumbheight"
                        )
                        or 0
                    ),

                "original_width":
                    int(
                        info.get(
                            "width"
                        )
                        or 0
                    ),

                "original_height":
                    int(
                        info.get(
                            "height"
                        )
                        or 0
                    ),

                "original_bytes":
                    int(
                        info.get(
                            "size"
                        )
                        or 0
                    ),
            }

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

        except Exception:
            if attempt == 2:
                return None, "ERROR"

            time.sleep(wait)

            wait = min(
                wait * 2,
                20
            )

    return None, "ERROR"


def controlled_download(
    url,
    destination,
    budget
):
    if not url:
        raise RuntimeError(
            "missing_download_url"
        )

    remaining = (
        MAX_TOTAL_DOWNLOAD
        - budget["used"]
    )

    allowed = min(
        remaining,
        MAX_SINGLE_DOWNLOAD
    )

    if allowed < 10_000:
        raise RuntimeError(
            "download_budget_exhausted"
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
    ) as r:
        r.raise_for_status()

        declared = (
            r.headers.get(
                "Content-Length"
            )
        )

        if declared:
            try:
                if int(declared) > allowed:
                    raise RuntimeError(
                        "declared_download_too_large"
                    )

            except ValueError:
                pass

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

                if total > allowed:
                    part.unlink(
                        missing_ok=True
                    )

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

    budget["used"] += total

    return total


def jpeg_size(path):
    try:
        with open(path, "rb") as f:
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

                    height, width = (
                        struct.unpack(
                            ">HH",
                            data[1:5]
                        )
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
    size = jpeg_size(
        path
    )

    if size:
        return size

    return png_size(
        path
    )


def image_magic(path):
    with open(path, "rb") as f:
        head = f.read(12)

    return {
        "jpeg":
            head[:2]
            == b"\xff\xd8",

        "png":
            head[:8]
            == b"\x89PNG\r\n\x1a\n",
    }


def geometry(width, height):
    width = int(width or 0)
    height = int(height or 0)

    if (
        width <= 0
        or height <= 0
    ):
        return {
            "pixels": 0,
            "aspect_score": 0,
            "cover_scale": None,
            "retained_fraction": 0,
        }

    pixels = (
        width * height
    )

    ratio = (
        width / height
    )

    aspect_error = abs(
        ratio
        - TARGET_RATIO
    )

    aspect_score = max(
        0,
        min(
            100,
            100
            - aspect_error * 150
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
        1,
        (
            1080 * 1920
        )
        / scaled_area
    )

    return {
        "pixels":
            pixels,

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


def candidate_text(candidate):
    return " ".join([
        str(
            candidate.get(
                "title"
            )
            or ""
        ),
        str(
            candidate.get(
                "evidence"
            )
            or ""
        ),
        " ".join(
            candidate.get(
                "role_hits"
            )
            or []
        ),
    ])


def real_raster_candidate(
    candidate
):
    mime = normalize(
        candidate.get(
            "mime"
        )
    )

    title = str(
        candidate.get(
            "title"
        )
        or ""
    )

    ext = (
        Path(
            title.replace(
                "File:",
                ""
            )
        ).suffix.lower()
    )

    if ext in DOCUMENT_EXT:
        return False

    return (
        mime in RASTER_MIMES
        or ext in {
            ".jpg",
            ".jpeg",
            ".png",
        }
    )


def hard_filter(
    scene,
    candidate
):
    text = candidate_text(
        candidate
    )

    low = normalize(
        text
    )

    reasons = []

    provider = str(
        candidate.get(
            "provider"
        )
        or ""
    )

    family = str(
        candidate.get(
            "family"
        )
        or ""
    ).upper()

    if scene in {
        1,
        5,
        6,
        8,
        10,
        11,
    }:
        if family != "IMAGE":
            reasons.append(
                "wrong_family"
            )

        if not real_raster_candidate(
            candidate
        ):
            reasons.append(
                "not_real_raster_image"
            )

    if scene == 1:
        if "elevator" not in low:
            reasons.append(
                "elevator_missing"
            )

        bad = term_hits(
            text,
            ELEVATOR_FALSE_CONTEXT
        )

        if bad:
            reasons.append(
                "elevator_polysemy_or_wrong_context"
            )

    elif scene == 8:
        if not any(
            term in low
            for term in (
                "hallway",
                "corridor",
            )
        ):
            reasons.append(
                "hallway_role_missing"
            )

    elif scene in {
        10,
        11,
    }:
        roof = any(
            term in low
            for term in (
                "roof",
                "rooftop",
            )
        )

        water = any(
            term in low
            for term in (
                "water tower",
                "water tank",
            )
        )

        if not roof:
            reasons.append(
                "rooftop_missing"
            )

        if not water:
            reasons.append(
                "water_structure_missing"
            )

    elif scene == 5:
        human = bool(
            term_hits(
                text,
                HUMAN_TERMS
            )
        )

        anonymous = bool(
            term_hits(
                text,
                ANONYMITY_TERMS
            )
        )

        elevator = (
            "elevator" in low
            or "lift" in low
        )

        if not human:
            reasons.append(
                "human_missing"
            )

        if not anonymous:
            reasons.append(
                "anonymity_missing"
            )

        if not elevator:
            reasons.append(
                "elevator_context_missing"
            )

    elif scene == 6:
        human = bool(
            term_hits(
                text,
                HUMAN_TERMS
            )
        )

        anonymous = bool(
            term_hits(
                text,
                ANONYMITY_TERMS
            )
        )

        hallway = any(
            term in low
            for term in (
                "hallway",
                "corridor",
            )
        )

        if not human:
            reasons.append(
                "human_missing"
            )

        if not anonymous:
            reasons.append(
                "anonymity_missing"
            )

        if not hallway:
            reasons.append(
                "hallway_context_missing"
            )

    elif scene == 7:
        if family != "VIDEO":
            reasons.append(
                "video_required"
            )

        if "elevator" not in low:
            reasons.append(
                "elevator_missing"
            )

        bad = term_hits(
            text,
            ELEVATOR_FALSE_CONTEXT
            | VIDEO_FALSE_CONTEXT
        )

        if bad:
            reasons.append(
                "wrong_video_context"
            )

    return {
        "passed":
            not reasons,

        "reasons":
            reasons,
    }


def group_candidates(
    vi600,
    group_name
):
    return (
        vi600.get(
            "search_groups",
            {}
        ).get(
            group_name,
            {}
        ).get(
            "top_candidates",
            []
        )
        or []
    )


def select_candidate(
    scene,
    candidates,
    used_titles
):
    inspected = []

    for candidate in candidates:
        check = hard_filter(
            scene,
            candidate
        )

        title = str(
            candidate.get(
                "title"
            )
            or ""
        )

        if title in used_titles:
            check = {
                "passed":
                    False,

                "reasons":
                    check[
                        "reasons"
                    ]
                    + [
                        "portfolio_duplicate_title"
                    ],
            }

        inspected.append({
            "title":
                title,

            "provider":
                candidate.get(
                    "provider"
                ),

            "mime":
                candidate.get(
                    "mime"
                ),

            "score":
                candidate.get(
                    "score"
                ),

            "passed":
                check[
                    "passed"
                ],

            "reasons":
                check[
                    "reasons"
                ],
        })

        if check[
            "passed"
        ]:
            return (
                candidate,
                inspected
            )

    return None, inspected


def stage_commons_image(
    scene,
    candidate,
    cache,
    cache_stats,
    budget
):
    if (
        candidate.get(
            "provider"
        )
        != "WIKIMEDIA_COMMONS"
    ):
        return {
            "staged": False,
            "reason":
                "only_commons_image_staging_in_vi650",
        }

    metadata, source = (
        cached_exact_commons(
            candidate[
                "title"
            ],
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

    if not metadata:
        return {
            "staged": False,
            "reason":
                "exact_metadata_missing",
        }

    if metadata[
        "mime"
    ] not in RASTER_MIMES:
        return {
            "staged": False,
            "reason":
                "exact_metadata_not_raster",
        }

    url = (
        metadata.get(
            "thumb_url"
        )
        or metadata.get(
            "original_url"
        )
    )

    if not url:
        return {
            "staged": False,
            "reason":
                "download_url_missing",
        }

    suffix = (
        ".png"
        if metadata[
            "mime"
        ] == "image/png"
        else ".jpg"
    )

    destination = (
        SANDBOX /
        f"scene_{scene:02d}_portfolio{suffix}"
    )

    try:
        actual_bytes = (
            controlled_download(
                url,
                destination,
                budget
            )
        )

    except Exception as exc:
        return {
            "staged": False,
            "reason":
                type(exc).__name__
                + ":"
                + str(exc),
        }

    magic = image_magic(
        destination
    )

    if not (
        magic["jpeg"]
        or magic["png"]
    ):
        return {
            "staged": False,
            "reason":
                "image_magic_failed",
        }

    dims = image_size(
        destination
    )

    if not dims:
        return {
            "staged": False,
            "reason":
                "image_dimensions_failed",
        }

    width, height = dims

    geo = geometry(
        width,
        height
    )

    technical_ok = (
        geo["pixels"]
        >= 800_000
    )

    crop_ok = (
        geo[
            "retained_fraction"
        ]
        >= 0.28
    )

    if not technical_ok:
        return {
            "staged": False,
            "reason":
                "thumbnail_technical_gate_failed",
        }

    if not crop_ok:
        return {
            "staged": False,
            "reason":
                "vertical_crop_gate_failed",
        }

    return {
        "staged":
            True,

        "scene":
            scene,

        "title":
            candidate[
                "title"
            ],

        "provider":
            candidate.get(
                "provider"
            ),

        "sandbox_path":
            str(
                destination
            ),

        "sha256":
            sha256(
                destination
            ),

        "mime":
            metadata[
                "mime"
            ],

        "width":
            width,

        "height":
            height,

        "pixels":
            geo[
                "pixels"
            ],

        "bytes":
            actual_bytes,

        "geometry":
            geo,

        "license":
            candidate.get(
                "license"
            ),

        "license_score":
            candidate.get(
                "license_score"
            ),

        "semantic_score":
            candidate.get(
                "score"
            ),

        "source_original_width":
            metadata[
                "original_width"
            ],

        "source_original_height":
            metadata[
                "original_height"
            ],

        "thumbnail_width_request":
            THUMB_WIDTH,

        "production_media_mutated":
            False,
    }


def existing_asset(
    payload,
    expected_hash=None
):
    path_value = payload.get(
        "sandbox_path"
    )

    if not path_value:
        return {
            "valid": False,
            "reason":
                "sandbox_path_missing",
        }

    path = Path(
        path_value
    )

    if not path.exists():
        return {
            "valid": False,
            "reason":
                "sandbox_file_missing",
        }

    digest = sha256(
        path
    )

    if (
        expected_hash
        and digest
        != expected_hash
    ):
        return {
            "valid": False,
            "reason":
                "sandbox_hash_mismatch",
        }

    return {
        "valid":
            True,

        "path":
            str(path),

        "sha256":
            digest,

        "bytes":
            path.stat().st_size,
    }


def portfolio_score(
    semantic,
    geometry_data,
    license_score,
    unique=True
):
    semantic = float(
        semantic or 70
    )

    technical = min(
        100,
        max(
            0,
            (
                geometry_data.get(
                    "pixels",
                    0
                )
                / 2_000_000
            )
            * 100
        )
    )

    aspect = float(
        geometry_data.get(
            "aspect_score",
            0
        )
    )

    license_value = float(
        license_score or 80
    )

    diversity = (
        100
        if unique
        else 0
    )

    score = (
        semantic * .45
        + technical * .20
        + aspect * .15
        + license_value * .10
        + diversity * .10
    )

    return round(
        max(
            0,
            min(
                100,
                score
            )
        ),
        2
    )


def build_shadow(
    vi600,
    payload
):
    source_value = (
        vi600.get(
            "shadow_plan",
            {}
        ).get(
            "path"
        )
    )

    if not source_value:
        return {
            "written": False,
            "reason":
                "vi600_shadow_missing",
        }

    source = Path(
        source_value
    )

    if not source.exists():
        return {
            "written": False,
            "reason":
                "vi600_shadow_not_found",
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
        "vi650_shadow"
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

    vi550 = load_gate(
        VI550,
        required=True
    )

    vi600 = load_gate(
        VI600,
        required=True
    )

    short_id = str(
        vi600.get(
            "short_id"
        )
        or "2026-09-01_1433"
    )

    cache = load_cache()

    cache_stats = {
        "CACHE": 0,
        "NETWORK": 0,
        "ERROR": 0,
    }

    budget = {
        "used": 0
    }

    staged600 = {
        int(scene):
            payload
        for scene, payload
        in (
            vi600.get(
                "staged_replacements"
            )
            or {}
        ).items()
    }

    scene3_existing = (
        staged600.get(3)
        or {}
    )

    scene9_existing = (
        vi420.get(
            "scene9",
            {}
        ).get(
            "candidate"
        )
        or {}
    )

    scene1_existing = (
        vi330.get(
            "candidate"
        )
        or {}
    )

    scene3_validation = (
        existing_asset(
            scene3_existing,
            scene3_existing.get(
                "sha256"
            )
        )
    )

    scene9_validation = (
        existing_asset(
            scene9_existing,
            scene9_existing.get(
                "sha256"
            )
        )
    )

    scene1_validation = (
        existing_asset(
            scene1_existing,
            scene1_existing.get(
                "sha256"
            )
        )
    )

    used_titles = set()

    if scene3_validation[
        "valid"
    ]:
        used_titles.add(
            str(
                scene3_existing.get(
                    "title"
                )
                or ""
            )
        )

    if scene9_validation[
        "valid"
    ]:
        used_titles.add(
            str(
                scene9_existing.get(
                    "title"
                )
                or ""
            )
        )

    selections = {}

    audits = {}

    mapping = {
        1:
            "ELEVATOR_IMAGE",

        5:
            "HUMAN_ELEVATOR",

        6:
            "HUMAN_HALLWAY",

        7:
            "ELEVATOR_VIDEO",

        8:
            "HALLWAY_IMAGE",

        10:
            "ROOFTOP_IMAGE",

        11:
            "ROOFTOP_IMAGE",
    }

    # Prioritize scenes where we already know
    # likely good Commons image candidates exist.
    selection_order = [
        8,
        10,
        11,
        1,
        5,
        6,
        7,
    ]

    for scene in selection_order:
        group = mapping[
            scene
        ]

        candidates = (
            group_candidates(
                vi600,
                group
            )
        )

        selected, inspected = (
            select_candidate(
                scene,
                candidates,
                used_titles
            )
        )

        audits[
            scene
        ] = {
            "group":
                group,

            "checked":
                len(
                    inspected
                ),

            "inspection":
                inspected,
        }

        if not selected:
            continue

        # VI650 stages only still images.
        # Video candidates receive hard audit only.
        if scene == 7:
            selections[
                scene
            ] = {
                "selected_metadata":
                    selected,

                "staged":
                    False,

                "reason":
                    "video_requires_later_controlled_stage",
            }

            continue

        staged = stage_commons_image(
            scene,
            selected,
            cache,
            cache_stats,
            budget
        )

        selections[
            scene
        ] = {
            "selected_metadata":
                selected,

            "stage":
                staged,
        }

        if staged.get(
            "staged"
        ):
            used_titles.add(
                staged[
                    "title"
                ]
            )

    save_cache(
        cache
    )


    staged650 = {
        scene:
            item[
                "stage"
            ]
        for scene, item
        in selections.items()
        if (
            isinstance(
                item,
                dict
            )
            and item.get(
                "stage",
                {}
            ).get(
                "staged"
            )
        )
    }

    portfolio = []

    # Scene 1
    portfolio.append({
        "scene": 1,

        "action":
            (
                "HYBRID_ARCHIVAL_INSERT_READY_BASE_LICENSE_PENDING"
                if scene1_validation[
                    "valid"
                ]
                else
                "HYBRID_ARCHIVAL_SOURCE_MISSING"
            ),

        "asset":
            scene1_existing
            if scene1_validation[
                "valid"
            ]
            else None,

        "license_resolved_for_new_asset":
            scene1_validation[
                "valid"
            ],

        "production_base_provenance_resolved":
            False,
    })

    # Scene 2
    portfolio.append({
        "scene": 2,
        "action":
            "KEEP_CURRENT_VERIFIED",
        "license_resolved":
            True,
    })

    # Scene 3
    portfolio.append({
        "scene": 3,

        "action":
            (
                "PORTFOLIO_LOCK_STAGED_BROLL"
                if scene3_validation[
                    "valid"
                ]
                else
                "SCENE3_STAGED_ASSET_INVALID"
            ),

        "asset":
            scene3_existing
            if scene3_validation[
                "valid"
            ]
            else None,
    })

    # Scene 4
    scene4_source = (
        vi600.get(
            "scene4_factual_source"
        )
        or {}
    )

    scene4_valid = (
        existing_asset(
            scene4_source,
            scene4_source.get(
                "sha256"
            )
        )
        if scene4_source
        else {
            "valid": False
        }
    )

    portfolio.append({
        "scene": 4,

        "action":
            (
                "FACTUAL_FRAME_REQUIRED_WITH_SOURCE_REUSE_GUARD"
                if scene4_valid[
                    "valid"
                ]
                else
                "FACTUAL_SOURCE_UNRESOLVED"
            ),

        "asset":
            scene4_source
            if scene4_valid[
                "valid"
            ]
            else None,

        "shared_source_with_scene1":
            (
                scene4_source.get(
                    "sha256"
                )
                == scene1_existing.get(
                    "sha256"
                )
                and bool(
                    scene4_source.get(
                        "sha256"
                    )
                )
            ),
    })

    # Scenes 5 / 6
    for scene in [
        5,
        6,
    ]:
        staged = staged650.get(
            scene
        )

        portfolio.append({
            "scene":
                scene,

            "action":
                (
                    "ANONYMOUS_REENACTMENT_SHADOW_READY"
                    if staged
                    else
                    "ANONYMOUS_REENACTMENT_PENDING"
                ),

            "asset":
                staged,

            "identity_attribution_allowed":
                False,
        })

    # Scene 7
    scene7_selection = (
        selections.get(7)
    )

    scene7_metadata = (
        scene7_selection.get(
            "selected_metadata"
        )
        if scene7_selection
        else None
    )

    portfolio.append({
        "scene": 7,

        "action":
            (
                "STRICT_VIDEO_METADATA_READY_FOR_LATER_STAGE"
                if scene7_metadata
                else
                "KEEP_CURRENT_PROVENANCE_PENDING"
            ),

        "asset":
            scene7_metadata,

        "automatic_video_stage":
            False,
    })

    # Scene 8
    portfolio.append({
        "scene": 8,

        "action":
            (
                "PORTFOLIO_LOCK_STAGED_BROLL"
                if 8 in staged650
                else
                "LICENSED_BROLL_PENDING"
            ),

        "asset":
            staged650.get(8),
    })

    # Scene 9
    portfolio.append({
        "scene": 9,

        "action":
            (
                "PORTFOLIO_LOCK_STAGED_OBJECT"
                if scene9_validation[
                    "valid"
                ]
                else
                "SCENE9_STAGED_ASSET_INVALID"
            ),

        "asset":
            scene9_existing
            if scene9_validation[
                "valid"
            ]
            else None,
    })

    # Scenes 10 / 11
    for scene in [
        10,
        11,
    ]:
        portfolio.append({
            "scene":
                scene,

            "action":
                (
                    "PORTFOLIO_LOCK_STAGED_BROLL"
                    if scene in staged650
                    else
                    "LICENSED_ROOFTOP_PENDING"
                ),

            "asset":
                staged650.get(
                    scene
                ),
        })

    # Scene 12 is deliberately not relaxed.
    portfolio.append({
        "scene": 12,

        "action":
            "HARD_HOLD_FACTUAL_DOCUMENT",

        "asset":
            None,

        "factual_gate_relaxed":
            False,
    })

    # Staged SHA/title repetition audit.
    hashes = {}

    titles = {}

    for item in portfolio:
        asset = (
            item.get(
                "asset"
            )
            or {}
        )

        digest = asset.get(
            "sha256"
        )

        title = asset.get(
            "title"
        )

        if digest:
            hashes.setdefault(
                digest,
                []
            ).append(
                item["scene"]
            )

        if title:
            titles.setdefault(
                title,
                []
            ).append(
                item["scene"]
            )

    duplicate_hashes = {
        digest:
            scenes
        for digest, scenes
        in hashes.items()
        if len(scenes) > 1
    }

    duplicate_titles = {
        title:
            scenes
        for title, scenes
        in titles.items()
        if len(scenes) > 1
    }

    shared_case_hash = (
        scene1_existing.get(
            "sha256"
        )
    )

    # Scene1/4 reuse is known and not active twice yet.
    permitted_shared_hash = {}

    if (
        shared_case_hash
        and shared_case_hash
        in duplicate_hashes
    ):
        scenes = duplicate_hashes[
            shared_case_hash
        ]

        if set(scenes) == {
            1,
            4,
        }:
            permitted_shared_hash[
                shared_case_hash
            ] = scenes

            del duplicate_hashes[
                shared_case_hash
            ]

    scored_assets = []

    for item in portfolio:
        asset = (
            item.get(
                "asset"
            )
            or {}
        )

        if not asset:
            continue

        geo = asset.get(
            "geometry"
        )

        if not geo:
            width = (
                asset.get(
                    "width"
                )
                or 0
            )

            height = (
                asset.get(
                    "height"
                )
                or 0
            )

            geo = geometry(
                width,
                height
            )

        if not geo.get(
            "pixels"
        ):
            continue

        score = portfolio_score(
            asset.get(
                "semantic_score"
            )
            or asset.get(
                "score"
            )
            or 90,

            geo,

            asset.get(
                "license_score"
            )
            or 90,

            unique=True
        )

        scored_assets.append({
            "scene":
                item[
                    "scene"
                ],

            "portfolio_score":
                score,
        })

    unresolved = [
        item["scene"]
        for item in portfolio
        if any(
            token
            in item["action"]
            for token in (
                "PENDING",
                "HOLD",
                "REQUIRED",
                "MISSING",
                "INVALID",
            )
        )
    ]

    locked = [
        item["scene"]
        for item in portfolio
        if (
            "PORTFOLIO_LOCK"
            in item["action"]
            or item["action"]
            == "KEEP_CURRENT_VERIFIED"
        )
    ]

    readiness = round(
        (
            len([
                item
                for item in portfolio
                if item["scene"]
                not in unresolved
            ])
            / 12
        )
        * 100,
        2
    )


    corrections = {
        "vi600_trace_url_recovery":
            "UNTRUSTED_UNLESS_EXACT_SHA256_MATCH",

        "commons_pdf_as_broll_image":
            "HARD_REJECTED",

        "commons_djvu_svg_as_broll":
            "HARD_REJECTED",

        "grain_elevator_polysemy":
            "HARD_REJECTED",

        "wtc_vaporwave_elevator_video":
            "HARD_REJECTED",

        "anonymous_human_identity":
            "NO_IDENTITY_ATTRIBUTION",

        "same_candidate_multiple_scenes":
            "DISALLOWED",

        "oversized_commons_original":
            "USE_CONTROLLED_1600PX_THUMBNAIL",

        "scene12_factual_gate":
            "NOT_RELAXED",

        "automatic_replace":
            False,
    }

    next_queue = []

    for scene in unresolved:
        if scene == 12:
            priority = 100
            task = (
                "FACTUAL_DOCUMENT_SEARCH"
            )

        elif scene == 4:
            priority = 90
            task = (
                "FACTUAL_FRAME_DERIVATION"
            )

        elif scene in {
            5,
            6,
        }:
            priority = 70
            task = (
                "ANONYMOUS_HUMAN_SEARCH"
            )

        elif scene == 7:
            priority = 65
            task = (
                "STRICT_ELEVATOR_VIDEO"
            )

        elif scene == 1:
            priority = 60
            task = (
                "BASE_LICENSE_RESOLUTION"
            )

        else:
            priority = 50
            task = (
                "LICENSED_BROLL_COMPLETION"
            )

        next_queue.append({
            "scene":
                scene,

            "priority":
                priority,

            "task":
                task,
        })

    next_queue.sort(
        key=lambda x: (
            x["priority"],
            -x["scene"],
        ),
        reverse=True
    )

    payload = {
        "version":
            VERSION,

        "corrections":
            corrections,

        "portfolio":
            portfolio,

        "staged_vi650":
            staged650,

        "hardening_audits":
            audits,

        "duplicate_hashes":
            duplicate_hashes,

        "duplicate_titles":
            duplicate_titles,

        "permitted_shared_case_source":
            permitted_shared_hash,

        "renderer_activation":
            False,

        "production_media_mutated":
            False,

        "production_plan_mutated":
            False,

        "automatic_replace":
            False,

        "ffmpeg":
            False,

        "video_generated":
            False,
    }

    shadow = build_shadow(
        vi600,
        payload
    )

    blockers = []

    if duplicate_hashes:
        blockers.append(
            "active_portfolio_duplicate_hash"
        )

    if duplicate_titles:
        blockers.append(
            "active_portfolio_duplicate_title"
        )

    if not shadow.get(
        "written"
    ):
        blockers.append(
            "vi650_shadow_not_written"
        )

    warnings = []

    if 12 in unresolved:
        warnings.append(
            "factual_document_unresolved"
        )

    if 4 in unresolved:
        warnings.append(
            "scene4_frame_derivation_pending"
        )

    if any(
        scene in unresolved
        for scene in (
            5,
            6,
        )
    ):
        warnings.append(
            "anonymous_human_media_pending"
        )

    if (
        permitted_shared_hash
    ):
        warnings.append(
            "scene1_scene4_share_case_source_not_active_twice"
        )

    report = {
        "version":
            VERSION,

        "status":
            (
                "VI650_SHADOW_PORTFOLIO_OPTIMIZER_CERTIFIED"
                if not blockers
                else "HOLD"
            ),

        "short_id":
            short_id,

        "corrections":
            corrections,

        "portfolio":
            portfolio,

        "locked_scenes":
            locked,

        "unresolved_scenes":
            unresolved,

        "portfolio_readiness_percent":
            readiness,

        "scored_assets":
            scored_assets,

        "new_staged_scenes":
            sorted(
                staged650
            ),

        "selections":
            selections,

        "hardening_audits":
            audits,

        "duplicate_hashes":
            duplicate_hashes,

        "duplicate_titles":
            duplicate_titles,

        "permitted_shared_case_source":
            permitted_shared_hash,

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

        "next_queue":
            next_queue,

        "shadow_plan":
            shadow,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "network_executed":
            cache_stats.get(
                "NETWORK",
                0
            ) > 0,

        "controlled_download_executed":
            bool(
                staged650
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
        " VI650 SHADOW PORTFOLIO OPTIMIZER"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "NEW STAGED:",
        r[
            "new_staged_scenes"
        ]
    )

    print(
        "LOCKED:",
        r[
            "locked_scenes"
        ]
    )

    print(
        "UNRESOLVED:",
        r[
            "unresolved_scenes"
        ]
    )

    print(
        "READINESS:",
        r[
            "portfolio_readiness_percent"
        ],
        "%"
    )

    print(
        "CACHE:",
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
        "===== HARDENING CORRECTIONS ====="
    )

    for key, value in (
        r["corrections"].items()
    ):
        print(
            key,
            "=",
            value
        )

    print()
    print(
        "===== PORTFOLIO ====="
    )

    for item in r[
        "portfolio"
    ]:
        print(
            "SCENE",
            item["scene"],
            "|",
            item["action"],
        )

        asset = (
            item.get(
                "asset"
            )
            or {}
        )

        if asset.get(
            "title"
        ):
            print(
                "   ASSET:",
                asset[
                    "title"
                ]
            )

        if asset.get(
            "sandbox_path"
        ):
            print(
                "   SANDBOX:",
                asset[
                    "sandbox_path"
                ]
            )

    print()
    print(
        "===== HARD CANDIDATE AUDIT ====="
    )

    for scene in sorted(
        r["hardening_audits"]
    ):
        audit = r[
            "hardening_audits"
        ][scene]

        print(
            "SCENE",
            scene,
            "| group=",
            audit[
                "group"
            ],
            "| checked=",
            audit[
                "checked"
            ],
        )

        for item in (
            audit[
                "inspection"
            ][:4]
        ):
            print(
                "  -",
                "PASS"
                if item[
                    "passed"
                ]
                else "REJECT",
                "|",
                item[
                    "title"
                ],
                "|",
                item[
                    "reasons"
                ],
            )

    print()
    print(
        "===== PORTFOLIO SCORES ====="
    )

    for item in r[
        "scored_assets"
    ]:
        print(
            "SCENE",
            item["scene"],
            "| score=",
            item[
                "portfolio_score"
            ],
        )

    print()
    print(
        "DUPLICATE HASHES:",
        r[
            "duplicate_hashes"
        ]
    )

    print(
        "DUPLICATE TITLES:",
        r[
            "duplicate_titles"
        ]
    )

    print(
        "PERMITTED SHARED CASE SOURCE:",
        r[
            "permitted_shared_case_source"
        ]
    )

    print()
    print(
        "===== NEXT QUEUE ====="
    )

    for item in r[
        "next_queue"
    ]:
        print(
            "SCENE",
            item[
                "scene"
            ],
            "| priority=",
            item[
                "priority"
            ],
            "|",
            item[
                "task"
            ],
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
