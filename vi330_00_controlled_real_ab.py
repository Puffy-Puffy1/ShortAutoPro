#!/usr/bin/env python3

import hashlib
import json
import os
import struct
from pathlib import Path

import requests


VERSION = "330.00"

BASE = Path.home() / "ShortAutoPro"
LOG = BASE / "logs/producao"

VI320 = (
    LOG /
    "vi320_00_deep_context_truth_latest.json"
)

OUT = (
    LOG /
    "vi330_00_controlled_real_ab_latest.json"
)

SANDBOX = (
    BASE /
    "temp" /
    "vi330_real_ab"
)

COMMONS = (
    "https://commons.wikimedia.org/w/api.php"
)

HEADERS = {
    "User-Agent":
        "ShortAutoPro/330.00 "
        "(controlled real media validation)"
}

MAX_DOWNLOAD = 80 * 1024 * 1024

WEBM_MAGIC = (
    b"\x1a\x45\xdf\xa3"
)


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


def media_family(path):
    ext = path.suffix.lower()

    if ext in {
        ".mp4",
        ".webm",
        ".mov",
        ".m4v",
        ".ogv",
        ".mpeg",
        ".mpg",
    }:
        return "VIDEO"

    if ext in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }:
        return "IMAGE"

    return "UNKNOWN"


def find_current():
    folder = (
        BASE /
        "imagens" /
        "short_2026-09-01_1433"
    )

    matches = sorted(
        folder.glob(
            "scene_01.*"
        )
    )

    if not matches:
        raise RuntimeError(
            "scene_01_media_missing"
        )

    return matches[0]


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
        with open(path, "rb") as f:
            data = f.read(24)

        if (
            len(data) >= 24
            and data[:8]
            == b"\x89PNG\r\n\x1a\n"
        ):
            w, h = struct.unpack(
                ">II",
                data[16:24]
            )

            return w, h

    except Exception:
        pass

    return None


def current_dimensions(path):
    if (
        path.suffix.lower()
        in {
            ".jpg",
            ".jpeg",
        }
    ):
        return jpeg_size(path)

    if (
        path.suffix.lower()
        == ".png"
    ):
        return png_size(path)

    return None


def commons_metadata(title):
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

    r = requests.get(
        COMMONS,
        params=params,
        headers=HEADERS,
        timeout=30
    )

    r.raise_for_status()

    data = r.json()

    pages = (
        data.get("query", {})
        .get("pages", [])
    )

    if not pages:
        raise RuntimeError(
            "commons_page_missing"
        )

    page = pages[0]

    infos = (
        page.get("imageinfo")
        or []
    )

    if not infos:
        raise RuntimeError(
            "commons_imageinfo_missing"
        )

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

        if isinstance(
            value,
            dict
        ):
            return str(
                value.get("value")
                or ""
            )

        return str(
            value or ""
        )

    return {
        "title":
            page.get("title")
            or title,

        "url":
            info.get("url"),

        "mime":
            str(
                info.get("mime")
                or ""
            ).lower(),

        "mediatype":
            str(
                info.get("mediatype")
                or ""
            ).lower(),

        "width":
            int(
                info.get("width")
                or 0
            ),

        "height":
            int(
                info.get("height")
                or 0
            ),

        "declared_size":
            int(
                info.get("size")
                or 0
            ),

        "license":
            mv("LicenseShortName"),

        "usage_terms":
            mv("UsageTerms"),

        "description":
            mv("ImageDescription"),
    }


def license_score(
    license_name,
    usage
):
    text = (
        str(license_name or "")
        + " "
        + str(usage or "")
    ).lower()

    if (
        "public domain"
        in text
        or "cc0"
        in text
    ):
        return 100

    if (
        "cc by-sa"
        in text
        or "cc-by-sa"
        in text
    ):
        return 92

    if (
        "cc by"
        in text
        or "cc-by"
        in text
    ):
        return 90

    return 45


def controlled_download(
    url,
    destination
):
    partial = Path(
        str(destination)
        + ".part"
    )

    partial.unlink(
        missing_ok=True
    )

    with requests.get(
        url,
        headers=HEADERS,
        timeout=45,
        stream=True
    ) as r:
        r.raise_for_status()

        content_type = str(
            r.headers.get(
                "Content-Type"
            )
            or ""
        ).lower()

        content_length = (
            r.headers.get(
                "Content-Length"
            )
        )

        if content_length:
            try:
                declared = int(
                    content_length
                )

                if declared > MAX_DOWNLOAD:
                    raise RuntimeError(
                        "candidate_too_large"
                    )

            except ValueError:
                pass

        total = 0

        with open(
            partial,
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
        partial.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            "candidate_too_small"
        )

    os.replace(
        partial,
        destination
    )

    return {
        "bytes":
            total,

        "content_type":
            content_type,
    }


def magic_check(path):
    with open(path, "rb") as f:
        first = f.read(4)

    return {
        "first4_hex":
            first.hex(),

        "webm_ebml":
            first
            == WEBM_MAGIC,
    }


def evaluate():
    vi320 = load_gate(
        VI320
    )

    if 1 not in (
        vi320.get(
            "deep_ready_scenes"
        )
        or []
    ):
        raise RuntimeError(
            "scene_1_not_deep_ready"
        )

    winner = None

    for scene in (
        vi320.get(
            "scene_decisions"
        )
        or []
    ):
        if (
            int(
                scene.get(
                    "scene",
                    -1
                )
            )
            == 1
        ):
            winner = scene.get(
                "best"
            )
            break

    if not winner:
        raise RuntimeError(
            "scene_1_winner_missing"
        )

    if (
        winner.get(
            "decision"
        )
        != "DEEP_TRUE_CANDIDATE"
    ):
        raise RuntimeError(
            "winner_not_deep_true"
        )

    title = str(
        winner.get("title")
        or ""
    )

    if (
        "Elisa Lam elevator video"
        not in title
    ):
        raise RuntimeError(
            "unexpected_winner"
        )

    commons = commons_metadata(
        title
    )

    mime_ok = (
        commons["mime"]
        .startswith(
            "video/"
        )
    )

    mediatype_ok = (
        commons["mediatype"]
        == "video"
    )

    if not (
        mime_ok
        or mediatype_ok
    ):
        raise RuntimeError(
            "commons_not_video"
        )

    if not commons.get(
        "url"
    ):
        raise RuntimeError(
            "candidate_url_missing"
        )

    SANDBOX.mkdir(
        parents=True,
        exist_ok=True
    )

    destination = (
        SANDBOX /
        "scene_01_elisa_lam_elevator.webm"
    )

    download = controlled_download(
        commons["url"],
        destination
    )

    magic = magic_check(
        destination
    )

    actual_size = (
        destination
        .stat()
        .st_size
    )

    candidate_hash = sha256(
        destination
    )

    current = find_current()

    current_hash = sha256(
        current
    )

    current_family = (
        media_family(
            current
        )
    )

    current_size = (
        current_dimensions(
            current
        )
    )

    if current_size:
        cw, ch = current_size
        current_pixels = cw * ch

    else:
        cw = 0
        ch = 0
        current_pixels = 0

    candidate_pixels = (
        commons["width"]
        * commons["height"]
    )

    lic = license_score(
        commons["license"],
        commons["usage_terms"]
    )

    inherited_truth = {
        "direct_case_truth":
            bool(
                (
                    winner.get(
                        "context_truth"
                    )
                    or {}
                ).get(
                    "direct_case_truth"
                )
            ),

        "context_entity":
            bool(
                (
                    winner.get(
                        "gates"
                    )
                    or {}
                ).get(
                    "context_entity"
                )
            ),

        "scene_role":
            bool(
                (
                    winner.get(
                        "gates"
                    )
                    or {}
                ).get(
                    "scene_role"
                )
            ),

        "wrong_geo_absent":
            bool(
                (
                    winner.get(
                        "gates"
                    )
                    or {}
                ).get(
                    "wrong_geo_absent"
                )
            ),
    }

    archival_low_res = (
        candidate_pixels
        > 0
        and candidate_pixels
        < 500_000
    )

    # Authentic archival CCTV footage may be
    # lower resolution than modern still media.
    # Low resolution creates a warning,
    # not an automatic semantic rejection.
    technical_valid = (
        commons["width"] >= 240
        and commons["height"] >= 180
        and actual_size >= 100_000
    )

    size_consistent = (
        commons[
            "declared_size"
        ] <= 0
        or abs(
            actual_size
            - commons[
                "declared_size"
            ]
        )
        <= max(
            4096,
            int(
                commons[
                    "declared_size"
                ]
                * 0.01
            )
        )
    )

    content_type_ok = (
        "video" in (
            download[
                "content_type"
            ]
        )
        or "webm" in (
            download[
                "content_type"
            ]
        )
        or magic[
            "webm_ebml"
        ]
    )

    gates = {
        "vi320_deep_truth":
            all(
                inherited_truth.values()
            ),

        "commons_video":
            mime_ok
            or mediatype_ok,

        "webm_signature":
            magic[
                "webm_ebml"
            ],

        "http_content":
            content_type_ok,

        "size_consistent":
            size_consistent,

        "technical_minimum":
            technical_valid,

        "license":
            lic >= 80,

        "unique_from_current":
            candidate_hash
            != current_hash,
    }

    passed = all(
        gates.values()
    )

    if passed:
        decision = (
            "READY_FOR_SHADOW_OVERRIDE_TEST"
        )

    else:
        decision = (
            "REJECT_REAL_AB"
        )

    warnings = []

    if archival_low_res:
        warnings.append(
            "authentic_archival_low_resolution"
        )

    if (
        current_family
        != "VIDEO"
    ):
        warnings.append(
            "cross_media_image_to_video"
        )

    if (
        current_pixels
        and candidate_pixels
        and candidate_pixels
        < current_pixels
    ):
        warnings.append(
            "candidate_lower_native_pixel_count"
        )

    # VI320 produced 105 due a bonus.
    # VI330 formally normalizes this scale.
    normalized_truth_score = min(
        100,
        max(
            0,
            int(
                winner.get(
                    "deep_score"
                )
                or 0
            )
        )
    )

    report = {
        "version":
            VERSION,

        "status":
            "VI330_CONTROLLED_REAL_AB_CERTIFIED",

        "short_id":
            vi320.get(
                "short_id"
            ),

        "scene":
            1,

        "historical_corrections": {
            "vi320_score_105":
                "NORMALIZED_TO_100",

            "semantic_gain":
                "NOT_COMPUTED_AGAINST_UNKNOWN_CURRENT_PROVENANCE",

            "low_resolution_archival_media":
                "WARNING_NOT_AUTOMATIC_REJECTION",

            "automatic_replace":
                False,
        },

        "current": {
            "path":
                str(current),

            "family":
                current_family,

            "sha256":
                current_hash,

            "bytes":
                current.stat().st_size,

            "width":
                cw,

            "height":
                ch,

            "pixels":
                current_pixels,

            "provenance":
                "UNVERIFIED",
        },

        "candidate": {
            "title":
                commons[
                    "title"
                ],

            "sandbox_path":
                str(
                    destination
                ),

            "family":
                "VIDEO",

            "mime":
                commons[
                    "mime"
                ],

            "mediatype":
                commons[
                    "mediatype"
                ],

            "width":
                commons[
                    "width"
                ],

            "height":
                commons[
                    "height"
                ],

            "pixels":
                candidate_pixels,

            "declared_bytes":
                commons[
                    "declared_size"
                ],

            "actual_bytes":
                actual_size,

            "sha256":
                candidate_hash,

            "http_content_type":
                download[
                    "content_type"
                ],

            "magic":
                magic,

            "license":
                commons[
                    "license"
                ],

            "license_score":
                lic,

            "normalized_truth_score":
                normalized_truth_score,

            "archival_low_resolution":
                archival_low_res,
        },

        "inherited_truth":
            inherited_truth,

        "gates":
            gates,

        "decision":
            decision,

        "blockers":
            (
                []
                if passed
                else [
                    key
                    for key, value
                    in gates.items()
                    if not value
                ]
            ),

        "warnings":
            warnings,

        "network_executed":
            True,

        "controlled_download_executed":
            True,

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
        " VI330 CONTROLLED REAL CROSS-MEDIA A/B"
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

    print()
    print(
        "===== CURRENT ====="
    )

    c = r["current"]

    print(
        "PATH:",
        c["path"]
    )

    print(
        "FAMILY:",
        c["family"]
    )

    print(
        "DIMENSIONS:",
        c["width"],
        "x",
        c["height"]
    )

    print(
        "PIXELS:",
        c["pixels"]
    )

    print(
        "BYTES:",
        c["bytes"]
    )

    print(
        "SHA256:",
        c["sha256"]
    )

    print(
        "PROVENANCE:",
        c["provenance"]
    )

    print()
    print(
        "===== CANDIDATE ====="
    )

    x = r["candidate"]

    print(
        "TITLE:",
        x["title"]
    )

    print(
        "SANDBOX:",
        x["sandbox_path"]
    )

    print(
        "FAMILY:",
        x["family"]
    )

    print(
        "MIME:",
        x["mime"]
    )

    print(
        "DIMENSIONS:",
        x["width"],
        "x",
        x["height"]
    )

    print(
        "PIXELS:",
        x["pixels"]
    )

    print(
        "DECLARED BYTES:",
        x["declared_bytes"]
    )

    print(
        "ACTUAL BYTES:",
        x["actual_bytes"]
    )

    print(
        "SHA256:",
        x["sha256"]
    )

    print(
        "WEBM MAGIC:",
        x["magic"]
    )

    print(
        "LICENSE:",
        x["license"]
    )

    print(
        "TRUTH SCORE:",
        x[
            "normalized_truth_score"
        ]
    )

    print(
        "ARCHIVAL LOW RES:",
        x[
            "archival_low_resolution"
        ]
    )

    print()
    print(
        "INHERITED TRUTH:",
        r["inherited_truth"]
    )

    print(
        "GATES:",
        r["gates"]
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
