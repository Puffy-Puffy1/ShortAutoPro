#!/usr/bin/env python3

import json
import re
import time
import hashlib
from pathlib import Path
from urllib.parse import urlparse

import requests


VERSION = "16.00"

BASE = Path.home() / "ShortAutoPro"

VI14 = (
    BASE / "logs/producao/"
    "vi14_00_consensus_candidate_gate_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi16_00_real_candidate_discovery_latest.json"
)

COMMONS_API = (
    "https://commons.wikimedia.org/w/api.php"
)

HEADERS = {
    "User-Agent":
        "ShortAutoPro/16.00 "
        "(read-only candidate discovery)"
}

MAX_SCENES = 3
MAX_RESULTS_PER_QUERY = 12
MAX_QUERIES_PER_SCENE = 4

MIN_REAL_GAIN = 7.0
MIN_CANDIDATE_SCORE = 68.0


STOP = {
    "the", "and", "for", "with",
    "from", "into", "this", "that",
    "person", "image", "photo",
    "photograph", "documentary",
    "editorial", "cinematic",
    "medium", "wide", "close",
    "shot", "clear",
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


def tokens(text):
    return {
        x.lower()
        for x in re.findall(
            r"[A-Za-zÀ-ÿ0-9'-]+",
            str(text or "")
        )
        if (
            len(x) >= 3
            and x.lower() not in STOP
        )
    }


def clean_query(text):
    remove = {
        "portrait", "medium",
        "wide", "close",
        "shot", "clear",
        "cinematic",
        "documentary",
        "editorial",
    }

    output = []
    seen = set()

    for word in re.findall(
        r"[A-Za-zÀ-ÿ0-9'-]+",
        str(text or "")
    ):
        low = word.lower()

        if low in remove:
            continue

        if low in seen:
            continue

        seen.add(low)
        output.append(word)

    return " ".join(output)


def query_variants(item):
    raw = clean_query(
        item.get("query") or ""
    )

    words = raw.split()

    variants = [
        raw,
        " ".join(words[:7]),
        " ".join(words[:5]),
        " ".join(words[:3]),
    ]

    result = []
    seen = set()

    for value in variants:
        value = value.strip()

        if not value:
            continue

        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result[
        :MAX_QUERIES_PER_SCENE
    ]


def commons_search(query):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit":
            MAX_RESULTS_PER_QUERY,
        "prop": "imageinfo",
        "iiprop":
            "url|size|mime|extmetadata",
        "format": "json",
        "formatversion": 2,
    }

    response = requests.get(
        COMMONS_API,
        params=params,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    return (
        data.get("query", {})
        .get("pages", [])
    )


def strip_html(text):
    return re.sub(
        r"<[^>]+>",
        " ",
        str(text or "")
    )


def meta_value(meta, key):
    value = (
        meta.get(key)
        or {}
    )

    if isinstance(value, dict):
        return (
            value.get("value")
            or ""
        )

    return str(value or "")


def license_score(meta):
    license_name = (
        meta_value(
            meta,
            "LicenseShortName"
        )
        .lower()
    )

    usage = (
        meta_value(
            meta,
            "UsageTerms"
        )
        .lower()
    )

    text = (
        license_name
        + " "
        + usage
    )

    if (
        "public domain" in text
        or "cc0" in text
    ):
        return 100

    if (
        "cc by-sa" in text
        or "cc-by-sa" in text
    ):
        return 92

    if (
        "cc by" in text
        or "cc-by" in text
    ):
        return 90

    if "creative commons" in text:
        return 82

    return 45


def resolution_score(width, height):
    pixels = (
        width * height
    )

    if pixels >= 8_000_000:
        return 100

    if pixels >= 4_000_000:
        return 94

    if pixels >= 2_000_000:
        return 86

    if pixels >= 1_000_000:
        return 75

    if pixels >= 500_000:
        return 58

    return 35


def vertical_fitness(
    width,
    height,
    ideal_shot
):
    if not width or not height:
        return 30

    ratio = (
        width / height
    )

    # Vertical source is advantageous
    # for 9:16 shorts.
    if ratio <= 0.80:
        score = 100

    elif ratio <= 1.05:
        score = 91

    elif ratio <= 1.35:
        score = 78

    elif ratio <= 1.65:
        score = 67

    else:
        score = 55

    if (
        ideal_shot == "wide"
        and ratio >= 1.25
    ):
        score += 8

    if (
        ideal_shot == "close_up"
        and ratio <= 1.20
    ):
        score += 5

    return min(
        100,
        score
    )


def semantic_score(
    query,
    title,
    description
):
    q = tokens(query)

    target = tokens(
        str(title)
        + " "
        + strip_html(description)
    )

    if not q:
        return 0

    shared = (
        q & target
    )

    coverage = (
        len(shared)
        / len(q)
    )

    title_tokens = tokens(
        title
    )

    title_overlap = (
        q & title_tokens
    )

    score = (
        coverage * 75
        + min(
            25,
            len(title_overlap)
            * 8
        )
    )

    if not shared:
        score = 0

    return min(
        100,
        round(score, 2)
    )


def normalize_candidate(
    page,
    query,
    ideal_shot
):
    info_list = (
        page.get("imageinfo")
        or []
    )

    if not info_list:
        return None

    info = info_list[0]

    mime = str(
        info.get("mime")
        or ""
    ).lower()

    if not mime.startswith(
        "image/"
    ):
        return None

    width = int(
        info.get("width")
        or 0
    )

    height = int(
        info.get("height")
        or 0
    )

    url = (
        info.get("url")
        or ""
    )

    if not url:
        return None

    meta = (
        info.get(
            "extmetadata"
        )
        or {}
    )

    title = (
        page.get("title")
        or ""
    )

    description = meta_value(
        meta,
        "ImageDescription"
    )

    semantic = semantic_score(
        query,
        title,
        description
    )

    resolution = resolution_score(
        width,
        height
    )

    crop = vertical_fitness(
        width,
        height,
        ideal_shot
    )

    license_quality = license_score(
        meta
    )

    score = (
        semantic * .45
        + resolution * .20
        + crop * .20
        + license_quality * .15
    )

    return {
        "id":
            hashlib.sha256(
                url.encode(
                    "utf-8"
                )
            ).hexdigest()[:16],

        "query":
            query,

        "title":
            title,

        "url":
            url,

        "description":
            strip_html(
                description
            )[:400],

        "width":
            width,

        "height":
            height,

        "mime":
            mime,

        "license":
            meta_value(
                meta,
                "LicenseShortName"
            ),

        "artist":
            strip_html(
                meta_value(
                    meta,
                    "Artist"
                )
            )[:200],

        "semantic_score":
            semantic,

        "resolution_score":
            resolution,

        "crop_score":
            crop,

        "license_score":
            license_quality,

        "candidate_score":
            round(
                score,
                2
            ),
    }


def discover_scene(item):
    all_candidates = []

    seen_urls = set()

    errors = []

    variants = query_variants(
        item
    )

    for query in variants:
        try:
            pages = commons_search(
                query
            )

        except Exception as exc:
            errors.append(
                type(exc).__name__
                + ": "
                + str(exc)[:200]
            )

            continue

        for page in pages:
            candidate = normalize_candidate(
                page,
                query,
                item.get(
                    "ideal_shot"
                )
            )

            if not candidate:
                continue

            url = candidate[
                "url"
            ]

            if url in seen_urls:
                continue

            seen_urls.add(url)

            all_candidates.append(
                candidate
            )

        # Do not hammer Commons.
        time.sleep(.8)

    all_candidates.sort(
        key=lambda x:
            x["candidate_score"],
        reverse=True
    )

    current = float(
        item.get(
            "current_score"
        )
        or 0
    )

    best = (
        all_candidates[0]
        if all_candidates
        else None
    )

    if best:
        real_gain = (
            best[
                "candidate_score"
            ]
            - current
        )
    else:
        real_gain = None

    if not best:
        decision = (
            "KEEP_CURRENT_NO_CANDIDATE"
        )

    elif (
        best["semantic_score"]
        < 25
    ):
        decision = (
            "KEEP_CURRENT_LOW_SEMANTIC_MATCH"
        )

    elif (
        best[
            "candidate_score"
        ]
        < MIN_CANDIDATE_SCORE
    ):
        decision = (
            "KEEP_CURRENT_LOW_CANDIDATE_SCORE"
        )

    elif (
        real_gain
        < MIN_REAL_GAIN
    ):
        decision = (
            "KEEP_CURRENT_REAL_GAIN_TOO_SMALL"
        )

    else:
        decision = (
            "READY_FOR_CONTROLLED_DOWNLOAD"
        )

    return {
        "scene":
            item.get("scene"),

        "provider":
            "WIKIMEDIA_COMMONS",

        "queries":
            variants,

        "candidate_count":
            len(
                all_candidates
            ),

        "current_score":
            round(
                current,
                2
            ),

        "best_candidate":
            best,

        "real_gain":
            (
                round(
                    real_gain,
                    2
                )
                if real_gain
                is not None
                else None
            ),

        "decision":
            decision,

        "top_candidates":
            all_candidates[:5],

        "errors":
            errors,

        "download_executed":
            False,
    }


def evaluate():
    vi14 = load_gate(
        VI14
    )

    if not vi14:
        raise RuntimeError(
            "vi14_report_missing"
        )

    approved = [
        x
        for x in (
            vi14.get(
                "decisions"
            )
            or []
        )
        if x.get(
            "action"
        ) in {
            "REAL_SEARCH_READY",
            "REAL_SEARCH_IDENTITY_LOCKED",
        }
    ]

    approved.sort(
        key=lambda x:
            x.get(
                "confidence",
                0
            ),
        reverse=True
    )

    approved = approved[
        :MAX_SCENES
    ]

    discoveries = []

    for item in approved:
        # Identity-locked scenes require
        # another gate before generic
        # visual discovery.
        if (
            item.get(
                "identity_mode"
            )
            == "NO_IDENTITY_INFERENCE"
        ):
            discoveries.append({
                "scene":
                    item.get(
                        "scene"
                    ),

                "decision":
                    "HOLD_IDENTITY_VERIFICATION",

                "candidate_count":
                    0,

                "download_executed":
                    False,
            })

            continue

        discoveries.append(
            discover_scene(
                item
            )
        )

    ready = [
        x["scene"]
        for x in discoveries
        if x.get(
            "decision"
        )
        == "READY_FOR_CONTROLLED_DOWNLOAD"
    ]

    blockers = []

    warnings = []

    if any(
        x.get(
            "download_executed"
        )
        for x in discoveries
    ):
        blockers.append(
            "download_side_effect_detected"
        )

    for x in discoveries:
        if x.get(
            "errors"
        ):
            warnings.append(
                "provider_errors_present"
            )
            break

    status = (
        "HOLD"
        if blockers
        else
        "VI16_REAL_CANDIDATE_DISCOVERY_CERTIFIED"
    )

    result = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            vi14.get(
                "short_id"
            ),

        "approved_scenes":
            [
                x.get(
                    "scene"
                )
                for x in approved
            ],

        "ready_for_controlled_download":
            ready,

        "discoveries":
            discoveries,

        "blockers":
            blockers,

        "warnings":
            sorted(
                set(
                    warnings
                )
            ),

        "network_executed":
            bool(approved),

        "automatic_download":
            False,

        "automatic_replace":
            False,

        "media_mutated":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "source_recovery":
            "SHADOW_ONLY",

        "full_active":
            False,
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUT.write_text(
        json.dumps(
            {
                "gate":
                    result
            },
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
        " VI16 REAL CANDIDATE DISCOVERY"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "APPROVED SCENES:",
        r["approved_scenes"]
    )

    print(
        "READY FOR CONTROLLED DOWNLOAD:",
        r[
            "ready_for_controlled_download"
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

    for item in r[
        "discoveries"
    ]:
        print(
            "SCENE:",
            item.get(
                "scene"
            )
        )

        print(
            " DECISION:",
            item.get(
                "decision"
            )
        )

        print(
            " CANDIDATES:",
            item.get(
                "candidate_count"
            )
        )

        print(
            " REAL GAIN:",
            item.get(
                "real_gain"
            )
        )

        best = item.get(
            "best_candidate"
        )

        if best:
            print(
                " BEST SCORE:",
                best[
                    "candidate_score"
                ]
            )

            print(
                " SEMANTIC:",
                best[
                    "semantic_score"
                ]
            )

            print(
                " RESOLUTION:",
                best[
                    "resolution_score"
                ]
            )

            print(
                " CROP:",
                best[
                    "crop_score"
                ]
            )

            print(
                " LICENSE:",
                best[
                    "license"
                ]
            )

            print(
                " TITLE:",
                best[
                    "title"
                ]
            )

        print()

    print(
        "NETWORK EXECUTED:",
        r["network_executed"]
    )

    print(
        "AUTOMATIC DOWNLOAD:",
        r["automatic_download"]
    )

    print(
        "AUTOMATIC REPLACE:",
        r["automatic_replace"]
    )

    print(
        "MEDIA MUTATED:",
        r["media_mutated"]
    )

    print(
        "FFMPEG EXECUTED:",
        r["ffmpeg_executed"]
    )

    print(
        "VIDEO GENERATED:",
        r["video_generated"]
    )
