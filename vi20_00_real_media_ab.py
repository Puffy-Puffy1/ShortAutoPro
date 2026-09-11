#!/usr/bin/env python3

import hashlib
import json
import mimetypes
import os
import shutil
import struct
import time
from pathlib import Path

import requests


VERSION = "20.00"

BASE = Path.home() / "ShortAutoPro"

VI16 = (
    BASE
    / "logs/producao/"
      "vi16_00_real_candidate_discovery_latest.json"
)

OUT = (
    BASE
    / "logs/producao/"
      "vi20_00_real_media_ab_latest.json"
)

SANDBOX = (
    BASE
    / "temp/"
      "vi20_candidate_sandbox"
)

ATTRIBUTION = (
    BASE
    / "credits/"
      "vi20_candidate_attribution.json"
)


MAX_DOWNLOAD_BYTES = 30 * 1024 * 1024

MIN_FILE_BYTES = 20_000

MIN_WIDTH = 640
MIN_HEIGHT = 640

MIN_FINAL_GAIN = 7.0
MIN_SEMANTIC = 30.0
MIN_RESOLUTION_SCORE = 65.0
MIN_CROP_SCORE = 50.0
MIN_LICENSE_SCORE = 75.0


HEADERS = {
    "User-Agent":
        "ShortAutoPro/20.00 "
        "(controlled read-only media validation)"
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


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(
                1024 * 1024
            )

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def safe_filename(scene, url, mime):
    ext = (
        mimetypes.guess_extension(
            mime or ""
        )
        or ""
    )

    if ext == ".jpe":
        ext = ".jpg"

    if ext not in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
    }:
        ext = ".img"

    token = hashlib.sha256(
        url.encode(
            "utf-8"
        )
    ).hexdigest()[:12]

    return (
        f"scene_{scene}_"
        f"{token}{ext}"
    )


def inspect_png(path):
    with open(path, "rb") as f:
        header = f.read(24)

    if (
        len(header) >= 24
        and header[:8]
        == b"\x89PNG\r\n\x1a\n"
    ):
        width, height = struct.unpack(
            ">II",
            header[16:24]
        )

        return (
            width,
            height
        )

    return None


def inspect_jpeg(path):
    with open(path, "rb") as f:
        data = f.read()

    if not data.startswith(
        b"\xff\xd8"
    ):
        return None

    i = 2

    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue

        marker = data[i + 1]

        if marker in {
            0xC0, 0xC1, 0xC2,
            0xC3, 0xC5, 0xC6,
            0xC7, 0xC9, 0xCA,
            0xCB, 0xCD, 0xCE,
            0xCF,
        }:
            height = int.from_bytes(
                data[i+5:i+7],
                "big"
            )

            width = int.from_bytes(
                data[i+7:i+9],
                "big"
            )

            return (
                width,
                height
            )

        if i + 4 > len(data):
            break

        length = int.from_bytes(
            data[i+2:i+4],
            "big"
        )

        if length < 2:
            break

        i += 2 + length

    return None


def inspect_image(path):
    result = inspect_png(
        path
    )

    if result:
        return {
            "format": "PNG",
            "width": result[0],
            "height": result[1],
        }

    result = inspect_jpeg(
        path
    )

    if result:
        return {
            "format": "JPEG",
            "width": result[0],
            "height": result[1],
        }

    return {
        "format": "UNKNOWN",
        "width": 0,
        "height": 0,
    }


def existing_media_hashes():
    hashes = {}

    root = (
        BASE
        / "imagens"
    )

    if not root.exists():
        return hashes

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        try:
            digest = sha256_file(
                path
            )
        except Exception:
            continue

        hashes[
            digest
        ] = str(path)

    return hashes


def controlled_download(candidate, scene):
    url = candidate.get(
        "url"
    )

    mime = candidate.get(
        "mime"
    )

    if not url:
        return {
            "status": "FAIL",
            "reason": "url_missing",
        }

    SANDBOX.mkdir(
        parents=True,
        exist_ok=True
    )

    filename = safe_filename(
        scene,
        url,
        mime
    )

    path = (
        SANDBOX
        / filename
    )

    if path.exists():
        path.unlink()

    try:
        with requests.get(
            url,
            headers=HEADERS,
            stream=True,
            timeout=30
        ) as response:

            response.raise_for_status()

            content_type = (
                response.headers.get(
                    "Content-Type"
                )
                or ""
            ).lower()

            if not content_type.startswith(
                "image/"
            ):
                return {
                    "status": "FAIL",
                    "reason":
                        "non_image_content_type",
                    "content_type":
                        content_type,
                }

            content_length = (
                response.headers.get(
                    "Content-Length"
                )
            )

            if content_length:
                try:
                    length = int(
                        content_length
                    )
                except Exception:
                    length = None

                if (
                    length
                    and length
                    > MAX_DOWNLOAD_BYTES
                ):
                    return {
                        "status": "FAIL",
                        "reason":
                            "file_too_large",
                    }

            written = 0

            with open(
                path,
                "wb"
            ) as f:

                for chunk in (
                    response.iter_content(
                        chunk_size=65536
                    )
                ):
                    if not chunk:
                        continue

                    written += len(
                        chunk
                    )

                    if (
                        written
                        > MAX_DOWNLOAD_BYTES
                    ):
                        f.close()

                        path.unlink(
                            missing_ok=True
                        )

                        return {
                            "status": "FAIL",
                            "reason":
                                "download_size_limit",
                        }

                    f.write(
                        chunk
                    )

    except Exception as exc:
        path.unlink(
            missing_ok=True
        )

        return {
            "status": "FAIL",
            "reason":
                type(exc).__name__
                + ": "
                + str(exc)[:250],
        }

    if not path.exists():
        return {
            "status": "FAIL",
            "reason":
                "file_missing_after_download",
        }

    size = path.stat().st_size

    if size < MIN_FILE_BYTES:
        return {
            "status": "FAIL",
            "reason":
                "file_too_small",
            "size": size,
        }

    info = inspect_image(
        path
    )

    digest = sha256_file(
        path
    )

    return {
        "status": "PASS",
        "path": str(path),
        "size": size,
        "sha256": digest,
        "format": info["format"],
        "width": info["width"],
        "height": info["height"],
        "content_type":
            content_type,
    }


def real_resolution_score(
    width,
    height
):
    pixels = (
        width * height
    )

    if pixels >= 8_000_000:
        return 100.0

    if pixels >= 4_000_000:
        return 94.0

    if pixels >= 2_000_000:
        return 86.0

    if pixels >= 1_000_000:
        return 75.0

    if pixels >= 500_000:
        return 58.0

    return 30.0


def real_crop_score(
    width,
    height,
    ideal_shot
):
    if (
        width <= 0
        or height <= 0
    ):
        return 0.0

    ratio = (
        width
        / height
    )

    if ratio <= .80:
        score = 100

    elif ratio <= 1.05:
        score = 92

    elif ratio <= 1.35:
        score = 80

    elif ratio <= 1.65:
        score = 68

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

    return float(
        min(
            100,
            score
        )
    )


def candidate_real_score(
    candidate,
    download,
    ideal_shot
):
    semantic = float(
        candidate.get(
            "semantic_score"
        )
        or 0
    )

    license_score = float(
        candidate.get(
            "license_score"
        )
        or 0
    )

    resolution = real_resolution_score(
        download.get(
            "width",
            0
        ),
        download.get(
            "height",
            0
        )
    )

    crop = real_crop_score(
        download.get(
            "width",
            0
        ),
        download.get(
            "height",
            0
        ),
        ideal_shot
    )

    total = (
        semantic * .45
        + resolution * .20
        + crop * .20
        + license_score * .15
    )

    return {
        "semantic":
            round(
                semantic,
                2
            ),

        "resolution":
            round(
                resolution,
                2
            ),

        "crop":
            round(
                crop,
                2
            ),

        "license":
            round(
                license_score,
                2
            ),

        "final_score":
            round(
                total,
                2
            ),
    }


def attribution_record(
    scene,
    candidate,
    download
):
    return {
        "scene":
            scene,

        "title":
            candidate.get(
                "title"
            ),

        "source_url":
            candidate.get(
                "url"
            ),

        "license":
            candidate.get(
                "license"
            ),

        "artist":
            candidate.get(
                "artist"
            ),

        "sha256":
            download.get(
                "sha256"
            ),

        "sandbox_path":
            download.get(
                "path"
            ),

        "downloaded_for":
            "controlled_candidate_validation",

        "automatic_replacement":
            False,
    }


def evaluate_candidate(
    discovery,
    current_hashes
):
    scene = discovery.get(
        "scene"
    )

    candidate = discovery.get(
        "best_candidate"
    )

    if not candidate:
        return {
            "scene": scene,
            "status": "REJECT",
            "reason":
                "best_candidate_missing",
        }

    download = controlled_download(
        candidate,
        scene
    )

    if download.get(
        "status"
    ) != "PASS":
        return {
            "scene": scene,
            "status": "REJECT",
            "reason":
                "download_validation_failed",
            "download":
                download,
        }

    duplicate_path = (
        current_hashes.get(
            download[
                "sha256"
            ]
        )
    )

    if duplicate_path:
        return {
            "scene": scene,
            "status": "REJECT",
            "reason":
                "candidate_duplicates_existing_media",
            "duplicate_of":
                duplicate_path,
            "download":
                download,
        }

    width = int(
        download.get(
            "width"
        )
        or 0
    )

    height = int(
        download.get(
            "height"
        )
        or 0
    )

    if (
        width < MIN_WIDTH
        or height < MIN_HEIGHT
    ):
        return {
            "scene": scene,
            "status": "REJECT",
            "reason":
                "real_dimensions_too_small",
            "download":
                download,
        }

    ideal_shot = discovery.get(
        "ideal_shot"
    )

    if not ideal_shot:
        ideal_shot = "wide"

    score = candidate_real_score(
        candidate,
        download,
        ideal_shot
    )

    current_score = float(
        discovery.get(
            "current_score"
        )
        or 0
    )

    final_gain = (
        score[
            "final_score"
        ]
        - current_score
    )

    gates = {
        "semantic":
            score["semantic"]
            >= MIN_SEMANTIC,

        "resolution":
            score["resolution"]
            >= MIN_RESOLUTION_SCORE,

        "crop":
            score["crop"]
            >= MIN_CROP_SCORE,

        "license":
            score["license"]
            >= MIN_LICENSE_SCORE,

        "gain":
            final_gain
            >= MIN_FINAL_GAIN,

        "unique_hash":
            duplicate_path
            is None,
    }

    passed = all(
        gates.values()
    )

    if passed:
        decision = (
            "READY_FOR_MANUAL_REPLACEMENT"
        )

        reason = (
            "real_ab_consensus_pass"
        )

    else:
        decision = "KEEP_CURRENT"

        failed = [
            key
            for key, ok
            in gates.items()
            if not ok
        ]

        reason = (
            "failed_gates:"
            + ",".join(
                failed
            )
        )

    return {
        "scene":
            scene,

        "status":
            "PASS",

        "decision":
            decision,

        "reason":
            reason,

        "current_score":
            round(
                current_score,
                2
            ),

        "candidate_score":
            score[
                "final_score"
            ],

        "final_gain":
            round(
                final_gain,
                2
            ),

        "scores":
            score,

        "gates":
            gates,

        "download":
            download,

        "candidate":
            candidate,

        "attribution":
            attribution_record(
                scene,
                candidate,
                download
            ),

        "production_media_mutated":
            False,
    }


def evaluate():
    vi16 = load_gate(
        VI16
    )

    if not vi16:
        raise RuntimeError(
            "vi16_report_missing"
        )

    ready = set(
        vi16.get(
            "ready_for_controlled_download"
        )
        or []
    )

    discoveries = [
        x
        for x in (
            vi16.get(
                "discoveries"
            )
            or []
        )
        if x.get(
            "scene"
        )
        in ready
    ]

    # Safety cap.
    discoveries = (
        discoveries[:3]
    )

    current_hashes = (
        existing_media_hashes()
    )

    results = []

    for discovery in discoveries:
        results.append(
            evaluate_candidate(
                discovery,
                current_hashes
            )
        )

        time.sleep(.5)

    ready_manual = [
        x["scene"]
        for x in results
        if x.get(
            "decision"
        )
        == "READY_FOR_MANUAL_REPLACEMENT"
    ]

    rejected = [
        x["scene"]
        for x in results
        if x.get(
            "decision"
        )
        != "READY_FOR_MANUAL_REPLACEMENT"
    ]

    attributions = [
        x["attribution"]
        for x in results
        if x.get(
            "attribution"
        )
    ]

    ATTRIBUTION.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    ATTRIBUTION.write_text(
        json.dumps(
            {
                "version":
                    VERSION,

                "records":
                    attributions,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    blockers = []

    warnings = []

    if any(
        x.get(
            "production_media_mutated"
        )
        for x in results
    ):
        blockers.append(
            "production_media_mutation_detected"
        )

    for result in results:
        if (
            result.get(
                "status"
            )
            == "REJECT"
        ):
            warnings.append(
                "candidate_validation_rejection"
            )
            break

    status = (
        "HOLD"
        if blockers
        else "VI20_REAL_MEDIA_AB_CERTIFIED"
    )

    report = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            vi16.get(
                "short_id"
            ),

        "input_ready_scenes":
            sorted(
                ready
            ),

        "evaluated_scenes":
            [
                x.get(
                    "scene"
                )
                for x in results
            ],

        "ready_for_manual_replacement":
            ready_manual,

        "rejected_scenes":
            rejected,

        "results":
            results,

        "sandbox":
            str(
                SANDBOX
            ),

        "attribution_manifest":
            str(
                ATTRIBUTION
            ),

        "blockers":
            blockers,

        "warnings":
            sorted(
                set(
                    warnings
                )
            ),

        "network_executed":
            bool(
                discoveries
            ),

        "controlled_download_executed":
            bool(
                discoveries
            ),

        "production_media_mutated":
            False,

        "automatic_replace":
            False,

        "renderer_activation":
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
        " VI20.00 REAL MEDIA A/B ENGINE"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "INPUT READY:",
        r[
            "input_ready_scenes"
        ]
    )

    print(
        "EVALUATED:",
        r[
            "evaluated_scenes"
        ]
    )

    print(
        "READY MANUAL:",
        r[
            "ready_for_manual_replacement"
        ]
    )

    print(
        "REJECTED:",
        r[
            "rejected_scenes"
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

    for x in r["results"]:
        print(
            "SCENE:",
            x.get(
                "scene"
            )
        )

        print(
            " STATUS:",
            x.get(
                "status"
            )
        )

        print(
            " DECISION:",
            x.get(
                "decision"
            )
        )

        print(
            " REASON:",
            x.get(
                "reason"
            )
        )

        print(
            " CURRENT:",
            x.get(
                "current_score"
            )
        )

        print(
            " CANDIDATE:",
            x.get(
                "candidate_score"
            )
        )

        print(
            " FINAL GAIN:",
            x.get(
                "final_gain"
            )
        )

        if x.get(
            "scores"
        ):
            print(
                " SCORES:",
                x["scores"]
            )

        if x.get(
            "gates"
        ):
            print(
                " GATES:",
                x["gates"]
            )

        if x.get(
            "download"
        ):
            d = x[
                "download"
            ]

            print(
                " REAL FILE:",
                d.get(
                    "path"
                )
            )

            print(
                " DIMENSIONS:",
                d.get(
                    "width"
                ),
                "x",
                d.get(
                    "height"
                )
            )

            print(
                " SHA256:",
                d.get(
                    "sha256"
                )
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

    print(
        "SOURCE RECOVERY:",
        r[
            "source_recovery"
        ]
    )
