#!/usr/bin/env python3
from short_id_runtime_v1 import resolve_short_id as _sap_resolve_short_id

import json
import hashlib
from pathlib import Path


VERSION = "230.00"

BASE = Path.home() / "ShortAutoPro"

VI225 = (
    BASE / "logs/producao/"
    "vi225_00_safe_family_fallback_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi230_00_current_vs_candidate_ab_latest.json"
)

SHORT_ID = _sap_resolve_short_id()
SCENE = 2

TARGET_RATIO = 9 / 16


def load_gate(path):
    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return data.get("gate", data)


def jpeg_size(path):
    import struct

    with open(path, "rb") as f:
        if f.read(2) != b"\xff\xd8":
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

            length_b = f.read(2)

            if len(length_b) != 2:
                return None

            length = struct.unpack(
                ">H",
                length_b
            )[0]

            if marker in {
                0xC0, 0xC1, 0xC2,
                0xC3, 0xC5, 0xC6,
                0xC7, 0xC9, 0xCA,
                0xCB, 0xCD, 0xCE,
                0xCF,
            }:
                data = f.read(5)

                h, w = struct.unpack(
                    ">HH",
                    data[1:5]
                )

                return w, h

            f.seek(
                length - 2,
                1
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


def aspect_score(w, h):
    if not w or not h:
        return 0.0

    ratio = w / h

    error = abs(
        ratio - TARGET_RATIO
    )

    score = (
        100
        - error * 180
    )

    return round(
        max(0, min(100, score)),
        2
    )


def relative_resolution_score(
    pixels,
    baseline_pixels
):
    if baseline_pixels <= 0:
        return 0.0

    ratio = (
        pixels
        / baseline_pixels
    )

    # Equal resolution = 90.
    # Better resolution can rise to 100.
    # Slightly lower resolution is not
    # automatically rejected.
    score = 90 * ratio

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


def evaluate():
    vi225 = load_gate(
        VI225
    )

    current = (
        BASE
        / "imagens"
        / f"short_{SHORT_ID}"
        / "scene_02.jpg"
    )

    if not current.exists():
        raise RuntimeError(
            "scene_02_current_missing"
        )

    current_size = jpeg_size(
        current
    )

    if not current_size:
        raise RuntimeError(
            "current_dimensions_unreadable"
        )

    cw, ch = current_size
    cpixels = cw * ch

    checks = (
        vi225.get("checks")
        or []
    )

    candidate = None

    for item in checks:
        if (
            "Hotel Cecil street scene"
            in str(
                item.get("title")
                or ""
            )
        ):
            candidate = item
            break

    if not candidate:
        raise RuntimeError(
            "street_scene_candidate_missing"
        )

    nw = int(
        candidate.get("width")
        or 0
    )

    nh = int(
        candidate.get("height")
        or 0
    )

    npixels = nw * nh

    current_aspect = aspect_score(
        cw,
        ch
    )

    candidate_aspect = aspect_score(
        nw,
        nh
    )

    relative_res = (
        relative_resolution_score(
            npixels,
            cpixels
        )
    )

    # Current scene lacks a verified role score
    # in this A/B stage, so we do not invent one.
    # Candidate carries verified VI225 truth.
    candidate_entity = float(
        candidate.get(
            "primary_score"
        )
        or 0
    )

    candidate_role = float(
        candidate.get(
            "role_score"
        )
        or 0
    )

    candidate_license = float(
        candidate.get(
            "license_score"
        )
        or 0
    )

    # Candidate score emphasizes truth/role,
    # but retains strong vertical-fit penalty.
    candidate_score = (
        candidate_entity * .30
        + candidate_role * .30
        + candidate_license * .15
        + relative_res * .15
        + candidate_aspect * .10
    )

    # Baseline is intentionally conservative:
    # current media gets full relative-resolution
    # and excellent aspect credit, but no invented
    # entity/role credit.
    current_score = (
        90 * .15
        + current_aspect * .10
    )

    # Context evidence from existing production
    # is unknown, so this is a suitability delta,
    # not permission to replace.
    suitability_gain = (
        candidate_score
        - current_score
    )

    pixel_ratio = (
        npixels / cpixels
        if cpixels
        else 0
    )

    same_quality_class = (
        pixel_ratio >= .90
    )

    strong_truth = (
        candidate_entity == 100
        and candidate_role == 100
    )

    candidate_viable = (
        same_quality_class
        and strong_truth
        and candidate_license >= 80
        and candidate_aspect >= 60
    )

    report = {
        "version":
            VERSION,

        "status":
            "VI230_CURRENT_VS_CANDIDATE_AB_CERTIFIED",

        "short_id":
            SHORT_ID,

        "scene":
            SCENE,

        "current": {
            "path":
                str(current),

            "sha256":
                sha256(current),

            "width":
                cw,

            "height":
                ch,

            "pixels":
                cpixels,

            "aspect_score":
                current_aspect,
        },

        "candidate": {
            "title":
                candidate.get("title"),

            "url":
                candidate.get("url"),

            "width":
                nw,

            "height":
                nh,

            "pixels":
                npixels,

            "pixel_ratio_vs_current":
                round(
                    pixel_ratio,
                    4
                ),

            "relative_resolution_score":
                relative_res,

            "aspect_score":
                candidate_aspect,

            "entity_score":
                candidate_entity,

            "role_score":
                candidate_role,

            "license":
                candidate.get("license"),

            "license_score":
                candidate_license,
        },

        "same_quality_class":
            same_quality_class,

        "strong_truth":
            strong_truth,

        "candidate_viable":
            candidate_viable,

        "suitability_gain":
            round(
                suitability_gain,
                2
            ),

        "decision":
            (
                "READY_FOR_CONTROLLED_AB_DOWNLOAD"
                if candidate_viable
                else "KEEP_CURRENT"
            ),

        "blockers":
            [],

        "warnings":
            (
                [
                    "candidate_lower_vertical_fit"
                ]
                if (
                    candidate_aspect
                    < current_aspect
                )
                else []
            ),

        "network_executed":
            False,

        "download_executed":
            False,

        "production_media_mutated":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
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
        " VI230 CURRENT VS AUTHENTIC CANDIDATE A/B"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print()
    print("CURRENT:")
    print(
        " ",
        r["current"]["width"],
        "x",
        r["current"]["height"]
    )
    print(
        " PIXELS:",
        r["current"]["pixels"]
    )
    print(
        " ASPECT SCORE:",
        r["current"]["aspect_score"]
    )
    print(
        " SHA256:",
        r["current"]["sha256"]
    )

    print()
    print("CANDIDATE:")
    print(
        " ",
        r["candidate"]["title"]
    )
    print(
        " ",
        r["candidate"]["width"],
        "x",
        r["candidate"]["height"]
    )
    print(
        " PIXELS:",
        r["candidate"]["pixels"]
    )
    print(
        " PIXEL RATIO:",
        r["candidate"][
            "pixel_ratio_vs_current"
        ]
    )
    print(
        " RELATIVE RES:",
        r["candidate"][
            "relative_resolution_score"
        ]
    )
    print(
        " ASPECT SCORE:",
        r["candidate"]["aspect_score"]
    )
    print(
        " ENTITY:",
        r["candidate"]["entity_score"]
    )
    print(
        " ROLE:",
        r["candidate"]["role_score"]
    )
    print(
        " LICENSE:",
        r["candidate"]["license"]
    )

    print()
    print(
        "SAME QUALITY CLASS:",
        r["same_quality_class"]
    )

    print(
        "STRONG TRUTH:",
        r["strong_truth"]
    )

    print(
        "CANDIDATE VIABLE:",
        r["candidate_viable"]
    )

    print(
        "SUITABILITY GAIN:",
        r["suitability_gain"]
    )

    print(
        "DECISION:",
        r["decision"]
    )

    print(
        "WARNINGS:",
        r["warnings"]
    )

    print()
    print(
        "DOWNLOAD EXECUTED:",
        r["download_executed"]
    )

    print(
        "PRODUCTION MEDIA MUTATED:",
        r["production_media_mutated"]
    )

    print(
        "FFMPEG EXECUTED:",
        r["ffmpeg_executed"]
    )

    print(
        "VIDEO GENERATED:",
        r["video_generated"]
    )
