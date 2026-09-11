#!/usr/bin/env python3

import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path


VERSION = "720.00"

BASE = Path.home() / "ShortAutoPro"
LOG = BASE / "logs/producao"

VI330 = LOG / "vi330_00_controlled_real_ab_latest.json"
VI700 = LOG / "vi700_00_canary_portfolio_builder_latest.json"

OUT = LOG / "vi720_00_case_context_repair_latest.json"

WORK = BASE / "temp/vi720_assets"
CANARY_DIR = BASE / "temp/vi720_canary"

MANIFEST = (
    CANARY_DIR /
    "portfolio_manifest.json"
)

SHORT_ID_DEFAULT = "2026-09-01_1433"


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


def run(command):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr[-2000:]
        )

    return result


def ffprobe_duration(path):
    result = run([
        "ffprobe",
        "-v", "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ])

    return float(
        result.stdout.strip()
    )


def probe_video(path):
    result = run([
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ])

    return json.loads(
        result.stdout
    )


def media_info(path):
    info = probe_video(
        path
    )

    width = None
    height = None
    fps = None
    duration = None

    try:
        duration = float(
            info.get(
                "format",
                {}
            ).get(
                "duration"
            )
        )
    except Exception:
        pass

    for stream in (
        info.get(
            "streams",
            []
        )
    ):
        if stream.get(
            "codec_type"
        ) != "video":
            continue

        width = stream.get(
            "width"
        )

        height = stream.get(
            "height"
        )

        fps = (
            stream.get(
                "avg_frame_rate"
            )
            or stream.get(
                "r_frame_rate"
            )
        )

        break

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "duration": duration,
    }


def scene_map_path(short_id):
    options = [
        BASE / "roteiros" /
        f"scene_map_{short_id}.json",

        BASE /
        f"scene_map_{short_id}.json",
    ]

    for path in options:
        if path.exists():
            return path

    return None


def scene_segments(short_id):
    path = scene_map_path(
        short_id
    )

    if not path:
        return {}

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return {}

    result = {}

    if isinstance(
        data,
        list
    ):
        iterable = data

    elif isinstance(
        data,
        dict
    ):
        iterable = (
            data.get("scenes")
            or data.get("scene_map")
            or data.get("items")
            or []
        )

        if not iterable:
            for key, value in data.items():
                if isinstance(
                    value,
                    dict
                ):
                    try:
                        scene = int(
                            re.sub(
                                r"\D",
                                "",
                                str(key)
                            )
                        )
                    except Exception:
                        continue

                    result[scene] = str(
                        value.get("segment")
                        or value.get("trecho")
                        or value.get("texto")
                        or ""
                    )

            return result

    else:
        return {}

    for index, item in enumerate(
        iterable,
        start=1
    ):
        if not isinstance(
            item,
            dict
        ):
            continue

        scene = (
            item.get("scene")
            or item.get("scene_number")
            or item.get("numero")
            or item.get("id")
            or index
        )

        try:
            scene = int(scene)
        except Exception:
            scene = index

        result[scene] = str(
            item.get("segment")
            or item.get("trecho")
            or item.get("texto")
            or item.get("narration")
            or ""
        )

    return result


def case_context_ok(text):
    low = (
        str(text or "")
        .lower()
    )

    terms = (
        "elisa",
        "lam",
        "cecil",
        "hotel",
        "elevador",
        "elevator",
        "câmera",
        "camera",
        "vigilância",
        "surveillance",
        "corredor",
        "hallway",
    )

    return any(
        term in low
        for term in terms
    )


def make_vertical_frame(
    source,
    timestamp,
    destination,
    foreground_width=980,
    brightness=-0.08
):
    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    destination.unlink(
        missing_ok=True
    )

    filter_complex = (
        "[0:v]split=2[bg][fg];"
        "[bg]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "gblur=sigma=28,"
        f"eq=brightness={brightness}:saturation=0.70"
        "[bg2];"
        "[fg]"
        f"scale={foreground_width}:-2"
        "[fg2];"
        "[bg2][fg2]"
        "overlay=(W-w)/2:(H-h)/2"
    )

    run([
        "ffmpeg",
        "-y",
        "-ss",
        f"{timestamp:.3f}",
        "-i",
        str(source),
        "-filter_complex",
        filter_complex,
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(destination),
    ])

    if not destination.exists():
        raise RuntimeError(
            "frame_not_created"
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
            media_info(destination),
    }


def make_vertical_case_video(
    source,
    start,
    duration,
    destination
):
    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    destination.unlink(
        missing_ok=True
    )

    filter_complex = (
        "[0:v]split=2[bg][fg];"
        "[bg]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "gblur=sigma=30,"
        "eq=brightness=-0.10:saturation=0.65"
        "[bg2];"
        "[fg]"
        "scale=1000:-2"
        "[fg2];"
        "[bg2][fg2]"
        "overlay=(W-w)/2:(H-h)/2,"
        "format=yuv420p"
    )

    run([
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{duration:.3f}",
        "-i",
        str(source),
        "-filter_complex",
        filter_complex,
        "-an",
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(destination),
    ])

    if not destination.exists():
        raise RuntimeError(
            "case_video_not_created"
        )

    return {
        "sandbox_path":
            str(destination),

        "sha256":
            sha256(destination),

        "bytes":
            destination.stat().st_size,

        "family":
            "VIDEO",

        "info":
            media_info(destination),
    }


def make_cta_background(
    source,
    destination
):
    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    destination.unlink(
        missing_ok=True
    )

    vf = (
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "eq=brightness=-0.13:"
        "contrast=1.03:"
        "saturation=0.78"
    )

    run([
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-vf",
        vf,
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(destination),
    ])

    if not destination.exists():
        raise RuntimeError(
            "cta_not_created"
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
            media_info(destination),
    }


def validate_case_source(
    candidate
):
    path_value = candidate.get(
        "sandbox_path"
    )

    expected = candidate.get(
        "sha256"
    )

    if not path_value:
        return {
            "valid": False,
            "reason":
                "sandbox_path_missing"
        }

    path = Path(
        path_value
    )

    if not path.exists():
        return {
            "valid": False,
            "reason":
                "case_video_missing"
        }

    actual = sha256(
        path
    )

    if (
        expected
        and actual != expected
    ):
        return {
            "valid": False,
            "reason":
                "case_video_hash_mismatch"
        }

    info = media_info(
        path
    )

    if not info.get(
        "duration"
    ):
        return {
            "valid": False,
            "reason":
                "case_video_duration_missing"
        }

    return {
        "valid": True,
        "path": str(path),
        "sha256": actual,
        "info": info,
    }


def evaluate():
    vi330 = load_gate(
        VI330
    )

    vi700 = load_gate(
        VI700
    )

    short_id = str(
        vi700.get(
            "short_id"
        )
        or SHORT_ID_DEFAULT
    )

    old_manifest_path = Path(
        vi700.get(
            "manifest",
            {}
        ).get(
            "path"
        )
    )

    if not old_manifest_path.exists():
        raise RuntimeError(
            "vi700_manifest_missing"
        )

    old_manifest = json.loads(
        old_manifest_path.read_text(
            encoding="utf-8"
        )
    )

    manifest = copy.deepcopy(
        old_manifest
    )

    manifest[
        "version"
    ] = VERSION

    manifest[
        "parent_manifest"
    ] = str(
        old_manifest_path
    )

    case_candidate = (
        vi330.get(
            "candidate"
        )
        or {}
    )

    case_validation = (
        validate_case_source(
            case_candidate
        )
    )

    if not case_validation[
        "valid"
    ]:
        raise RuntimeError(
            "verified_case_video_invalid:"
            + str(
                case_validation
            )
        )

    source = Path(
        case_validation[
            "path"
        ]
    )

    duration = float(
        case_validation[
            "info"
        ][
            "duration"
        ]
    )

    if duration < 4:
        raise RuntimeError(
            "verified_case_video_too_short"
        )

    segments = scene_segments(
        short_id
    )

    t4 = min(
        max(
            duration * 0.20,
            0.1
        ),
        max(
            duration - 0.2,
            0.1
        )
    )

    t5 = min(
        max(
            duration * 0.42,
            0.1
        ),
        max(
            duration - 0.2,
            0.1
        )
    )

    t6 = min(
        max(
            duration * 0.68,
            0.1
        ),
        max(
            duration - 0.2,
            0.1
        )
    )

    clip_duration = min(
        8.0,
        max(
            3.0,
            duration * 0.25
        )
    )

    clip_start = max(
        0.0,
        min(
            duration
            - clip_duration,
            duration * 0.45
        )
    )

    created = {}

    created[4] = make_vertical_frame(
        source,
        t4,
        WORK / "scene_04_case_evidence.jpg",
        foreground_width=1000,
        brightness=-0.10
    )

    # Scenes 5/6 are allowed only when their
    # narration remains inside the case context.
    scene5_ok = case_context_ok(
        segments.get(
            5,
            ""
        )
    )

    scene6_ok = case_context_ok(
        segments.get(
            6,
            ""
        )
    )

    if scene5_ok:
        created[5] = make_vertical_frame(
            source,
            t5,
            WORK / "scene_05_case_context.jpg",
            foreground_width=930,
            brightness=-0.06
        )

    if scene6_ok:
        created[6] = make_vertical_frame(
            source,
            t6,
            WORK / "scene_06_case_context.jpg",
            foreground_width=1040,
            brightness=-0.11
        )

    created[7] = make_vertical_case_video(
        source,
        clip_start,
        clip_duration,
        WORK / "scene_07_case_elevator.mp4"
    )

    scene2 = (
        manifest.get(
            "scenes",
            {}
        ).get(
            "2",
            {}
        )
    )

    scene2_path = Path(
        scene2.get(
            "original_path"
        )
        or ""
    )

    if not scene2_path.exists():
        raise RuntimeError(
            "verified_scene2_context_missing"
        )

    created[12] = make_cta_background(
        scene2_path,
        WORK / "scene_12_hotel_cecil_cta.jpg"
    )

    usage = {
        4:
            "AUTHENTIC_CASE_EVIDENCE_FRAME",

        5:
            "AUTHENTIC_CASE_CONTEXT_NOT_EXACT_EVENT",

        6:
            "AUTHENTIC_CASE_CONTEXT_NOT_EXACT_EVENT",

        7:
            "AUTHENTIC_CASE_ELEVATOR_CLIP",

        12:
            "VERIFIED_HOTEL_CONTEXT_CTA_NOT_DOCUMENT",
    }

    title = {
        4:
            "Elisa Lam elevator surveillance - derived frame",

        5:
            "Elisa Lam elevator surveillance - context frame",

        6:
            "Elisa Lam elevator surveillance - context frame",

        7:
            "Elisa Lam elevator surveillance - vertical clip",

        12:
            "Hotel Cecil verified facade - CTA background",
    }

    for scene, asset in (
        created.items()
    ):
        entry = (
            manifest[
                "scenes"
            ][
                str(scene)
            ]
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
        ] = title[
            scene
        ]

        entry[
            "license"
        ] = (
            case_candidate.get(
                "license"
            )
            if scene in {
                4,
                5,
                6,
                7,
            }
            else "CC BY-SA 3.0"
        )

        entry[
            "vi720_usage"
        ] = usage[
            scene
        ]

        if scene == 12:
            entry[
                "mode"
            ] = (
                "CANARY_CASE_CONTEXT_CTA"
            )

        elif scene == 7:
            entry[
                "mode"
            ] = (
                "CANARY_AUTHENTIC_CASE_VIDEO"
            )

        else:
            entry[
                "mode"
            ] = (
                "CANARY_AUTHENTIC_CASE_FRAME"
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
        "vi720_policy"
    ] = {
        "scene4":
            "authentic_evidence",

        "scene5":
            (
                "authentic_case_context"
                if scene5_ok
                else "legacy_semantic_gate_failed"
            ),

        "scene6":
            (
                "authentic_case_context"
                if scene6_ok
                else "legacy_semantic_gate_failed"
            ),

        "scene7":
            "authentic_case_video",

        "scene12":
            "role_repaired_to_context_cta",

        "no_fake_document":
            True,

        "no_identity_invention":
            True,
    }

    CANARY_DIR.mkdir(
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

    hashes = {}

    for scene in active:
        entry = manifest[
            "scenes"
        ][
            str(scene)
        ]

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

    required_new = {
        4,
        7,
        12,
    }

    ready = (
        required_new.issubset(
            set(active)
        )
        and not duplicates
    )

    warnings = []

    if not scene5_ok:
        warnings.append(
            "scene5_case_context_text_gate_failed_keep_legacy"
        )

    if not scene6_ok:
        warnings.append(
            "scene6_case_context_text_gate_failed_keep_legacy"
        )

    if 5 in created:
        warnings.append(
            "scene5_authentic_case_context_not_claimed_exact_moment"
        )

    if 6 in created:
        warnings.append(
            "scene6_authentic_case_context_not_claimed_exact_moment"
        )

    warnings.append(
        "scene12_role_changed_from_unverified_document_to_context_cta"
    )

    report = {
        "version":
            VERSION,

        "status":
            (
                "VI720_CASE_CONTEXT_CANARY_READY"
                if ready
                else "HOLD"
            ),

        "short_id":
            short_id,

        "canary_ready":
            ready,

        "verified_case_source": {
            "path":
                str(source),

            "sha256":
                case_validation[
                    "sha256"
                ],

            "duration":
                duration,

            "license":
                case_candidate.get(
                    "license"
                ),
        },

        "scene_segments": {
            str(scene):
                segments.get(
                    scene,
                    ""
                )
            for scene in (
                4,
                5,
                6,
                7,
                12,
            )
        },

        "scene5_context_gate":
            scene5_ok,

        "scene6_context_gate":
            scene6_ok,

        "created_assets":
            created,

        "active_override_scenes":
            active,

        "duplicate_asset_hashes":
            duplicates,

        "manifest": {
            "path":
                str(MANIFEST),

            "sha256":
                sha256(MANIFEST),
        },

        "warnings":
            warnings,

        "blockers":
            (
                []
                if ready
                else [
                    "minimum_vi720_asset_set_not_ready"
                ]
            ),

        "production_media_mutated":
            False,

        "core_source_mutated":
            False,

        "automatic_replace":
            False,

        "video_generated":
            True,

        "video_generated_scope":
            "SCENE7_STAGED_ASSET_ONLY",
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
        " VI720 CASE CONTEXT REPAIR"
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
        "===== VERIFIED CASE SOURCE ====="
    )

    print(
        r[
            "verified_case_source"
        ]
    )

    print()
    print(
        "===== SCENE 5/6 SEMANTIC GATES ====="
    )

    print(
        "SCENE 5:",
        r[
            "scene5_context_gate"
        ]
    )

    print(
        "SCENE 6:",
        r[
            "scene6_context_gate"
        ]
    )

    print()
    print(
        "===== NEW ASSETS ====="
    )

    for scene, asset in (
        r[
            "created_assets"
        ].items()
    ):
        print(
            "SCENE",
            scene,
            "|",
            asset[
                "family"
            ]
        )

        print(
            "   PATH:",
            asset[
                "sandbox_path"
            ]
        )

        print(
            "   SHA:",
            asset[
                "sha256"
            ]
        )

        print(
            "   INFO:",
            asset[
                "info"
            ]
        )

    print()
    print(
        "DUPLICATE HASHES:",
        r[
            "duplicate_asset_hashes"
        ]
    )

    print(
        "MANIFEST:",
        r[
            "manifest"
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
