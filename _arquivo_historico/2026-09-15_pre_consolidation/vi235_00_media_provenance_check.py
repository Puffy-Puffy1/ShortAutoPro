#!/usr/bin/env python3
from short_id_runtime_v1 import resolve_short_id as _sap_resolve_short_id

import hashlib
import json
import struct
from pathlib import Path

import requests


VERSION = "235.00"

BASE = Path.home() / "ShortAutoPro"

VI225 = (
    BASE / "logs/producao/"
    "vi225_00_safe_family_fallback_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi235_00_media_provenance_check_latest.json"
)

SANDBOX = (
    BASE / "temp"
    / "vi235_provenance"
)

CURRENT = (
    BASE
    / "imagens"
    / "short_2026-09-01_1433"
    / "scene_02.jpg"
)

HEADERS = {
    "User-Agent":
        "ShortAutoPro/235.00 "
        "(controlled provenance verification)"
}


def load_gate(path):
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


def jpeg_size(path):
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
                0xD9
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


def download(url, destination):
    r = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    r.raise_for_status()

    data = r.content

    if len(data) < 10_000:
        raise RuntimeError(
            "download_too_small"
        )

    if not data.startswith(
        b"\xff\xd8"
    ):
        raise RuntimeError(
            "not_jpeg"
        )

    destination.write_bytes(
        data
    )

    return len(data)


def evaluate():
    if not CURRENT.exists():
        raise RuntimeError(
            "current_scene_02_missing"
        )

    vi225 = load_gate(
        VI225
    )

    checks = (
        vi225.get("checks")
        or []
    )

    targets = []

    for item in checks:
        title = str(
            item.get("title")
            or ""
        )

        if (
            "Hotel Cecil LA.jpg"
            in title
            or
            "Hotel Cecil street scene.jpg"
            in title
        ):
            url = item.get("url")

            if url:
                targets.append({
                    "title":
                        title,

                    "url":
                        url,
                })

    if len(targets) < 2:
        raise RuntimeError(
            "required_candidates_missing"
        )

    SANDBOX.mkdir(
        parents=True,
        exist_ok=True
    )

    current_hash = sha256(
        CURRENT
    )

    current_size = jpeg_size(
        CURRENT
    )

    results = []

    for index, item in enumerate(
        targets,
        start=1
    ):
        destination = (
            SANDBOX
            / f"candidate_{index}.jpg"
        )

        byte_count = download(
            item["url"],
            destination
        )

        candidate_hash = sha256(
            destination
        )

        dimensions = jpeg_size(
            destination
        )

        results.append({
            "title":
                item["title"],

            "sandbox_path":
                str(destination),

            "bytes":
                byte_count,

            "sha256":
                candidate_hash,

            "dimensions":
                list(dimensions)
                if dimensions
                else None,

            "exact_match_current":
                candidate_hash
                == current_hash,
        })

    exact_matches = [
        x
        for x in results
        if x[
            "exact_match_current"
        ]
    ]

    if exact_matches:
        decision = (
            "CURRENT_MEDIA_PROVENANCE_IDENTIFIED"
        )

    else:
        decision = (
            "CURRENT_MEDIA_NOT_EXACT_MATCH"
        )

    report = {
        "version":
            VERSION,

        "status":
            "VI235_MEDIA_PROVENANCE_CERTIFIED",

        "short_id":
            _sap_resolve_short_id(),

        "scene":
            2,

        "current": {
            "path":
                str(CURRENT),

            "sha256":
                current_hash,

            "dimensions":
                list(current_size)
                if current_size
                else None,

            "bytes":
                CURRENT.stat().st_size,
        },

        "candidate_results":
            results,

        "exact_match_titles":
            [
                x["title"]
                for x in exact_matches
            ],

        "decision":
            decision,

        "blockers":
            [],

        "warnings":
            (
                []
                if exact_matches
                else [
                    "current_not_exact_commons_match"
                ]
            ),

        "network_executed":
            True,

        "controlled_sandbox_download":
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
        " VI235 MEDIA PROVENANCE + IDENTITY CHECK"
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
        "CURRENT SHA256:",
        r["current"]["sha256"]
    )

    print(
        "CURRENT DIMENSIONS:",
        r["current"]["dimensions"]
    )

    print(
        "CURRENT BYTES:",
        r["current"]["bytes"]
    )

    print()

    for x in r[
        "candidate_results"
    ]:
        print(
            "CANDIDATE:",
            x["title"]
        )

        print(
            " DIMENSIONS:",
            x["dimensions"]
        )

        print(
            " BYTES:",
            x["bytes"]
        )

        print(
            " SHA256:",
            x["sha256"]
        )

        print(
            " EXACT MATCH CURRENT:",
            x[
                "exact_match_current"
            ]
        )

        print()

    print(
        "EXACT MATCH TITLES:",
        r["exact_match_titles"]
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
        "CONTROLLED SANDBOX DOWNLOAD:",
        r[
            "controlled_sandbox_download"
        ]
    )

    print(
        "PRODUCTION MEDIA MUTATED:",
        r[
            "production_media_mutated"
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
