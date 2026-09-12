#!/usr/bin/env python3
from short_id_runtime_v1 import resolve_short_id as _sap_resolve_short_id

import copy
import hashlib
import html
import json
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

import requests


VERSION = "800.00"

BASE = Path.home() / "ShortAutoPro"

LOG = BASE / "logs/producao"

PARENT_MANIFEST = (
    BASE /
    "temp/vi720_canary/portfolio_manifest.json"
)

VI330 = (
    LOG /
    "vi330_00_controlled_real_ab_latest.json"
)

VI720 = (
    LOG /
    "vi720_00_case_context_repair_latest.json"
)

OUT = (
    LOG /
    "vi800_00_production_readiness_latest.json"
)

WORK = (
    BASE /
    "temp/vi800_assets"
)

PUBLISH = (
    BASE /
    "temp/vi800_publish"
)

MANIFEST = (
    PUBLISH /
    "portfolio_manifest.json"
)

CREDITS = (
    PUBLISH /
    "credits_vi800.txt"
)

SHORT_ID = _sap_resolve_short_id()

COMMONS_API = (
    "https://commons.wikimedia.org/w/api.php"
)

HEADERS = {
    "User-Agent":
        "ShortAutoPro/800.00 "
        "(production readiness)"
}

HOTEL_CECIL_TITLE = (
    "File:Hotel Cecil LA.jpg"
)

ROOF_QUERIES = [
    "Hotel Cecil rooftop Los Angeles",
    "Cecil Hotel rooftop Los Angeles",
    "Hotel Cecil water tank",
    "Cecil Hotel water tank",
]

ROOF_TERMS = {
    "roof",
    "rooftop",
    "water tank",
    "water tower",
}

WRONG_GEO = {
    "new york",
    "manhattan",
    "chicago",
    "indianapolis",
    "arizona",
    "nevada",
    "egypt",
    "alexandria",
}


def load_gate(path):
    if not path.exists():
        return {}

    raw = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return raw.get(
        "gate",
        raw
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
            p.stderr[-3000:]
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

    info = {
        "duration":
            None,

        "width":
            None,

        "height":
            None,

        "fps":
            None,
    }

    try:
        info[
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

        info[
            "width"
        ] = stream.get(
            "width"
        )

        info[
            "height"
        ] = stream.get(
            "height"
        )

        info[
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

    return info


def ext_value(meta, name):
    value = (
        meta.get(
            name,
            {}
        ).get(
            "value"
        )
    )

    return html.unescape(
        str(value or "")
    )


def commons_exact(title):
    params = {
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
    }

    try:
        r = requests.get(
            COMMONS_API,
            params=params,
            headers=HEADERS,
            timeout=30
        )

        if r.status_code == 429:
            time.sleep(5)

            r = requests.get(
                COMMONS_API,
                params=params,
                headers=HEADERS,
                timeout=30
            )

        r.raise_for_status()

        pages = (
            r.json()
            .get(
                "query",
                {}
            )
            .get(
                "pages",
                []
            )
        )

        if not pages:
            return None

        page = pages[0]

        infos = (
            page.get(
                "imageinfo"
            )
            or []
        )

        if not infos:
            return None

        info = infos[0]

        meta = (
            info.get(
                "extmetadata"
            )
            or {}
        )

        return {
            "title":
                page.get(
                    "title"
                )
                or title,

            "original_url":
                info.get(
                    "url"
                ),

            "thumb_url":
                info.get(
                    "thumburl"
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

            "mime":
                info.get(
                    "mime"
                ),

            "license":
                ext_value(
                    meta,
                    "LicenseShortName"
                ),

            "artist":
                normalize(
                    ext_value(
                        meta,
                        "Artist"
                    )
                ),

            "credit":
                normalize(
                    ext_value(
                        meta,
                        "Credit"
                    )
                ),

            "description":
                normalize(
                    ext_value(
                        meta,
                        "ImageDescription"
                    )
                ),

            "categories":
                normalize(
                    ext_value(
                        meta,
                        "Categories"
                    )
                ),

            "page_url":
                (
                    "https://commons.wikimedia.org/wiki/"
                    + quote(
                        str(
                            page.get(
                                "title"
                            )
                            or title
                        ).replace(
                            " ",
                            "_"
                        ),
                        safe=":/_()"
                    )
                ),
        }

    except Exception:
        return None


def commons_search(query):
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
            12,

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
    }

    try:
        r = requests.get(
            COMMONS_API,
            params=params,
            headers=HEADERS,
            timeout=30
        )

        if r.status_code == 429:
            time.sleep(5)

            r = requests.get(
                COMMONS_API,
                params=params,
                headers=HEADERS,
                timeout=30
            )

        r.raise_for_status()

        result = []

        for page in (
            r.json()
            .get(
                "query",
                {}
            )
            .get(
                "pages",
                []
            )
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

            meta = (
                info.get(
                    "extmetadata"
                )
                or {}
            )

            candidate = {
                "title":
                    page.get(
                        "title"
                    )
                    or "",

                "original_url":
                    info.get(
                        "url"
                    ),

                "thumb_url":
                    info.get(
                        "thumburl"
                    ),

                "mime":
                    info.get(
                        "mime"
                    ),

                "license":
                    ext_value(
                        meta,
                        "LicenseShortName"
                    ),

                "artist":
                    normalize(
                        ext_value(
                            meta,
                            "Artist"
                        )
                    ),

                "description":
                    normalize(
                        ext_value(
                            meta,
                            "ImageDescription"
                        )
                    ),

                "categories":
                    normalize(
                        ext_value(
                            meta,
                            "Categories"
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
            }

            text = normalize(
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

            cecil = (
                "hotel cecil"
                in text
                or
                "cecil hotel"
                in text
            )

            roof = any(
                term in text
                for term in (
                    ROOF_TERMS
                )
            )

            wrong_geo = any(
                term in text
                for term in (
                    WRONG_GEO
                )
            )

            raster = (
                str(
                    candidate.get(
                        "mime"
                    )
                ).lower()
                in {
                    "image/jpeg",
                    "image/png",
                }
            )

            license_text = (
                candidate.get(
                    "license"
                )
                or ""
            ).lower()

            licensed = any(
                token in license_text
                for token in (
                    "public domain",
                    "cc by",
                    "cc0",
                )
            )

            candidate[
                "strict_truth"
            ] = (
                cecil
                and roof
                and not wrong_geo
                and raster
                and licensed
            )

            result.append(
                candidate
            )

        return result

    except Exception:
        return []


def find_verified_rooftop():
    audit = []

    for query in ROOF_QUERIES:
        results = commons_search(
            query
        )

        for candidate in results:
            audit.append({
                "query":
                    query,

                "title":
                    candidate[
                        "title"
                    ],

                "strict_truth":
                    candidate[
                        "strict_truth"
                    ],

                "license":
                    candidate[
                        "license"
                    ],
            })

            if candidate[
                "strict_truth"
            ]:
                return (
                    candidate,
                    audit
                )

    return None, audit


def download_candidate(
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
            "candidate_url_missing"
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

                total += len(
                    chunk
                )

                if total > (
                    8 * 1024 * 1024
                ):
                    part.unlink(
                        missing_ok=True
                    )

                    raise RuntimeError(
                        "candidate_too_large"
                    )

                f.write(
                    chunk
                )

    if total < 20_000:
        part.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            "candidate_too_small"
        )

    part.replace(
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


def vertical_context_image(
    source,
    destination,
    foreground_width=980,
    y_expression="(H-h)/2",
    foreground_blur=0,
    dark=-0.08
):
    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    destination.unlink(
        missing_ok=True
    )

    fg_filters = (
        f"scale={foreground_width}:-2,"
        f"eq=brightness={dark}:"
        "saturation=0.82"
    )

    if foreground_blur > 0:
        fg_filters += (
            f",gblur=sigma={foreground_blur}"
        )

    # FFmpeg filtergraph uses commas as filter separators.
    # Escape commas inside dynamic overlay expressions.
    safe_y_expression = str(y_expression).replace(",", r"\,")

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
        + fg_filters
        + "[fg2];"
        "[bg2][fg2]"
        f"overlay=(W-w)/2:{safe_y_expression},"
        "format=yuv420p"
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

    if not destination.exists():
        raise RuntimeError(
            "vertical_context_failed"
        )

    return {
        "sandbox_path":
            str(destination),

        "sha256":
            sha256(destination),

        "bytes":
            destination.stat().st_size,

        "family":
            "IMAGE",

        "info":
            media_info(
                destination
            ),
    }


def case_frame(
    source_video,
    timestamp,
    destination
):
    destination.unlink(
        missing_ok=True
    )

    fc = (
        "[0:v]split=2[bg][fg];"
        "[bg]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "gblur=sigma=30,"
        "eq=brightness=-0.13:"
        "saturation=0.55"
        "[bg2];"
        "[fg]"
        "scale=1000:-2,"
        "eq=brightness=-0.06:"
        "saturation=0.75"
        "[fg2];"
        "[bg2][fg2]"
        "overlay=(W-w)/2:(H-h)/2,"
        "format=yuv420p"
    )

    run([
        "ffmpeg",
        "-y",
        "-ss",
        f"{timestamp:.3f}",
        "-i",
        str(source_video),
        "-filter_complex",
        fc,
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(destination),
    ])

    return {
        "sandbox_path":
            str(destination),

        "sha256":
            sha256(destination),

        "bytes":
            destination.stat().st_size,

        "family":
            "IMAGE",

        "info":
            media_info(
                destination
            ),
    }


def abstract_medication(
    source,
    destination
):
    destination.unlink(
        missing_ok=True
    )

    # Intentionally destroys readable labels.
    # This asset is illustrative only.
    fc = (
        "[0:v]split=2[bg][fg];"
        "[bg]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "gblur=sigma=34,"
        "eq=brightness=-0.18:"
        "saturation=0.42"
        "[bg2];"
        "[fg]"
        "scale=940:-2,"
        "gblur=sigma=12,"
        "eq=brightness=-0.05:"
        "contrast=1.05:"
        "saturation=0.38"
        "[fg2];"
        "[bg2][fg2]"
        "overlay=(W-w)/2:(H-h)/2,"
        "format=yuv420p"
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

    return {
        "sandbox_path":
            str(destination),

        "sha256":
            sha256(destination),

        "bytes":
            destination.stat().st_size,

        "family":
            "IMAGE",

        "info":
            media_info(
                destination
            ),

        "labels_intentionally_obscured":
            True,

        "epistemic_role":
            "ILLUSTRATIVE_MEDICATION_BROLL",
    }


def vertical_rooftop_candidate(
    source,
    destination
):
    return vertical_context_image(
        source,
        destination,
        foreground_width=1080,
        y_expression="(H-h)/2",
        foreground_blur=0,
        dark=-0.06
    )


def manifest_entry(
    manifest,
    scene
):
    return (
        manifest[
            "scenes"
        ][
            str(scene)
        ]
    )


def activate_asset(
    manifest,
    scene,
    asset,
    title,
    license_name,
    usage,
    source_title=None
):
    entry = manifest_entry(
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
        "mode"
    ] = (
        "VI800_TRUTH_SAFE_OVERRIDE"
    )

    entry[
        "epistemic_usage"
    ] = usage

    entry[
        "source_title"
    ] = source_title


def evaluate():
    if not PARENT_MANIFEST.exists():
        raise RuntimeError(
            "vi720_manifest_missing"
        )

    parent = json.loads(
        PARENT_MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    manifest = copy.deepcopy(
        parent
    )

    manifest[
        "version"
    ] = VERSION

    manifest[
        "parent_manifest"
    ] = str(
        PARENT_MANIFEST
    )

    vi330 = load_gate(
        VI330
    )

    vi720 = load_gate(
        VI720
    )

    case = (
        vi330.get(
            "candidate"
        )
        or {}
    )

    case_path = Path(
        case.get(
            "sandbox_path"
        )
        or ""
    )

    if not case_path.exists():
        raise RuntimeError(
            "verified_case_video_missing"
        )

    if (
        case.get(
            "sha256"
        )
        and sha256(
            case_path
        )
        != case[
            "sha256"
        ]
    ):
        raise RuntimeError(
            "verified_case_video_hash_mismatch"
        )

    case_info = media_info(
        case_path
    )

    case_duration = float(
        case_info.get(
            "duration"
        )
        or 0
    )

    if case_duration < 3:
        raise RuntimeError(
            "verified_case_video_too_short"
        )

    scene2 = manifest_entry(
        manifest,
        2
    )

    facade_path = Path(
        scene2.get(
            "original_path"
        )
        or ""
    )

    if not facade_path.exists():
        raise RuntimeError(
            "verified_hotel_cecil_facade_missing"
        )

    facade_meta = commons_exact(
        HOTEL_CECIL_TITLE
    )

    facade_license = (
        (
            facade_meta
            or {}
        ).get(
            "license"
        )
        or "CC BY-SA 3.0"
    )

    # --------------------------------------------------
    # SCENE 5
    # Remove any remaining artistic/generic face.
    # Use authentic case footage as context only.
    # --------------------------------------------------

    asset5 = case_frame(
        case_path,
        min(
            case_duration * 0.36,
            max(
                0.1,
                case_duration - 0.2
            )
        ),
        WORK /
        "scene_05_authentic_case_context.jpg"
    )

    activate_asset(
        manifest,
        5,
        asset5,
        (
            "Elisa Lam elevator footage "
            "- contextual frame"
        ),
        case.get(
            "license"
        )
        or "Public domain",
        (
            "AUTHENTIC_CASE_CONTEXT_"
            "NOT_EXACT_NARRATED_MOMENT"
        ),
        "File:Elisa Lam elevator video.webm"
    )

    # --------------------------------------------------
    # SCENE 6
    # Different verified source to avoid four
    # consecutive frames from the same surveillance clip.
    # --------------------------------------------------

    asset6 = vertical_context_image(
        facade_path,
        WORK /
        "scene_06_verified_hotel_context.jpg",
        foreground_width=1040,
        y_expression="(H-h)/2",
        foreground_blur=0,
        dark=-0.07
    )

    activate_asset(
        manifest,
        6,
        asset6,
        (
            "Hotel Cecil verified facade "
            "- contextual treatment"
        ),
        facade_license,
        (
            "VERIFIED_HOTEL_CONTEXT_"
            "NOT_EVENT_REENACTMENT"
        ),
        HOTEL_CECIL_TITLE
    )

    # --------------------------------------------------
    # SCENE 9
    # Existing medicine source is licensed but had
    # an unsafe readable product label. Destroy text.
    # --------------------------------------------------

    scene9 = manifest_entry(
        manifest,
        9
    )

    med_source = Path(
        scene9.get(
            "canary_path"
        )
        or ""
    )

    if not med_source.exists():
        raise RuntimeError(
            "scene9_medication_source_missing"
        )

    asset9 = abstract_medication(
        med_source,
        WORK /
        "scene_09_medication_illustrative_safe.jpg"
    )

    activate_asset(
        manifest,
        9,
        asset9,
        (
            "Generic medication "
            "- intentionally defocused"
        ),
        scene9.get(
            "license"
        )
        or "CC BY 4.0",
        "ILLUSTRATIVE_MEDICATION_BROLL",
        scene9.get(
            "title"
        )
    )

    # --------------------------------------------------
    # SCENE 10 / 11
    # Only use rooftop media if Hotel Cecil + rooftop
    # are both evidenced by the candidate metadata.
    # Otherwise use verified facade context.
    # --------------------------------------------------

    roof_candidate, roof_audit = (
        find_verified_rooftop()
    )

    roof_download = None
    roof_verified = False

    if roof_candidate:
        try:
            suffix = (
                ".png"
                if str(
                    roof_candidate.get(
                        "mime"
                    )
                ).lower()
                == "image/png"
                else ".jpg"
            )

            raw_path = (
                WORK /
                (
                    "verified_hotel_cecil_rooftop"
                    + suffix
                )
            )

            roof_download = (
                download_candidate(
                    roof_candidate,
                    raw_path
                )
            )

            roof_verified = True

        except Exception:
            roof_verified = False

    if roof_verified:
        roof_path = Path(
            roof_download[
                "path"
            ]
        )

        asset10 = (
            vertical_rooftop_candidate(
                roof_path,
                WORK /
                "scene_10_verified_rooftop.jpg"
            )
        )

        activate_asset(
            manifest,
            10,
            asset10,
            roof_candidate[
                "title"
            ],
            roof_candidate[
                "license"
            ],
            "VERIFIED_HOTEL_CECIL_ROOFTOP_CONTEXT",
            roof_candidate[
                "title"
            ]
        )

        # Scene 11 intentionally uses hotel facade
        # so we do not repeat the same roof asset.
        asset11 = vertical_context_image(
            facade_path,
            WORK /
            "scene_11_verified_hotel_context.jpg",
            foreground_width=1160,
            y_expression="(H-h)/2-180",
            foreground_blur=0,
            dark=-0.11
        )

        activate_asset(
            manifest,
            11,
            asset11,
            "Hotel Cecil verified facade - upper context",
            facade_license,
            (
                "VERIFIED_HOTEL_CONTEXT_"
                "NOT_ROOFTOP_EVIDENCE"
            ),
            HOTEL_CECIL_TITLE
        )

    else:
        asset10 = vertical_context_image(
            facade_path,
            WORK /
            "scene_10_hotel_context_safe.jpg",
            foreground_width=1100,
            y_expression="(H-h)/2-220",
            foreground_blur=0,
            dark=-0.08
        )

        activate_asset(
            manifest,
            10,
            asset10,
            (
                "Hotel Cecil verified facade "
                "- contextual upper-building view"
            ),
            facade_license,
            (
                "VERIFIED_HOTEL_CONTEXT_"
                "ROOFTOP_NOT_CLAIMED"
            ),
            HOTEL_CECIL_TITLE
        )

        asset11 = vertical_context_image(
            facade_path,
            WORK /
            "scene_11_hotel_context_safe.jpg",
            foreground_width=940,
            y_expression="(H-h)/2+80",
            foreground_blur=0,
            dark=-0.13
        )

        activate_asset(
            manifest,
            11,
            asset11,
            (
                "Hotel Cecil verified facade "
                "- contextual second treatment"
            ),
            facade_license,
            (
                "VERIFIED_HOTEL_CONTEXT_"
                "ROOFTOP_NOT_CLAIMED"
            ),
            HOTEL_CECIL_TITLE
        )

    # Scene 12 from VI720 remains verified contextual CTA.
    manifest_entry(
        manifest,
        12
    )[
        "epistemic_usage"
    ] = (
        "VERIFIED_HOTEL_CONTEXT_CTA_"
        "NOT_AUTOPSY_DOCUMENT"
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
        "vi800_truth_policy"
    ] = {
        "artistic_face":
            "REMOVED",

        "generic_identifiable_human":
            "DISALLOWED",

        "medication_labels":
            "INTENTIONALLY_OBSCURED",

        "generic_rooftop_as_case_evidence":
            "DISALLOWED",

        "verified_rooftop_found":
            roof_verified,

        "rooftop_fallback":
            (
                None
                if roof_verified
                else "VERIFIED_HOTEL_FACADE_CONTEXT"
            ),

        "scene12_fake_document":
            "DISALLOWED",

        "case_video":
            "AUTHENTIC_ARCHIVAL_CONTEXT",

        "automatic_production_replace":
            False,
    }

    # Active asset collision audit.
    hashes = {}

    for scene in active:
        entry = manifest_entry(
            manifest,
            scene
        )

        digest = entry.get(
            "expected_sha256"
        )

        if digest:
            hashes.setdefault(
                digest,
                []
            ).append(
                scene
            )

    duplicates = {
        digest:
            scenes
        for digest, scenes
        in hashes.items()
        if len(scenes) > 1
    }

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


    credit_titles = {}

    for scene in active:
        entry = manifest_entry(
            manifest,
            scene
        )

        source_title = (
            entry.get(
                "source_title"
            )
            or entry.get(
                "title"
            )
        )

        if (
            source_title
            and str(
                source_title
            ).startswith(
                "File:"
            )
        ):
            credit_titles[
                source_title
            ] = None

    credit_titles[
        HOTEL_CECIL_TITLE
    ] = None

    credits_metadata = {}

    for title in (
        credit_titles
    ):
        credits_metadata[
            title
        ] = commons_exact(
            title
        )

    lines = [
        "SHORTAUTOPRO VI800 - MEDIA CREDITS",
        "================================",
        "",
        (
            "Nota: algumas imagens são usadas como "
            "contexto ou B-roll ilustrativo e não como "
            "registro exato do momento narrado."
        ),
        "",
    ]

    for title, metadata in (
        credits_metadata.items()
    ):
        metadata = (
            metadata
            or {}
        )

        lines.extend([
            title,
            (
                "License: "
                + str(
                    metadata.get(
                        "license"
                    )
                    or "See source page"
                )
            ),
            (
                "Artist/Author: "
                + str(
                    metadata.get(
                        "artist"
                    )
                    or "See source page"
                )
            ),
            (
                "Source: "
                + str(
                    metadata.get(
                        "page_url"
                    )
                    or (
                        "https://commons.wikimedia.org/wiki/"
                        + quote(
                            title.replace(
                                " ",
                                "_"
                            ),
                            safe=":/_()"
                        )
                    )
                )
            ),
            "",
        ])

    lines.extend([
        "ARCHIVAL CASE FOOTAGE",
        "File:Elisa Lam elevator video.webm",
        (
            "License: "
            + str(
                case.get(
                    "license"
                )
                or "Public domain"
            )
        ),
        (
            "Usage: authentic archival context; "
            "derived frames are not claimed as "
            "the exact narrated moment unless explicitly stated."
        ),
        "",
        "SCENE 9",
        (
            "Generic medication image is used only as "
            "illustrative B-roll. Original visible labels were "
            "deliberately obscured."
        ),
    ])

    CREDITS.write_text(
        "\n".join(
            lines
        ),
        encoding="utf-8"
    )

    blockers = []

    required = {
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

    if not required.issubset(
        set(active)
    ):
        blockers.append(
            "required_truth_safe_portfolio_incomplete"
        )

    if duplicates:
        blockers.append(
            "active_asset_hash_collision"
        )

    if not asset9.get(
        "labels_intentionally_obscured"
    ):
        blockers.append(
            "medication_label_not_obscured"
        )

    ready = not blockers

    report = {
        "version":
            VERSION,

        "status":
            (
                "VI800_PRODUCTION_CANDIDATE_READY"
                if ready
                else "HOLD"
            ),

        "short_id":
            SHORT_ID,

        "canary_ready":
            ready,

        "active_override_scenes":
            active,

        "truth_repairs": {
            "scene5":
                "AUTHENTIC_CASE_CONTEXT",

            "scene6":
                "VERIFIED_HOTEL_CONTEXT",

            "scene9":
                "ILLUSTRATIVE_MEDICATION_LABEL_OBSCURED",

            "scene10":
                (
                    "VERIFIED_ROOFTOP"
                    if roof_verified
                    else "VERIFIED_HOTEL_CONTEXT"
                ),

            "scene11":
                "VERIFIED_HOTEL_CONTEXT",

            "scene12":
                "VERIFIED_CONTEXT_CTA_NOT_DOCUMENT",
        },

        "verified_rooftop_found":
            roof_verified,

        "verified_rooftop_candidate":
            roof_candidate,

        "rooftop_search_audit":
            roof_audit,

        "active_duplicate_hashes":
            duplicates,

        "manifest": {
            "path":
                str(MANIFEST),

            "sha256":
                sha256(MANIFEST),
        },

        "credits": {
            "path":
                str(CREDITS),

            "sha256":
                sha256(CREDITS),
        },

        "blockers":
            blockers,

        "warnings": (
            []
            if roof_verified
            else [
                (
                    "verified_rooftop_not_found_"
                    "using_verified_hotel_context_instead"
                )
            ]
        ),

        "production_media_mutated":
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
        " VI800 PRODUCTION READINESS"
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
        r["canary_ready"]
    )

    print(
        "ACTIVE OVERRIDES:",
        r[
            "active_override_scenes"
        ]
    )

    print()
    print(
        "===== TRUTH REPAIRS ====="
    )

    for scene, action in (
        r[
            "truth_repairs"
        ].items()
    ):
        print(
            scene.upper(),
            "=",
            action
        )

    print()
    print(
        "VERIFIED ROOFTOP FOUND:",
        r[
            "verified_rooftop_found"
        ]
    )

    if r[
        "verified_rooftop_candidate"
    ]:
        print(
            "ROOFTOP:",
            r[
                "verified_rooftop_candidate"
            ][
                "title"
            ]
        )

    print()
    print(
        "DUPLICATE HASHES:",
        r[
            "active_duplicate_hashes"
        ]
    )

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
