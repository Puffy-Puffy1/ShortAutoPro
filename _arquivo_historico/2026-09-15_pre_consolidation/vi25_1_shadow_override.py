#!/usr/bin/env python3

import hashlib
import json
import shutil
from pathlib import Path

import vi25_00_canary_replacement as v


BASE = Path.home() / "ShortAutoPro"

VI20 = (
    BASE / "logs/producao/"
    "vi20_00_real_media_ab_latest.json"
)

OUT_DIR = (
    BASE / "temp/"
    "vi25_shadow_override"
)

MANIFEST = (
    BASE / "manifests/"
    "vi25_1_shadow_override_latest.json"
)


def sha(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            b = f.read(
                1024 * 1024
            )

            if not b:
                break

            h.update(b)

    return h.hexdigest()


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


def main():
    vi20 = load_gate(
        VI20
    )

    short_id = str(
        vi20.get("short_id")
    )

    plans = v.build_plan()

    if len(plans) != 1:
        raise RuntimeError(
            "expected_single_canary_scene"
        )

    plan = plans[0]

    scene = int(
        plan["scene"]
    )

    target = Path(
        plan["target"]
    )

    candidate = Path(
        plan["candidate"]
    )

    old_family = v.media_family(
        target
    )

    new_family = v.media_family(
        candidate
    )

    OUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    stage_dir = (
        OUT_DIR
        / f"short_{short_id}"
    )

    stage_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    staged = (
        stage_dir
        / f"scene_{scene:02d}"
          f"{candidate.suffix.lower()}"
    )

    shutil.copy2(
        candidate,
        staged
    )

    if sha(staged) != (
        plan[
            "candidate_sha256"
        ]
    ):
        raise RuntimeError(
            "staged_hash_mismatch"
        )

    source_plan = (
        BASE / "roteiros"
        / f"motion_plan_{short_id}.json"
    )

    if not source_plan.exists():
        raise RuntimeError(
            "motion_plan_missing"
        )

    data = json.loads(
        source_plan.read_text(
            encoding="utf-8"
        )
    )

    changed = 0

    for item in (
        data.get("scenes")
        or []
    ):
        if int(
            item.get("scene")
            or -1
        ) != scene:
            continue

        item[
            "media"
        ] = str(
            staged
        )

        changed += 1

    if changed != 1:
        raise RuntimeError(
            f"scene_override_count:{changed}"
        )

    shadow_plan = (
        OUT_DIR
        / f"motion_plan_{short_id}"
          "_vi25_shadow.json"
    )

    shadow_plan.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    manifest = {
        "status":
            "VI25_1_SHADOW_OVERRIDE_CERTIFIED",

        "short_id":
            short_id,

        "scene":
            scene,

        "production_target":
            str(target),

        "production_family":
            old_family,

        "production_sha256":
            sha(target),

        "candidate":
            str(candidate),

        "candidate_family":
            new_family,

        "candidate_sha256":
            sha(candidate),

        "staged_candidate":
            str(staged),

        "staged_sha256":
            sha(staged),

        "shadow_motion_plan":
            str(shadow_plan),

        "shadow_motion_plan_sha256":
            sha(shadow_plan),

        "vi20_gain":
            plan["vi20_gain"],

        "cross_type":
            old_family != new_family,

        "production_media_mutated":
            False,

        "production_motion_plan_mutated":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "source_recovery":
            "SHADOW_ONLY",
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

    print(
        "STATUS:",
        manifest["status"]
    )

    print(
        "SCENE:",
        scene
    )

    print(
        "PRODUCTION:",
        target
    )

    print(
        "PRODUCTION FAMILY:",
        old_family
    )

    print(
        "STAGED:",
        staged
    )

    print(
        "STAGED FAMILY:",
        new_family
    )

    print(
        "CROSS TYPE:",
        manifest["cross_type"]
    )

    print(
        "SHADOW PLAN:",
        shadow_plan
    )

    print(
        "VI20 GAIN:",
        manifest["vi20_gain"]
    )

    print(
        "PRODUCTION MEDIA MUTATED:",
        False
    )

    print(
        "PRODUCTION PLAN MUTATED:",
        False
    )

    print(
        "FFMPEG EXECUTED:",
        False
    )

    print(
        "VIDEO GENERATED:",
        False
    )


if __name__ == "__main__":
    main()
