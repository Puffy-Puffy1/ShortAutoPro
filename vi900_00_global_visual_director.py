#!/usr/bin/env python3

import copy
import hashlib
import html
import json
import os
import re
import subprocess
import time

from collections import Counter
from pathlib import Path
from urllib.parse import quote

import requests


VERSION = "900.00"

BASE = Path.home() / "ShortAutoPro"
LOG = BASE / "logs/producao"

SHORT_ID = "2026-09-01_1433"

VI800_MANIFEST = (
    BASE /
    "temp/vi800_publish/portfolio_manifest.json"
)

VI720_MANIFEST = (
    BASE /
    "temp/vi720_canary/portfolio_manifest.json"
)

VI700_MANIFEST = (
    BASE /
    "temp/vi700_canary/portfolio_manifest.json"
)

VI800_REPORT = (
    LOG /
    "vi800_00_production_readiness_latest.json"
)

OUT = (
    LOG /
    "vi900_00_global_visual_director_latest.json"
)

WORK = (
    BASE /
    "temp/vi900_assets"
)

PUBLISH = (
    BASE /
    "temp/vi900_publish"
)

MANIFEST = (
    PUBLISH /
    "portfolio_manifest.json"
)

CREDITS = (
    PUBLISH /
    "credits_vi900.txt"
)

COMMONS_API = (
    "https://commons.wikimedia.org/w/api.php"
)

HEADERS = {
    "User-Agent":
        "ShortAutoPro/900.00 "
        "(Global Visual Director)"
}

ILLUSTRATION_TEXT = (
    "IMAGEM ILUSTRATIVA"
)


GENERIC_SCENES = {
    3,
    6,
    8,
    9,
    10,
    11,
}


CASE_SOURCE_GROUP = (
    "elisa_lam_authentic_elevator_archive"
)

FACADE_SOURCE_GROUP = (
    "hotel_cecil_verified_facade"
)


ALLOWED_LICENSE = (
    "public domain",
    "cc0",
    "cc by",
    "cc-by",
    "creative commons attribution",
)


CORRIDOR_NEGATIVES = {
    "hospital",
    "school",
    "university",
    "airport",
    "ship",
    "cruise",
    "church",
    "museum",
    "shopping mall",
    "subway",
    "train station",
}


KNOWN_CORRIDOR_TITLES = [
    "File:Pincolini Hotel nom 07 - Reno Nevada.jpg",
]


def load_json(path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def load_gate(path):
    if not path.exists():
        return {}

    data = load_json(
        path
    )

    return data.get(
        "gate",
        data
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


def normalize(value):
    text = html.unescape(
        str(value or "")
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
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


def run(command):
    p = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if p.returncode != 0:
        raise RuntimeError(
            p.stderr[-3500:]
        )

    return p


def ffprobe(path):
    p = run([
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ])

    return json.loads(
        p.stdout
    )


def media_info(path):
    raw = ffprobe(
        path
    )

    result = {
        "width": None,
        "height": None,
        "duration": None,
        "fps": None,
    }

    try:
        result[
            "duration"
        ] = float(
            raw.get(
                "format",
                {}
            ).get(
                "duration"
            )
        )

    except Exception:
        pass

    for stream in (
        raw.get(
            "streams",
            []
        )
    ):
        if (
            stream.get(
                "codec_type"
            )
            != "video"
        ):
            continue

        result[
            "width"
        ] = stream.get(
            "width"
        )

        result[
            "height"
        ] = stream.get(
            "height"
        )

        result[
            "fps"
        ] = (
            stream.get(
                "avg_frame_rate"
            )
            or stream.get(
                "r_frame_rate"
            )
        )

        break

    return result


def existing(path):
    try:
        return (
            path is not None
            and Path(path).exists()
        )

    except Exception:
        return False


def ext_value(metadata, field):
    return html.unescape(
        str(
            metadata.get(
                field,
                {}
            ).get(
                "value"
            )
            or ""
        )
    )


def license_ok(value):
    low = normalize(
        value
    )

    return any(
        token in low
        for token in ALLOWED_LICENSE
    )


def commons_request(params):
    wait = 3

    for attempt in range(4):
        try:
            r = requests.get(
                COMMONS_API,
                params=params,
                headers=HEADERS,
                timeout=35
            )

            if r.status_code == 429:
                time.sleep(
                    wait
                )

                wait *= 2
                continue

            r.raise_for_status()

            return r.json()

        except Exception:
            if attempt == 3:
                return {}

            time.sleep(
                wait
            )

            wait *= 2

    return {}


def parse_commons_page(page):
    infos = (
        page.get(
            "imageinfo"
        )
        or []
    )

    if not infos:
        return None

    info = infos[0]

    metadata = (
        info.get(
            "extmetadata"
        )
        or {}
    )

    title = (
        page.get(
            "title"
        )
        or ""
    )

    candidate = {
        "title":
            title,

        "mime":
            normalize(
                info.get(
                    "mime"
                )
            ),

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

        "original_url":
            info.get(
                "url"
            ),

        "thumb_url":
            info.get(
                "thumburl"
            ),

        "license":
            ext_value(
                metadata,
                "LicenseShortName"
            ),

        "artist":
            normalize(
                ext_value(
                    metadata,
                    "Artist"
                )
            ),

        "description":
            normalize(
                ext_value(
                    metadata,
                    "ImageDescription"
                )
            ),

        "categories":
            normalize(
                ext_value(
                    metadata,
                    "Categories"
                )
            ),

        "page_url":
            (
                "https://commons.wikimedia.org/wiki/"
                + quote(
                    title.replace(
                        " ",
                        "_"
                    ),
                    safe=":/_()"
                )
            ),
    }

    candidate[
        "evidence_text"
    ] = normalize(
        " ".join([
            candidate[
                "title"
            ],
            candidate[
                "description"
            ],
            candidate[
                "categories"
            ],
        ])
    )

    return candidate


def commons_exact(title):
    data = commons_request({
        "action":
            "query",

        "titles":
            title,

        "prop":
            "imageinfo",

        "iiprop":
            "url|size|mime|extmetadata",

        "iiurlwidth":
            1600,

        "format":
            "json",

        "formatversion":
            2,
    })

    pages = (
        data.get(
            "query",
            {}
        ).get(
            "pages",
            []
        )
    )

    if not pages:
        return None

    return parse_commons_page(
        pages[0]
    )


def commons_search(query):
    data = commons_request({
        "action":
            "query",

        "generator":
            "search",

        "gsrsearch":
            query,

        "gsrnamespace":
            6,

        "gsrlimit":
            30,

        "prop":
            "imageinfo",

        "iiprop":
            "url|size|mime|extmetadata",

        "iiurlwidth":
            1600,

        "format":
            "json",

        "formatversion":
            2,
    })

    candidates = []

    for page in (
        data.get(
            "query",
            {}
        ).get(
            "pages",
            []
        )
    ):
        candidate = (
            parse_commons_page(
                page
            )
        )

        if candidate:
            candidates.append(
                candidate
            )

    return candidates


def candidate_is_raster(candidate):
    return (
        candidate.get(
            "mime"
        )
        in {
            "image/jpeg",
            "image/png",
        }
    )


def download_commons(
    candidate,
    destination
):
    url = (
        candidate.get(
            "thumb_url"
        )
        or candidate.get(
            "original_url"
        )
    )

    if not url:
        raise RuntimeError(
            "download_url_missing"
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
        stream=True,
        timeout=45
    ) as r:
        r.raise_for_status()

        total = 0

        with open(
            part,
            "wb"
        ) as f:
            for block in (
                r.iter_content(
                    256 * 1024
                )
            ):
                if not block:
                    continue

                total += len(
                    block
                )

                if total > (
                    8 * 1024 * 1024
                ):
                    part.unlink(
                        missing_ok=True
                    )

                    raise RuntimeError(
                        "download_limit_exceeded"
                    )

                f.write(
                    block
                )

    if total < 20_000:
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
        "path":
            str(destination),

        "sha256":
            sha256(destination),

        "bytes":
            total,
    }


def drawtext_available():
    try:
        p = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-filters",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        return (
            "drawtext"
            in p.stdout
        )

    except Exception:
        return False


def vertical_labeled_image(
    source,
    destination,
    label=True,
    foreground_width=1010,
    saturation=0.82,
    brightness=-0.05
):
    source = Path(
        source
    )

    destination = Path(
        destination
    )

    if not source.exists():
        raise RuntimeError(
            f"source_missing:{source}"
        )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    destination.unlink(
        missing_ok=True
    )

    fg = (
        f"scale={foreground_width}:-2,"
        f"eq=brightness={brightness}:"
        f"saturation={saturation}"
    )

    fc = (
        "[0:v]split=2[bg][fg];"
        "[bg]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "gblur=sigma=28,"
        "eq=brightness=-0.14:"
        "saturation=0.60"
        "[bg2];"
        "[fg]"
        + fg
        + "[fg2];"
        "[bg2][fg2]"
        "overlay=(W-w)/2:(H-h)/2"
    )

    if label:
        fc += (
            ",drawbox="
            "x=18:y=18:"
            "w=320:h=58:"
            "color=black@0.58:"
            "t=fill"
            ",drawtext="
            "text='IMAGEM ILUSTRATIVA':"
            "fontcolor=white:"
            "fontsize=25:"
            "x=32:y=33"
        )

    fc += (
        ",format=yuv420p"
    )

    run([
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-filter_complex",
        fc,
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(destination),
    ])

    info = media_info(
        destination
    )

    if (
        info.get(
            "width"
        )
        != 1080
        or
        info.get(
            "height"
        )
        != 1920
    ):
        raise RuntimeError(
            "derived_image_not_vertical_1080x1920"
        )

    return {
        "sandbox_path":
            str(destination),

        "sha256":
            sha256(
                destination
            ),

        "bytes":
            destination.stat().st_size,

        "family":
            "IMAGE",

        "info":
            info,

        "illustration_label":
            bool(label),
    }


def validate_image_source(
    path,
    expected_hash=None
):
    path = Path(
        path
    )

    if not path.exists():
        return False

    if expected_hash:
        return (
            sha256(path)
            == expected_hash
        )

    return True


def manifest_scene(
    manifest,
    scene
):
    return (
        manifest.get(
            "scenes",
            {}
        ).get(
            str(scene),
            {}
        )
    )


def source_for_scene(
    manifest,
    scene
):
    entry = manifest_scene(
        manifest,
        scene
    )

    candidate = entry.get(
        "canary_path"
    )

    if (
        candidate
        and Path(
            candidate
        ).exists()
    ):
        return Path(
            candidate
        )

    original = entry.get(
        "original_path"
    )

    if (
        original
        and Path(
            original
        ).exists()
    ):
        return Path(
            original
        )

    return None


def activate_asset(
    manifest,
    scene,
    asset,
    title,
    license_name,
    source_group,
    epistemic_usage,
    source_title=None,
    illustration=False
):
    entry = manifest_scene(
        manifest,
        scene
    )

    entry[
        "override_active"
    ] = True

    entry[
        "canary_path"
    ] = asset[
        "sandbox_path"
    ]

    entry[
        "expected_sha256"
    ] = asset[
        "sha256"
    ]

    entry[
        "family"
    ] = asset[
        "family"
    ]

    entry[
        "dimensions"
    ] = [
        asset[
            "info"
        ].get(
            "width"
        ),

        asset[
            "info"
        ].get(
            "height"
        ),
    ]

    entry[
        "title"
    ] = title

    entry[
        "license"
    ] = license_name

    entry[
        "source_title"
    ] = (
        source_title
        or title
    )

    entry[
        "source_group"
    ] = source_group

    entry[
        "epistemic_usage"
    ] = epistemic_usage

    entry[
        "illustration_label"
    ] = bool(
        illustration
    )

    entry[
        "mode"
    ] = (
        "VI900_GLOBAL_DIRECTOR_OVERRIDE"
    )


def corridor_candidate_score(
    candidate,
    excluded_titles
):
    title = str(
        candidate.get(
            "title"
        )
        or ""
    )

    text = candidate.get(
        "evidence_text"
    ) or ""

    reasons = []

    if title in excluded_titles:
        reasons.append(
            "already_used_title"
        )

    if not candidate_is_raster(
        candidate
    ):
        reasons.append(
            "not_raster"
        )

    if not license_ok(
        candidate.get(
            "license"
        )
    ):
        reasons.append(
            "license_not_approved"
        )

    hotel = (
        "hotel"
        in text
    )

    hallway = any(
        term in text
        for term in (
            "hallway",
            "corridor",
        )
    )

    if not hotel:
        reasons.append(
            "hotel_context_missing"
        )

    if not hallway:
        reasons.append(
            "corridor_role_missing"
        )

    negatives = sorted({
        term
        for term in (
            CORRIDOR_NEGATIVES
        )
        if term in text
    })

    if negatives:
        reasons.append(
            "wrong_context:"
            + ",".join(
                negatives
            )
        )

    pixels = (
        int(
            candidate.get(
                "width"
            )
            or 0
        )
        *
        int(
            candidate.get(
                "height"
            )
            or 0
        )
    )

    if pixels < 800_000:
        reasons.append(
            "resolution_too_low"
        )

    if reasons:
        return {
            "passed":
                False,

            "score":
                0,

            "reasons":
                reasons,
        }

    width = int(
        candidate.get(
            "width"
        )
        or 1
    )

    height = int(
        candidate.get(
            "height"
        )
        or 1
    )

    ratio = (
        width
        / height
    )

    target = (
        9 / 16
    )

    aspect = max(
        0,
        100
        - abs(
            ratio - target
        ) * 80
    )

    resolution = min(
        100,
        pixels
        / 4_000_000
        * 100
    )

    score = (
        50
        + aspect * .25
        + resolution * .25
    )

    return {
        "passed":
            True,

        "score":
            round(
                score,
                2
            ),

        "reasons":
            [],
    }


def find_third_corridor(
    excluded_titles
):
    audit = []

    candidates = []

    for title in (
        KNOWN_CORRIDOR_TITLES
    ):
        candidate = commons_exact(
            title
        )

        if candidate:
            candidates.append(
                candidate
            )

    candidates.extend(
        commons_search(
            "hotel hallway corridor interior"
        )
    )

    seen = set()

    qualified = []

    for candidate in candidates:
        title = candidate.get(
            "title"
        )

        if not title:
            continue

        if title in seen:
            continue

        seen.add(
            title
        )

        result = corridor_candidate_score(
            candidate,
            excluded_titles
        )

        audit.append({
            "title":
                title,

            "passed":
                result[
                    "passed"
                ],

            "score":
                result[
                    "score"
                ],

            "reasons":
                result[
                    "reasons"
                ],

            "license":
                candidate.get(
                    "license"
                ),
        })

        if result[
            "passed"
        ]:
            candidate[
                "vi900_score"
            ] = result[
                "score"
            ]

            qualified.append(
                candidate
            )

    qualified.sort(
        key=lambda x:
            x.get(
                "vi900_score",
                0
            ),
        reverse=True
    )

    return (
        qualified[0]
        if qualified
        else None,
        audit
    )


def stage_corridor_candidate(
    candidate
):
    suffix = (
        ".png"
        if candidate.get(
            "mime"
        )
        == "image/png"
        else ".jpg"
    )

    raw = (
        WORK /
        (
            "scene_06_corridor_source"
            + suffix
        )
    )

    download_commons(
        candidate,
        raw
    )

    return vertical_labeled_image(
        raw,
        WORK /
        "scene_06_corridor_illustrative.jpg",
        label=True,
        foreground_width=1020,
        saturation=0.80,
        brightness=-0.06
    )


def select_parent_manifest():
    if VI800_MANIFEST.exists():
        return (
            VI800_MANIFEST,
            load_json(
                VI800_MANIFEST
            ),
            "VI800"
        )

    if VI720_MANIFEST.exists():
        return (
            VI720_MANIFEST,
            load_json(
                VI720_MANIFEST
            ),
            "VI720"
        )

    raise RuntimeError(
        "no_parent_manifest_available"
    )


def load_vi700():
    if not VI700_MANIFEST.exists():
        raise RuntimeError(
            "vi700_manifest_missing"
        )

    return load_json(
        VI700_MANIFEST
    )


def vi700_asset(
    vi700,
    scene
):
    entry = manifest_scene(
        vi700,
        scene
    )

    path = entry.get(
        "canary_path"
    )

    if not path:
        raise RuntimeError(
            f"vi700_scene_{scene}_path_missing"
        )

    path = Path(
        path
    )

    if not path.exists():
        raise RuntimeError(
            f"vi700_scene_{scene}_file_missing"
        )

    expected = entry.get(
        "expected_sha256"
    )

    if (
        expected
        and sha256(
            path
        )
        != expected
    ):
        raise RuntimeError(
            f"vi700_scene_{scene}_hash_mismatch"
        )

    return (
        entry,
        path
    )


def rebuild_generic_asset(
    vi700,
    scene,
    output_name,
    source_group,
    epistemic_usage
):
    entry, source = vi700_asset(
        vi700,
        scene
    )

    asset = vertical_labeled_image(
        source,
        WORK /
        output_name,
        label=True,
        foreground_width=1010,
        saturation=0.82,
        brightness=-0.05
    )

    return {
        "asset":
            asset,

        "title":
            entry.get(
                "title"
            )
            or (
                f"VI700 scene {scene}"
            ),

        "license":
            entry.get(
                "license"
            )
            or "See source",

        "source_group":
            source_group,

        "epistemic_usage":
            epistemic_usage,

        "source_title":
            entry.get(
                "title"
            ),
    }


def rebuild_parent_generic(
    parent,
    scene,
    output_name,
    source_group,
    epistemic_usage
):
    entry = manifest_scene(
        parent,
        scene
    )

    source = source_for_scene(
        parent,
        scene
    )

    if not source:
        raise RuntimeError(
            f"parent_scene_{scene}_source_missing"
        )

    asset = vertical_labeled_image(
        source,
        WORK /
        output_name,
        label=True,
        foreground_width=1010,
        saturation=0.72,
        brightness=-0.07
    )

    return {
        "asset":
            asset,

        "title":
            entry.get(
                "title"
            )
            or f"Scene {scene}",

        "license":
            entry.get(
                "license"
            )
            or "See source",

        "source_group":
            source_group,

        "epistemic_usage":
            epistemic_usage,

        "source_title":
            entry.get(
                "source_title"
            )
            or entry.get(
                "title"
            ),
    }


def apply_vi900_portfolio():
    parent_path, parent, parent_version = (
        select_parent_manifest()
    )

    vi700 = load_vi700()

    manifest = copy.deepcopy(
        parent
    )

    manifest[
        "version"
    ] = VERSION

    manifest[
        "parent_manifest"
    ] = str(
        parent_path
    )

    manifest[
        "parent_version"
    ] = parent_version


    if not drawtext_available():
        raise RuntimeError(
            "ffmpeg_drawtext_filter_missing"
        )


    # --------------------------------------------------
    # SCENE 3
    # Arizona hallway:
    # allowed, but explicitly illustrative.
    # --------------------------------------------------

    s3 = rebuild_generic_asset(
        vi700,
        3,
        "scene_03_hallway_illustrative.jpg",
        "arizona_biltmore_hallway",
        "ILLUSTRATIVE_HOTEL_CORRIDOR"
    )

    activate_asset(
        manifest,
        3,
        s3["asset"],
        s3["title"],
        s3["license"],
        s3["source_group"],
        s3["epistemic_usage"],
        s3["source_title"],
        illustration=True
    )


    # --------------------------------------------------
    # SCENE 8
    # Different hotel corridor.
    # --------------------------------------------------

    s8 = rebuild_generic_asset(
        vi700,
        8,
        "scene_08_hallway_illustrative.jpg",
        "conrad_indianapolis_hallway",
        "ILLUSTRATIVE_HOTEL_CORRIDOR"
    )

    activate_asset(
        manifest,
        8,
        s8["asset"],
        s8["title"],
        s8["license"],
        s8["source_group"],
        s8["epistemic_usage"],
        s8["source_title"],
        illustration=True
    )


    # --------------------------------------------------
    # SCENE 6
    # Third and unique hotel corridor.
    # --------------------------------------------------

    excluded = {
        str(
            s3[
                "source_title"
            ]
            or ""
        ),
        str(
            s8[
                "source_title"
            ]
            or ""
        ),
    }

    corridor_candidate, corridor_audit = (
        find_third_corridor(
            excluded
        )
    )

    if not corridor_candidate:
        raise RuntimeError(
            "no_unique_licensed_scene6_corridor"
        )

    s6_asset = stage_corridor_candidate(
        corridor_candidate
    )

    activate_asset(
        manifest,
        6,
        s6_asset,
        corridor_candidate[
            "title"
        ],
        corridor_candidate[
            "license"
        ],
        "vi900_unique_hotel_corridor",
        "ILLUSTRATIVE_HOTEL_CORRIDOR",
        corridor_candidate[
            "title"
        ],
        illustration=True
    )


    # --------------------------------------------------
    # SCENE 9
    # Medication is illustrative only.
    # --------------------------------------------------

    s9 = rebuild_parent_generic(
        parent,
        9,
        "scene_09_medication_illustrative.jpg",
        "generic_medication_broll",
        "ILLUSTRATIVE_MEDICATION_BROLL"
    )

    activate_asset(
        manifest,
        9,
        s9["asset"],
        s9["title"],
        s9["license"],
        s9["source_group"],
        s9["epistemic_usage"],
        s9["source_title"],
        illustration=True
    )


    # --------------------------------------------------
    # SCENE 10
    # Restore generic rooftop/water tower,
    # but CLEARLY label it as illustration.
    # --------------------------------------------------

    s10 = rebuild_generic_asset(
        vi700,
        10,
        "scene_10_rooftop_illustrative.jpg",
        "nyc_water_towers_46th_street",
        "ILLUSTRATIVE_ROOFTOP_WATER_STRUCTURE"
    )

    activate_asset(
        manifest,
        10,
        s10["asset"],
        s10["title"],
        s10["license"],
        s10["source_group"],
        s10["epistemic_usage"],
        s10["source_title"],
        illustration=True
    )


    # --------------------------------------------------
    # SCENE 11
    # Different rooftop source.
    # --------------------------------------------------

    s11 = rebuild_generic_asset(
        vi700,
        11,
        "scene_11_rooftop_illustrative.jpg",
        "nyc_spires_rooftop",
        "ILLUSTRATIVE_ROOFTOP_CONTEXT"
    )

    activate_asset(
        manifest,
        11,
        s11["asset"],
        s11["title"],
        s11["license"],
        s11["source_group"],
        s11["epistemic_usage"],
        s11["source_title"],
        illustration=True
    )


    # --------------------------------------------------
    # Keep scenes 4 / 5 / 7 from parent,
    # but tag authentic source group.
    # --------------------------------------------------

    for scene in (
        4,
        5,
        7,
    ):
        entry = manifest_scene(
            manifest,
            scene
        )

        entry[
            "source_group"
        ] = (
            CASE_SOURCE_GROUP
        )

        entry[
            "illustration_label"
        ] = False

        entry[
            "epistemic_usage"
        ] = (
            "AUTHENTIC_CASE_ARCHIVAL_CONTEXT"
        )


    # --------------------------------------------------
    # Verified facade only scene 2 + CTA scene 12.
    # --------------------------------------------------

    for scene in (
        2,
        12,
    ):
        entry = manifest_scene(
            manifest,
            scene
        )

        entry[
            "source_group"
        ] = (
            FACADE_SOURCE_GROUP
        )

        entry[
            "illustration_label"
        ] = False

        entry[
            "epistemic_usage"
        ] = (
            "VERIFIED_HOTEL_CECIL_CONTEXT"
        )


    # Scene 1 legacy becomes its own source group.
    entry1 = manifest_scene(
        manifest,
        1
    )

    entry1[
        "source_group"
    ] = (
        "legacy_scene1_hook"
    )


    active = sorted(
        int(scene)
        for scene, entry
        in (
            manifest.get(
                "scenes",
                {}
            ).items()
        )
        if entry.get(
            "override_active"
        )
    )

    manifest[
        "active_override_scenes"
    ] = active


    manifest[
        "vi900_policy"
    ] = {
        "global_director":
            True,

        "generic_media_requires_label":
            True,

        "hotel_cecil_facade_max_scenes":
            2,

        "authentic_case_source_max_scenes":
            3,

        "generic_source_max_scenes":
            1,

        "minimum_unique_source_groups":
            8,

        "minimum_unique_sources_per_6_scene_window":
            4,

        "no_generic_rooftop_as_case_evidence":
            True,

        "no_generic_corridor_as_case_evidence":
            True,

        "no_generic_medication_as_case_evidence":
            True,

        "automatic_production_replace":
            False,
    }

    return (
        manifest,
        corridor_audit,
        corridor_candidate,
        parent_version
    )


def derive_source_group(
    scene,
    entry
):
    explicit = entry.get(
        "source_group"
    )

    if explicit:
        return explicit

    title = normalize(
        entry.get(
            "source_title"
        )
        or entry.get(
            "title"
        )
    )

    if (
        "elisa lam"
        in title
        and
        "elevator"
        in title
    ):
        return (
            CASE_SOURCE_GROUP
        )

    if (
        "hotel cecil"
        in title
    ):
        return (
            FACADE_SOURCE_GROUP
        )

    expected = entry.get(
        "expected_sha256"
    )

    if expected:
        return (
            "asset_"
            + expected[:16]
        )

    return (
        f"scene_{scene}_unknown"
    )


def source_sequence(
    manifest
):
    sequence = []

    for scene in range(
        1,
        13
    ):
        entry = manifest_scene(
            manifest,
            scene
        )

        group = derive_source_group(
            scene,
            entry
        )

        entry[
            "source_group"
        ] = group

        sequence.append({
            "scene":
                scene,

            "source_group":
                group,

            "title":
                entry.get(
                    "title"
                ),

            "illustration_label":
                bool(
                    entry.get(
                        "illustration_label"
                    )
                ),

            "epistemic_usage":
                entry.get(
                    "epistemic_usage"
                ),

            "override_active":
                bool(
                    entry.get(
                        "override_active"
                    )
                ),
        })

    return sequence


def max_consecutive_group(
    sequence
):
    maximum = 0

    current = None
    run_length = 0

    worst = None

    for item in sequence:
        group = item[
            "source_group"
        ]

        if group == current:
            run_length += 1

        else:
            current = group
            run_length = 1

        if run_length > maximum:
            maximum = run_length
            worst = group

    return (
        maximum,
        worst
    )


def window_diversity(
    sequence,
    window=6
):
    result = []

    for start in range(
        0,
        len(sequence)
        - window
        + 1
    ):
        part = sequence[
            start:
            start + window
        ]

        unique = sorted({
            item[
                "source_group"
            ]
            for item in part
        })

        result.append({
            "start_scene":
                part[0][
                    "scene"
                ],

            "end_scene":
                part[-1][
                    "scene"
                ],

            "unique_sources":
                len(
                    unique
                ),

            "sources":
                unique,
        })

    return result


def global_diversity_gate(
    manifest
):
    sequence = source_sequence(
        manifest
    )

    counts = Counter(
        item[
            "source_group"
        ]
        for item in sequence
    )

    unique_groups = sorted(
        counts
    )

    blockers = []

    warnings = []


    if len(
        unique_groups
    ) < 8:
        blockers.append(
            "global_unique_source_count_below_8"
        )


    facade_count = counts.get(
        FACADE_SOURCE_GROUP,
        0
    )

    if facade_count > 2:
        blockers.append(
            "hotel_cecil_facade_overused"
        )


    case_count = counts.get(
        CASE_SOURCE_GROUP,
        0
    )

    if case_count > 3:
        blockers.append(
            "authentic_case_archive_overused"
        )


    for group, count in (
        counts.items()
    ):
        if group in {
            FACADE_SOURCE_GROUP,
            CASE_SOURCE_GROUP,
        }:
            continue

        if count > 1:
            blockers.append(
                "generic_source_repeated:"
                + group
            )


    max_run, worst_run = (
        max_consecutive_group(
            sequence
        )
    )

    if max_run > 2:
        blockers.append(
            "source_repetition_run_above_2"
        )


    windows = window_diversity(
        sequence,
        window=6
    )

    for item in windows:
        if (
            item[
                "unique_sources"
            ]
            < 4
        ):
            blockers.append(
                "low_window_diversity:"
                + str(
                    item[
                        "start_scene"
                    ]
                )
                + "-"
                + str(
                    item[
                        "end_scene"
                    ]
                )
            )


    for scene in sorted(
        GENERIC_SCENES
    ):
        entry = manifest_scene(
            manifest,
            scene
        )

        if not entry.get(
            "illustration_label"
        ):
            blockers.append(
                f"scene_{scene}_generic_missing_illustration_label"
            )


    s10 = manifest_scene(
        manifest,
        10
    )

    s11 = manifest_scene(
        manifest,
        11
    )

    if (
        s10.get(
            "source_group"
        )
        ==
        s11.get(
            "source_group"
        )
    ):
        blockers.append(
            "rooftop_source_duplicate"
        )


    required_active = {
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
    }

    actual_active = {
        int(scene)
        for scene, entry
        in (
            manifest.get(
                "scenes",
                {}
            ).items()
        )
        if entry.get(
            "override_active"
        )
    }

    missing = sorted(
        required_active
        - actual_active
    )

    if missing:
        blockers.append(
            "required_override_missing:"
            + ",".join(
                str(x)
                for x in missing
            )
        )


    diversity_score = round(
        min(
            100,
            (
                len(
                    unique_groups
                )
                / 9
            )
            * 70
            +
            (
                sum(
                    min(
                        1,
                        item[
                            "unique_sources"
                        ]
                        / 4
                    )
                    for item in windows
                )
                / max(
                    1,
                    len(
                        windows
                    )
                )
            )
            * 30
        ),
        2
    )


    if facade_count == 2:
        warnings.append(
            "hotel_cecil_facade_used_exactly_twice"
        )


    return {
        "sequence":
            sequence,

        "counts":
            dict(
                counts
            ),

        "unique_source_groups":
            unique_groups,

        "unique_source_count":
            len(
                unique_groups
            ),

        "facade_count":
            facade_count,

        "case_archive_count":
            case_count,

        "maximum_consecutive_same_source":
            max_run,

        "worst_consecutive_source":
            worst_run,

        "windows":
            windows,

        "diversity_score":
            diversity_score,

        "blockers":
            sorted(
                set(
                    blockers
                )
            ),

        "warnings":
            warnings,
    }


def write_credits(
    manifest,
    corridor_candidate
):
    lines = [
        "SHORTAUTOPRO VI900 - MEDIA CREDITS",
        "=================================",
        "",
        (
            "Aviso editorial: mídias marcadas como "
            "'IMAGEM ILUSTRATIVA' são usadas apenas "
            "como contexto visual e não representam "
            "o local ou momento exato narrado."
        ),
        "",
    ]

    seen = set()

    for scene in range(
        1,
        13
    ):
        entry = manifest_scene(
            manifest,
            scene
        )

        title = (
            entry.get(
                "source_title"
            )
            or entry.get(
                "title"
            )
        )

        license_name = (
            entry.get(
                "license"
            )
            or "See source"
        )

        group = (
            entry.get(
                "source_group"
            )
        )

        if not title:
            continue

        key = (
            str(title),
            str(license_name),
            str(group),
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        lines.extend([
            f"SCENE SOURCE GROUP: {group}",
            f"Title: {title}",
            f"License: {license_name}",
            (
                "Epistemic usage: "
                + str(
                    entry.get(
                        "epistemic_usage"
                    )
                    or "context"
                )
            ),
            (
                "Illustrative label: "
                + str(
                    bool(
                        entry.get(
                            "illustration_label"
                        )
                    )
                )
            ),
        ])

        if str(
            title
        ).startswith(
            "File:"
        ):
            lines.append(
                "Source: "
                + (
                    "https://commons.wikimedia.org/wiki/"
                    + quote(
                        str(
                            title
                        ).replace(
                            " ",
                            "_"
                        ),
                        safe=":/_()"
                    )
                )
            )

        lines.append(
            ""
        )


    if corridor_candidate:
        lines.extend([
            "VI900 NEW CORRIDOR DISCOVERY",
            (
                "Title: "
                + corridor_candidate[
                    "title"
                ]
            ),
            (
                "License: "
                + str(
                    corridor_candidate.get(
                        "license"
                    )
                )
            ),
            (
                "Source: "
                + str(
                    corridor_candidate.get(
                        "page_url"
                    )
                    or ""
                )
            ),
            "",
        ])


    CREDITS.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    CREDITS.write_text(
        "\n".join(
            lines
        ),
        encoding="utf-8"
    )


def evaluate():
    (
        manifest,
        corridor_audit,
        corridor_candidate,
        parent_version,
    ) = apply_vi900_portfolio()


    diversity = global_diversity_gate(
        manifest
    )


    write_credits(
        manifest,
        corridor_candidate
    )


    MANIFEST.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    MANIFEST.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    blockers = list(
        diversity[
            "blockers"
        ]
    )


    ready = not blockers


    report = {
        "version":
            VERSION,

        "status":
            (
                "VI900_GLOBAL_VISUAL_DIRECTOR_READY"
                if ready
                else "HOLD"
            ),

        "short_id":
            SHORT_ID,

        "parent_version":
            parent_version,

        "canary_ready":
            ready,

        "active_override_scenes":
            manifest[
                "active_override_scenes"
            ],

        "global_diversity":
            diversity,

        "scene6_corridor_candidate":
            corridor_candidate,

        "scene6_corridor_audit":
            corridor_audit,

        "truth_policy": {
            "generic_corridor":
                "ILLUSTRATION_LABEL_REQUIRED",

            "generic_rooftop":
                "ILLUSTRATION_LABEL_REQUIRED",

            "generic_medication":
                "ILLUSTRATION_LABEL_REQUIRED",

            "hotel_cecil_facade":
                "MAX_2_SCENES",

            "authentic_case_archive":
                "MAX_3_SCENES",

            "generic_asset_reuse":
                "MAX_1_SCENE",

            "production_auto_replace":
                False,
        },

        "manifest": {
            "path":
                str(MANIFEST),

            "sha256":
                sha256(
                    MANIFEST
                ),
        },

        "credits": {
            "path":
                str(CREDITS),

            "sha256":
                sha256(
                    CREDITS
                ),
        },

        "blockers":
            blockers,

        "warnings":
            diversity[
                "warnings"
            ],

        "network_executed":
            True,

        "production_media_mutated":
            False,

        "production_plan_mutated":
            False,

        "core_source_mutated":
            False,

        "automatic_replace":
            False,

        "full_video_generated":
            False,
    }


    OUT.write_text(
        json.dumps(
            {
                "gate":
                    report
            },
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
        " VI900 GLOBAL VISUAL DIRECTOR"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "CANARY READY:",
        r[
            "canary_ready"
        ]
    )

    print(
        "PARENT:",
        r[
            "parent_version"
        ]
    )

    print(
        "ACTIVE OVERRIDES:",
        r[
            "active_override_scenes"
        ]
    )

    d = r[
        "global_diversity"
    ]

    print()
    print(
        "===== GLOBAL DIVERSITY ====="
    )

    print(
        "UNIQUE SOURCES:",
        d[
            "unique_source_count"
        ]
    )

    print(
        "DIVERSITY SCORE:",
        d[
            "diversity_score"
        ]
    )

    print(
        "HOTEL CECIL FACADE COUNT:",
        d[
            "facade_count"
        ]
    )

    print(
        "AUTHENTIC CASE ARCHIVE COUNT:",
        d[
            "case_archive_count"
        ]
    )

    print(
        "MAX CONSECUTIVE SAME SOURCE:",
        d[
            "maximum_consecutive_same_source"
        ],
        "|",
        d[
            "worst_consecutive_source"
        ]
    )

    print()
    print(
        "===== SOURCE SEQUENCE ====="
    )

    for item in d[
        "sequence"
    ]:
        print(
            "SCENE",
            item[
                "scene"
            ],
            "|",
            item[
                "source_group"
            ],
            "| illustrative=",
            item[
                "illustration_label"
            ],
            "|",
            item[
                "epistemic_usage"
            ],
        )

    print()
    print(
        "===== 6-SCENE WINDOWS ====="
    )

    for item in d[
        "windows"
    ]:
        print(
            f"{item['start_scene']}-{item['end_scene']}",
            "| unique=",
            item[
                "unique_sources"
            ],
            "|",
            item[
                "sources"
            ]
        )

    print()
    print(
        "===== SCENE 6 NEW CORRIDOR ====="
    )

    candidate = r[
        "scene6_corridor_candidate"
    ]

    if candidate:
        print(
            "TITLE:",
            candidate[
                "title"
            ]
        )

        print(
            "LICENSE:",
            candidate[
                "license"
            ]
        )

        print(
            "SCORE:",
            candidate[
                "vi900_score"
            ]
        )

    print()
    print(
        "MANIFEST:",
        r["manifest"]
    )

    print(
        "CREDITS:",
        r["credits"]
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
        "PRODUCTION MEDIA MUTATED:",
        r[
            "production_media_mutated"
        ]
    )

    print(
        "CORE SOURCE MUTATED:",
        r[
            "core_source_mutated"
        ]
    )
