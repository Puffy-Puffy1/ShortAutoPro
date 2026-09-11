#!/usr/bin/env python3

import hashlib
import json
import shutil
import time
from pathlib import Path


VERSION = "25.00"

BASE = Path.home() / "ShortAutoPro"

VI20 = (
    BASE / "logs/producao/"
    "vi20_00_real_media_ab_latest.json"
)

MANIFEST = (
    BASE / "manifests/"
    "vi25_canary_replacement_latest.json"
)

BACKUP_ROOT = (
    BASE / "backups/"
    "vi25_canary"
)

MAX_CANARY_SCENES = 1


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



def find_scene_media(scene):
    vi20 = load_gate(VI20)

    short_id = str(
        vi20.get("short_id")
        or ""
    ).strip()

    if not short_id:
        raise RuntimeError(
            "vi20_short_id_missing"
        )

    folder = (
        BASE
        / "imagens"
        / f"short_{short_id}"
    )

    if not folder.exists():
        raise RuntimeError(
            f"short_media_folder_missing:{folder}"
        )

    stem = f"scene_{int(scene):02d}"

    candidates = [
        path
        for path in folder.glob(
            stem + ".*"
        )
        if path.is_file()
    ]

    candidates.sort(
        key=lambda p:
            p.stat().st_mtime,
        reverse=True
    )

    return candidates


def media_family(path):
    ext = Path(path).suffix.lower()

    if ext in {
        ".jpg", ".jpeg",
        ".png", ".webp"
    }:
        return "IMAGE"

    if ext in {
        ".mp4", ".mov",
        ".mkv", ".webm"
    }:
        return "VIDEO"

    return "UNKNOWN"

def build_plan():
    vi20 = load_gate(
        VI20
    )

    ready = (
        vi20.get(
            "ready_for_manual_replacement"
        )
        or []
    )

    if not ready:
        raise RuntimeError(
            "no_vi20_ready_scene"
        )

    ready = ready[
        :MAX_CANARY_SCENES
    ]

    results = {
        int(
            x.get("scene")
        ): x
        for x in (
            vi20.get(
                "results"
            )
            or []
        )
        if x.get(
            "scene"
        ) is not None
    }

    plans = []

    for scene in ready:
        result = results.get(
            int(scene)
        )

        if not result:
            raise RuntimeError(
                f"scene_{scene}_result_missing"
            )

        download = (
            result.get(
                "download"
            )
            or {}
        )

        candidate_path = Path(
            download.get(
                "path"
            )
            or ""
        )

        if not candidate_path.exists():
            raise RuntimeError(
                f"scene_{scene}_candidate_missing"
            )

        expected_hash = (
            download.get(
                "sha256"
            )
        )

        actual_hash = sha256_file(
            candidate_path
        )

        if (
            not expected_hash
            or actual_hash
            != expected_hash
        ):
            raise RuntimeError(
                f"scene_{scene}_candidate_hash_mismatch"
            )

        media = find_scene_media(
            scene
        )

        if not media:
            raise RuntimeError(
                f"scene_{scene}_production_media_not_found"
            )

        # Conservative:
        # require exactly one obvious target.
        target = media[0]

        plans.append({
            "scene":
                int(scene),

            "target":
                str(target),

            "candidate":
                str(candidate_path),

            "candidate_sha256":
                actual_hash,

            "current_sha256":
                sha256_file(
                    target
                ),

            "current_size":
                target.stat().st_size,

            "candidate_size":
                candidate_path.stat().st_size,

            "vi20_gain":
                result.get(
                    "final_gain"
                ),
        })

    return plans


def execute():
    plans = build_plan()

    timestamp = time.strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_dir = (
        BACKUP_ROOT
        / timestamp
    )

    backup_dir.mkdir(
        parents=True,
        exist_ok=False
    )

    manifest = {
        "version":
            VERSION,

        "timestamp":
            timestamp,

        "status":
            "PREPARED",

        "max_canary_scenes":
            MAX_CANARY_SCENES,

        "plans":
            [],

        "video_generated":
            False,

        "ffmpeg_executed":
            False,

        "source_recovery":
            "SHADOW_ONLY",
    }

    try:
        for plan in plans:
            target = Path(
                plan["target"]
            )

            candidate = Path(
                plan["candidate"]
            )

            backup = (
                backup_dir
                / target.name
            )

            shutil.copy2(
                target,
                backup
            )

            backup_hash = sha256_file(
                backup
            )

            if (
                backup_hash
                != plan[
                    "current_sha256"
                ]
            ):
                raise RuntimeError(
                    "backup_hash_mismatch"
                )

            temp_target = (
                target.parent
                / (
                    target.name
                    + ".vi25_tmp"
                )
            )

            shutil.copy2(
                candidate,
                temp_target
            )

            copied_hash = sha256_file(
                temp_target
            )

            if (
                copied_hash
                != plan[
                    "candidate_sha256"
                ]
            ):
                temp_target.unlink(
                    missing_ok=True
                )

                raise RuntimeError(
                    "candidate_copy_hash_mismatch"
                )

            temp_target.replace(
                target
            )

            final_hash = sha256_file(
                target
            )

            if (
                final_hash
                != plan[
                    "candidate_sha256"
                ]
            ):
                raise RuntimeError(
                    "post_replace_hash_mismatch"
                )

            manifest[
                "plans"
            ].append({
                **plan,

                "backup":
                    str(backup),

                "backup_sha256":
                    backup_hash,

                "final_sha256":
                    final_hash,

                "status":
                    "CANARY_REPLACED",
            })

        manifest[
            "status"
        ] = (
            "VI25_CANARY_REPLACEMENT_CERTIFIED"
        )

    except Exception as exc:
        # Immediate rollback.
        for item in manifest[
            "plans"
        ]:
            backup = Path(
                item["backup"]
            )

            target = Path(
                item["target"]
            )

            if backup.exists():
                shutil.copy2(
                    backup,
                    target
                )

        manifest[
            "status"
        ] = "ROLLED_BACK"

        manifest[
            "error"
        ] = (
            type(exc).__name__
            + ": "
            + str(exc)
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

    return manifest


if __name__ == "__main__":
    r = execute()

    print()
    print(
        "=============================================="
    )
    print(
        " VI25.00 CANARY REPLACEMENT CONTROLLER"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "CANARY SCENES:",
        [
            x["scene"]
            for x in r[
                "plans"
            ]
        ]
    )

    for x in r[
        "plans"
    ]:
        print()
        print(
            "SCENE:",
            x["scene"]
        )

        print(
            " TARGET:",
            x["target"]
        )

        print(
            " BACKUP:",
            x["backup"]
        )

        print(
            " OLD HASH:",
            x["current_sha256"]
        )

        print(
            " NEW HASH:",
            x["final_sha256"]
        )

        print(
            " GAIN:",
            x["vi20_gain"]
        )

    print()
    print(
        "FFMPEG EXECUTED:",
        r["ffmpeg_executed"]
    )

    print(
        "VIDEO GENERATED:",
        r["video_generated"]
    )

    print(
        "SOURCE RECOVERY:",
        r["source_recovery"]
    )
